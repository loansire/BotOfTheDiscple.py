# -*- coding: utf-8 -*-
"""Cog pipeline : un unique poll/min qui traite LE reset Bungie selon le jour.

Source de vérité unique du dernier reset traité : PipelineState.last_reset_iso
(global, pas par serveur).

Arbre de décision (chaque reset est un reset quotidien) :
- TOUJOURS    → secteurs oubliés + Avant-garde + Eververse (republier)
- VENDREDI    → Xûr arrive : supprime tout + republie tout (statut + catégories)
- MARDI       → Xûr part (supprime catégories + édite statut) + raids/donjons + Ada-1
- FIN DE RESET→ vérification d'existence : republie SANS ping les messages
  persistants disparus de Discord (à chaque reset, pas chaque minute).

Détection « reset déjà traité » : comparaison de last_reset() (instant pur du
dernier reset survenu) avec l'iso persisté. On n'avance l'iso QU'APRÈS succès.

Hold mode : si un fetch Bungie lève BungieUnavailableError (maintenance
déclarée, panne non déclarée, ou données pas encore prêtes après le reset), on
N'AVANCE PAS l'état et on retente plus tard. Le poll/min EST la boucle de
retry, espacée progressivement (1, 2, 5, 10 puis 15 min) ; le hash-skip évite
de reposter ce qui a déjà été publié avant l'échec (seule la partie en échec
est réellement retentée). Une erreur inattendue suit le même chemin (avec un
log d'erreur) au lieu d'être retentée sans limite chaque minute.

Les jours de semaine des resets en attente sont persistés (pending_weekdays) :
si une maintenance du mardi déborde sur le reset du mercredi, les étapes du
mardi (raids/donjons, Ada-1, départ de Xûr) sont quand même jouées.

Alerte : après HOLD_ALERT_AFTER en hold mode, un DM est envoyé à l'auteur du
bot (OWNER_ID), puis un second au rétablissement.

Refresh manuel (/refresh) : publication forcée SANS ping — exception assumée à
la règle « repost = ping ». Les choix proposés sont dérivés du registre des
topics (bot/topics.py) ; le reset automatique, lui, notifie toujours."""
import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.bungie.errors import BungieMaintenanceError, BungieUnavailableError
from bot.bungie.reset import FRIDAY, TUESDAY, last_reset
from bot.core.config import OWNER_ID
from bot.core.logger import log
from bot.features.ada.handler import publication as ada
from bot.features.eververse.handler import publication as eververse
from bot.features.vanguard.handler import publication as vanguard
from bot.features.weekly import handler as weekly
from bot.features.xur import handler as xur
from bot.features.xur import is_xur_active
from bot.publishing.registry import publications
from bot.storage.pipeline_state import pipeline_state
from bot.topics import TOPICS

# Délais successifs entre deux tentatives en hold mode (minutes, le dernier
# se répète).
_RETRY_DELAYS_MIN = (1, 2, 5, 10, 15)

# Durée de hold mode au-delà de laquelle l'auteur du bot est prévenu en DM.
HOLD_ALERT_AFTER = 30 * 60  # secondes

# Valeur spéciale « toutes les publications ».
_REFRESH_ALL = "all"

# Choix proposés par /refresh : les topics PERSISTANTS du registre (les topics
# événementiels news_*/maintenance_* n'ont rien à « rafraîchir »).
_REFRESH_CHOICES = [app_commands.Choice(name="Tout", value=_REFRESH_ALL)] + [
    app_commands.Choice(name=t.refresh, value=t.key) for t in TOPICS.values() if t.refresh
]


class Pipeline(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = pipeline_state()
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
        # features/weekly/freshness.py).
        await weekly.lost_sectors.publish(self.bot, strict=True)
        await vanguard.publish(self.bot, strict=True)
        await eververse.publish(self.bot)

        # VENDREDI : Xûr arrive (seulement s'il est encore là : un hold mode
        # qui aurait débordé jusqu'au mardi ne doit pas le republier).
        if FRIDAY in weekdays and is_xur_active():
            await xur.publish_arrival(self.bot)

        # MARDI : Xûr part + raids/donjons + Ada-1 (resets hebdo).
        # publish_raid_dungeon purge une seule fois le cache partagé puis
        # publie les deux messages distincts (raids puis donjons).
        if TUESDAY in weekdays:
            await xur.mark_departed(self.bot)
            await weekly.publish_raid_dungeon(self.bot, strict=True)
            await ada.publish(self.bot)

        # FIN DE RESET : réparation des messages disparus (sans ping).
        await self._verify_existence()

    async def _verify_existence(self):
        """Republie SANS ping les messages persistants supprimés à la main.
        Une BungieUnavailableError est RE-LEVÉE pour que le reset entier soit
        considéré en échec (hold mode) ; les autres erreurs sont seulement
        loguées."""
        try:
            for publication in publications().values():
                if hasattr(publication, "restore"):
                    await publication.restore(self.bot)
        except BungieUnavailableError:
            raise
        except Exception as e:
            log.error(f"[Pipeline] Vérification d'existence échouée : {e}")

    # ---------- Refresh manuel (ciblé ou global) ----------
    # Chaque publication invalide son état (les IDs de messages sont conservés
    # pour supprimer les anciens), régénère ses images puis republie, SANS ping.

    async def _refresh(self, key: str) -> None:
        if key == _REFRESH_ALL:
            for publication in publications().values():
                await publication.refresh(self.bot)
        else:
            await publications()[key].refresh(self.bot)

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

        if publication != _REFRESH_ALL and publication not in publications():
            # garde-fou (les choices contraignent déjà la valeur)
            await interaction.response.send_message(
                f":x: Publication inconnue : `{publication}`.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        label = (
            "Toutes les publications" if publication == _REFRESH_ALL
            else TOPICS[publication].refresh
        )
        try:
            async with self._lock:
                await self._refresh(publication)
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
