# -*- coding: utf-8 -*-
"""Cog pipeline : un unique poll/min qui traite LE reset Bungie selon le jour.

Remplace les cogs weekly et xur (fusionnés). Source de vérité unique du
dernier reset traité : PipelineState.last_reset_iso (global, pas par serveur).

Arbre de décision (chaque reset est un reset quotidien) :
- TOUJOURS    → secteurs oubliés + Avant-garde + Eververse (republier)
- VENDREDI    → Xûr arrive : supprime tout + republie tout (statut + catégories)
- MARDI       → Xûr part (supprime catégories + édite statut) + raids/donjons + Ada-1
- FIN DE RESET→ vérification d'existence (point 4) : republie SANS ping les
  messages persistants disparus de Discord (à chaque reset, pas chaque minute).

Détection « reset déjà traité » : comparaison de last_reset() (instant pur du
dernier reset survenu) avec l'iso persisté. On n'avance l'iso QU'APRÈS succès.

Hold mode (point 9) : si un fetch Bungie lève BungieUnavailableError
(maintenance déclarée, panne non déclarée, ou données pas encore prêtes après
le reset), on N'AVANCE PAS l'état et on retente plus tard. Le poll/min EST la
boucle de retry, espacée progressivement (1, 2, 5, 10 puis 15 min) ; le
hash-skip évite de reposter ce qui a déjà été publié avant l'échec (seule la
partie en échec est réellement retentée). Une erreur inattendue suit le même
chemin (avec un log d'erreur) au lieu d'être retentée sans limite chaque minute.

Les jours de semaine des resets en attente sont persistés (pending_weekdays) :
si une maintenance du mardi déborde sur le reset du mercredi, les étapes du
mardi (raids/donjons, Ada-1, départ de Xûr) sont quand même jouées.

Alerte : après HOLD_ALERT_AFTER en hold mode, un DM est envoyé à l'auteur du
bot (OWNER_ID), puis un second au rétablissement.

Refresh manuel (/refresh) : publication forcée SANS ping (`ping=False`) —
exception assumée à la règle « repost = ping ». Le reset automatique, lui,
notifie toujours (ping par défaut)."""
import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.bungie.errors import BungieMaintenanceError, BungieUnavailableError
from bot.bungie.reset import FRIDAY, TUESDAY, last_reset
from bot.discord.handlers import ada as ada_handler
from bot.discord.handlers import eververse as eververse_handler
from bot.discord.handlers import vanguard as vanguard_handler
from bot.discord.handlers import weekly as weekly_handler
from bot.discord.handlers import xur as xur_handler
from bot.features.ada.state import AdaMessageState
from bot.features.eververse.state import EververseMessageState
from bot.features.pipeline_state import PipelineState
from bot.features.weekly.state import WeeklyMessageState
from bot.features.xur import is_xur_active
from bot.features.xur.state import XurMessageState
from bot.utils.logger import log

# Seul utilisateur autorisé à déclencher /refresh (auteur du bot).
OWNER_ID = 222465158075777035

# Délais successifs entre deux tentatives en hold mode (minutes, le dernier
# se répète).
_RETRY_DELAYS_MIN = (1, 2, 5, 10, 15)

# Durée de hold mode au-delà de laquelle l'auteur du bot est prévenu en DM.
HOLD_ALERT_AFTER = 30 * 60  # secondes

# Valeur spéciale « toutes les publications ».
_REFRESH_ALL = "all"

# Choix proposés par /refresh (value = clé interne de dispatch). Seules les
# features PERSISTANTES sont listées : les topics événementiels (news_*,
# maintenance_*) n'ont rien à « rafraîchir » (publiés sur nouvel article/event).
_REFRESH_CHOICES = [
    app_commands.Choice(name="Tout", value=_REFRESH_ALL),
    app_commands.Choice(name="Secteurs Oubliés", value="daily_lost_sector"),
    app_commands.Choice(name="Raids", value="weekly_raid"),
    app_commands.Choice(name="Donjons", value="weekly_dungeon"),
    app_commands.Choice(name="Avant-garde", value="daily_vanguard"),
    app_commands.Choice(name="Xûr", value="xur"),
    app_commands.Choice(name="Eververse", value="eververse"),
    app_commands.Choice(name="Ada-1", value="ada"),
]

# Libellés pour le message de confirmation (par value).
_REFRESH_LABELS = {
    _REFRESH_ALL: "Toutes les publications",
    "daily_lost_sector": "Secteurs Oubliés",
    "weekly_raid": "Raids",
    "weekly_dungeon": "Donjons",
    "daily_vanguard": "Avant-garde",
    "xur": "Xûr",
    "eververse": "Eververse",
    "ada": "Ada-1",
}


class Pipeline(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = PipelineState()
        self.weekly_state = WeeklyMessageState()
        self.xur_state = XurMessageState()
        self.eververse_state = EververseMessageState()
        self.ada_state = AdaMessageState()
        self._hold = False  # True tant que le reset n'a pas pu être traité
        self._hold_since: float | None = None   # time.monotonic() d'entrée en hold
        self._hold_reason = ""
        self._attempts = 0                      # tentatives échouées consécutives
        self._retry_at = 0.0                    # time.monotonic() de la prochaine tentative
        self._alert_sent = False
        # Sérialise le poll automatique et /refresh (mêmes états, sinon
        # suppression/repost concurrents et messages en double).
        self._lock = asyncio.Lock()
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    # ---------- Détection du reset (automatique) ----------
    @tasks.loop(minutes=1)
    async def poll(self):
        reset = last_reset()
        current = reset.isoformat()
        if current == self.state.last_reset_iso:
            return  # reset déjà traité (rattrapage automatique au redémarrage)
        if time.monotonic() < self._retry_at:
            return  # hold mode : on attend la prochaine tentative planifiée

        # Le jour du reset courant rejoint les jours en attente (persistés).
        weekdays = set(self.state.pending_weekdays)
        if reset.weekday() not in weekdays:
            weekdays.add(reset.weekday())
            self.state.pending_weekdays = list(weekdays)
            self.state.save()

        if self._hold:
            log.debug(f"[Pipeline] Hold mode — tentative n°{self._attempts + 1} (weekdays={sorted(weekdays)}).")
        else:
            log.info(f"[Pipeline] Nouveau reset détecté (weekdays={sorted(weekdays)}).")

        async with self._lock:
            try:
                await self._process_reset(weekdays)
            except BungieUnavailableError as e:
                kind = "maintenance" if isinstance(e, BungieMaintenanceError) else "données indisponibles"
                await self._enter_hold(f"{kind} : {e}", level="warning")
                return  # on n'avance PAS l'état → retry plus tard
            except Exception as e:
                await self._enter_hold(f"erreur inattendue : {e!r}", level="error")
                return

        await self._leave_hold()
        self.state.pending_weekdays = []
        self.state.last_reset_iso = current
        self.state.save()

    async def _enter_hold(self, reason: str, *, level: str) -> None:
        """Hold mode : planifie la prochaine tentative (backoff) et prévient
        l'auteur du bot si le blocage dure."""
        delay = _RETRY_DELAYS_MIN[min(self._attempts, len(_RETRY_DELAYS_MIN) - 1)]
        self._attempts += 1
        self._retry_at = time.monotonic() + delay * 60
        self._hold_reason = reason

        if not self._hold:
            self._hold = True
            self._hold_since = time.monotonic()
            getattr(log, level)(
                f"[Pipeline] Reset non traité ({reason}) — hold mode activé, "
                f"nouvelle tentative dans {delay} min."
            )
        else:
            log.debug(f"[Pipeline] Toujours en hold ({reason}) — prochaine tentative dans {delay} min.")

        held = time.monotonic() - (self._hold_since or time.monotonic())
        if not self._alert_sent and held >= HOLD_ALERT_AFTER:
            self._alert_sent = await self._dm_owner(
                f"⚠️ **BotOfTheDisciple** : le reset Bungie n'est toujours pas traité "
                f"après {int(held // 60)} min ({self._attempts} tentatives).\n"
                f"Dernière raison : `{reason[:300]}`\n"
                "Les publications reprendront automatiquement au rétablissement."
            )

    async def _leave_hold(self) -> None:
        if self._hold:
            held = int((time.monotonic() - (self._hold_since or time.monotonic())) // 60)
            log.info(f"[Pipeline] Reset traité après {held} min de hold mode — hold levé.")
            if self._alert_sent:
                await self._dm_owner(
                    f"✅ **BotOfTheDisciple** : reset traité, publications à jour "
                    f"(après {held} min de blocage)."
                )
        self._hold = False
        self._hold_since = None
        self._hold_reason = ""
        self._attempts = 0
        self._retry_at = 0.0
        self._alert_sent = False

    async def _dm_owner(self, content: str) -> bool:
        """DM à l'auteur du bot. True si envoyé (sinon on retentera plus tard)."""
        try:
            user = self.bot.get_user(OWNER_ID) or await self.bot.fetch_user(OWNER_ID)
            await user.send(content)
            return True
        except discord.DiscordException as e:
            log.warning(f"[Pipeline] DM d'alerte impossible : {e}")
            return False

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()

    async def _process_reset(self, weekdays: set[int]):
        """`weekdays` : jours des resets en attente (normalement un seul ; deux
        si un hold mode a débordé sur le reset suivant)."""
        # TOUJOURS : secteurs oubliés + Avant-garde + Eververse (tout reset est
        # quotidien). strict=True : refuse des données pas encore à jour (cf.
        # handlers.weekly / handlers.vanguard).
        await weekly_handler.publish_lost_sectors(self.bot, self.weekly_state, strict=True)
        await vanguard_handler.publish(self.bot, self.weekly_state, strict=True)
        await eververse_handler.publish(self.bot, self.eververse_state)

        # VENDREDI : Xûr arrive (seulement s'il est encore là : un hold mode
        # qui aurait débordé jusqu'au mardi ne doit pas le republier).
        if FRIDAY in weekdays and is_xur_active():
            await xur_handler.publish_arrival(self.bot, self.xur_state)

        # MARDI : Xûr part + raids/donjons + Ada-1 (resets hebdo).
        # publish_raid_dungeon orchestre la purge unique du cache puis publie
        # les deux messages distincts (raids puis donjons). Ada-1 (vendor hebdo)
        # publie ensuite son propre message (cache d'icônes séparé, banners/ada/).
        if TUESDAY in weekdays:
            await xur_handler.mark_departed(self.bot, self.xur_state)
            await weekly_handler.publish_raid_dungeon(self.bot, self.weekly_state, strict=True)
            await ada_handler.publish(self.bot, self.ada_state)

        # FIN DE RESET : réparation des messages disparus (sans ping).
        await self._verify_existence()

    async def _verify_existence(self):
        """Point 4 : republie SANS ping les messages persistants supprimés à la
        main. Couvre tous les topics. Une BungieUnavailableError est RE-LEVÉE
        pour que le reset entier soit considéré en échec (hold mode) ; les
        autres erreurs sont seulement loguées."""
        try:
            await weekly_handler.restore(self.bot, self.weekly_state)
            await vanguard_handler.restore(self.bot, self.weekly_state)
            await xur_handler.restore(self.bot, self.xur_state)
            await eververse_handler.restore(self.bot, self.eververse_state)
            await ada_handler.restore(self.bot, self.ada_state)
        except BungieUnavailableError:
            raise
        except Exception as e:
            log.error(f"[Pipeline] Vérification d'existence échouée : {e}")

    # ---------- Refresh manuel (ciblé ou global) ----------
    # Chaque coroutine invalide l'état CIBLÉ (les IDs de messages sont conservés
    # pour pouvoir supprimer les anciens) puis republie uniquement sa feature,
    # SANS ping (refresh = forcer, mais sans re-notifier les rôles). « Forcer »
    # régénère aussi les images : raids/donjons passent par refresh_raid/
    # refresh_dungeon (purge du cache bandeaux) ; les autres features purgent
    # déjà leur cache en interne dans publish_*.

    async def _refresh_sectors(self):
        self.weekly_state.invalidate("daily_lost_sector")
        await weekly_handler.publish_lost_sectors(self.bot, self.weekly_state, ping=False)

    async def _refresh_raid(self):
        self.weekly_state.invalidate("weekly_raid")
        await weekly_handler.refresh_raid(self.bot, self.weekly_state)

    async def _refresh_dungeon(self):
        self.weekly_state.invalidate("weekly_dungeon")
        await weekly_handler.refresh_dungeon(self.bot, self.weekly_state)

    async def _refresh_vanguard(self):
        self.weekly_state.invalidate("daily_vanguard")
        await vanguard_handler.publish(self.bot, self.weekly_state, ping=False)

    async def _refresh_xur(self):
        self.xur_state.invalidate()
        if is_xur_active():
            await xur_handler.publish_arrival(self.bot, self.xur_state, ping=False)
        else:
            # Édition in-place du statut « absent » → aucune notification.
            await xur_handler.refresh_absent_status(self.bot, self.xur_state)

    async def _refresh_eververse(self):
        self.eververse_state.invalidate()
        await eververse_handler.publish(self.bot, self.eververse_state, ping=False)

    async def _refresh_ada(self):
        self.ada_state.invalidate()
        await ada_handler.publish(self.bot, self.ada_state, ping=False)

    async def _refresh_all(self):
        # Invalide tout (les IDs sont conservés pour supprimer les anciens).
        self.weekly_state.invalidate()
        self.xur_state.invalidate()
        self.eververse_state.invalidate()
        self.ada_state.invalidate()

        await weekly_handler.publish_lost_sectors(self.bot, self.weekly_state, ping=False)
        # Orchestrateur : purge unique du cache puis raids + donjons (sans ping).
        await weekly_handler.publish_raid_dungeon(self.bot, self.weekly_state, ping=False)
        await vanguard_handler.publish(self.bot, self.weekly_state, ping=False)
        await eververse_handler.publish(self.bot, self.eververse_state, ping=False)
        # Ada-1 : vendor permanent → on republie quel que soit le jour.
        await ada_handler.publish(self.bot, self.ada_state, ping=False)

        if is_xur_active():
            await xur_handler.publish_arrival(self.bot, self.xur_state, ping=False)
        else:
            await xur_handler.refresh_absent_status(self.bot, self.xur_state)

    def _dispatch(self):
        """Table {value → coroutine de refresh}."""
        return {
            _REFRESH_ALL: self._refresh_all,
            "daily_lost_sector": self._refresh_sectors,
            "weekly_raid": self._refresh_raid,
            "weekly_dungeon": self._refresh_dungeon,
            "daily_vanguard": self._refresh_vanguard,
            "xur": self._refresh_xur,
            "eververse": self._refresh_eververse,
            "ada": self._refresh_ada,
        }

    @app_commands.command(
        name="refresh",
        description="Réactualise une publication persistante (sans ping).",
    )
    @app_commands.describe(
        publication="Publication à actualiser (par défaut : toutes)."
    )
    @app_commands.choices(publication=_REFRESH_CHOICES)
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def refresh(
        self, interaction: discord.Interaction, publication: str = _REFRESH_ALL
    ):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "🚫 Cette commande est réservée à l'auteur du bot.", ephemeral=True
            )
            return

        fn = self._dispatch().get(publication)
        if fn is None:  # garde-fou (les choices contraignent déjà la valeur)
            await interaction.response.send_message(
                f":x: Publication inconnue : `{publication}`.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        label = _REFRESH_LABELS.get(publication, publication)
        try:
            async with self._lock:
                await fn()
        except BungieUnavailableError as e:
            await interaction.followup.send(
                "🔧 L'API Bungie est indisponible (maintenance ou données pas "
                f"encore à jour : {str(e)[:200]}). Réessaie plus tard.",
                ephemeral=True,
            )
            return
        except Exception as e:
            log.error(f"[Pipeline] /refresh ({publication}) a échoué : {e}")
            await interaction.followup.send(
                ":x: Échec de la republication.", ephemeral=True
            )
            return

        await interaction.followup.send(
            f"✅ {label} : actualisation effectuée (sans ping).", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Pipeline(bot))