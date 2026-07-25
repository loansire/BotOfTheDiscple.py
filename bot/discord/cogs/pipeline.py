# -*- coding: utf-8 -*-
"""Cog pipeline : un unique poll/min qui traite LE reset Bungie selon le jour.

Remplace les cogs weekly et xur (fusionnés). Source de vérité unique du
dernier reset traité : PipelineState.last_reset_iso (global, pas par serveur).

Arbre de décision (chaque reset est un reset quotidien) :
- TOUJOURS    → secteurs oubliés + Eververse (republier)
- VENDREDI    → Xûr arrive : supprime tout + republie tout (statut + catégories)
- MARDI       → Xûr part (supprime catégories + édite statut) + raids/donjons + Ada-1
- FIN DE RESET→ vérification d'existence (point 4) : republie SANS ping les
  messages persistants disparus de Discord (à chaque reset, pas chaque minute).

Détection « reset déjà traité » : comparaison de last_reset() (instant pur du
dernier reset survenu) avec l'iso persisté. On n'avance l'iso QU'APRÈS succès.

Hold mode (point 9) : si un fetch Bungie lève BungieMaintenanceError (API en
maintenance, typiquement au reset du mardi), on N'AVANCE PAS l'état et on
retente au poll suivant — chaque minute jusqu'au rétablissement. Le poll/min
EST la boucle de retry ; le hash-skip évite de reposter ce qui a déjà été
publié avant l'échec (seule la partie en échec est réellement retentée).

Refresh manuel (/refresh) : publication forcée SANS ping (`ping=False`) —
exception assumée à la règle « repost = ping ». Le reset automatique, lui,
notifie toujours (ping par défaut)."""
import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.bungie.errors import BungieMaintenanceError
from bot.bungie.reset import FRIDAY, TUESDAY, last_reset
from bot.discord.handlers import ada as ada_handler
from bot.discord.handlers import eververse as eververse_handler
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
        self._hold = False  # True tant que l'API Bungie est en maintenance
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    # ---------- Détection du reset (automatique) ----------
    @tasks.loop(minutes=1)
    async def poll(self):
        current = last_reset().isoformat()
        if current == self.state.last_reset_iso:
            return  # reset déjà traité (rattrapage automatique au redémarrage)

        weekday = last_reset().weekday()
        if self._hold:
            log.debug("[Pipeline] Hold mode — nouvelle tentative de traitement du reset.")
        else:
            log.info(f"[Pipeline] Nouveau reset détecté (weekday={weekday}).")

        try:
            await self._process_reset(weekday)
        except BungieMaintenanceError as e:
            if not self._hold:
                log.warning(
                    f"[Pipeline] API Bungie en maintenance ({e}) — hold mode activé. "
                    "Le reset sera retenté chaque minute jusqu'au rétablissement."
                )
                self._hold = True
            return  # on n'avance PAS l'état → retry au prochain poll
        except Exception as e:
            log.error(f"[Pipeline] Traitement du reset échoué : {e}")
            return  # on n'avance pas non plus (erreur transitoire éventuelle)

        if self._hold:
            log.info("[Pipeline] API Bungie rétablie — reset traité, hold mode levé.")
            self._hold = False

        self.state.last_reset_iso = current
        self.state.save()

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()

    async def _process_reset(self, weekday: int):
        # TOUJOURS : secteurs oubliés + Eververse (tout reset est quotidien).
        await weekly_handler.publish_lost_sectors(self.bot, self.weekly_state)
        await eververse_handler.publish(self.bot, self.eververse_state)

        # VENDREDI : Xûr arrive.
        if weekday == FRIDAY:
            await xur_handler.publish_arrival(self.bot, self.xur_state)

        # MARDI : Xûr part + raids/donjons + Ada-1 (resets hebdo).
        # publish_raid_dungeon orchestre la purge unique du cache puis publie
        # les deux messages distincts (raids puis donjons). Ada-1 (vendor hebdo)
        # publie ensuite son propre message (cache d'icônes séparé, banners/ada/).
        if weekday == TUESDAY:
            await xur_handler.mark_departed(self.bot, self.xur_state)
            await weekly_handler.publish_raid_dungeon(self.bot, self.weekly_state)
            await ada_handler.publish(self.bot, self.ada_state)

        # FIN DE RESET : réparation des messages disparus (sans ping).
        await self._verify_existence()

    async def _verify_existence(self):
        """Point 4 : republie SANS ping les messages persistants supprimés à la
        main. Couvre tous les topics. Une BungieMaintenanceError est RE-LEVÉE
        pour que le reset entier soit considéré en échec (hold mode) ; les
        autres erreurs sont seulement loguées."""
        try:
            await weekly_handler.restore(self.bot, self.weekly_state)
            await xur_handler.restore(self.bot, self.xur_state)
            await eververse_handler.restore(self.bot, self.eververse_state)
            await ada_handler.restore(self.bot, self.ada_state)
        except BungieMaintenanceError:
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
            "xur": self._refresh_xur,
            "eververse": self._refresh_eververse,
            "ada": self._refresh_ada,
        }

    @app_commands.command(
        name="refresh",
        description="",
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
            await fn()
        except BungieMaintenanceError:
            await interaction.followup.send(
                "🔧 L'API Bungie est en maintenance. Réessaie plus tard — "
                "les features se réactualiseront automatiquement au rétablissement.",
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