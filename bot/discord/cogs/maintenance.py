# -*- coding: utf-8 -*-
"""Maintenances Destiny / Marathon : détection Zendesk + déclaration manuelle.

Un seul enregistrement « actif » par jeu (state.json), ÉCRASÉ à chaque
déclencheur Zendesk ou mise à jour manuelle. Chaque écrasement republie un
NOUVEAU message (jamais d'édition). À l'expiration de la fin, seul un DM de
rappel part vers l'auteur du bot : l'enregistrement reste en base et le
message de fin n'est publié que par /maintenance-delete."""
import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.core.config import OWNER_ID
from bot.core.logger import log
from bot.features.maintenance import (
    extract_window,
    format_discord_message,
    get_maintenances,
)
from bot.features.maintenance.formatter import GAME_LABELS
from bot.features.maintenance.manual import ManualInputError, build_manual_window
from bot.features.maintenance.state import MaintenanceState
from bot.features.maintenance.view import build_maintenance_embed, build_maintenance_end_embed
from bot.publishing.event import publish_to_subscribers

GAMES = ("destiny", "marathon")
GAME_CHOICES = [app_commands.Choice(name=GAME_LABELS[g], value=g) for g in GAMES]

# Intervalle mini entre deux requêtes Zendesk d'un même jeu (anti-429).
FETCH_INTERVAL = 180  # secondes
# Fin supposée quand la maintenance n'annonce pas d'heure de retour.
NO_END_GRACE = 12 * 3600  # secondes
# Délai avant de retenter un DM de rappel qui a échoué.
DM_RETRY = 600  # secondes


def _signature(window: dict) -> tuple:
    return window.get("offline_unix"), window.get("online_unix"), window.get("event_type")


class MaintenanceModal(discord.ui.Modal):
    day = discord.ui.TextInput(
        label="Jour (en anglais, sans année)",
        placeholder="October 20",
        max_length=30,
    )
    start = discord.ui.TextInput(
        label="Arrêt des serveurs",
        placeholder="8:30 AM PDT",
        max_length=30,
    )
    stop = discord.ui.TextInput(
        label="Retour des serveurs",
        placeholder="10:00 AM PDT",
        max_length=30,
    )
    comment = discord.ui.TextInput(
        label="Description (facultatif)",
        style=discord.TextStyle.long,
        placeholder="Update 1.0.6, prolongée jusqu'à 11:00 AM PDT…",
        required=False,
        max_length=500,
    )

    def __init__(self, cog: "Maintenance", game: str, default_comment: str | None = None):
        super().__init__(title=f"Maintenance {GAME_LABELS[game]}")
        self.cog = cog
        self.game = game
        self.comment.default = default_comment

    async def on_submit(self, interaction: discord.Interaction):
        try:
            window = build_manual_window(
                self.game, self.day.value, self.start.value, self.stop.value, self.comment.value
            )
        except ManualInputError as e:
            await interaction.response.send_message(f":x: {e}", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await self.cog.declare(self.game, window)
        await interaction.followup.send(
            f"✅ Maintenance {window['game_label']} publiée : arrêt <t:{window['offline_unix']}:F>, "
            f"retour <t:{window['online_unix']}:F>.",
            ephemeral=True,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        log.error(f"[Maintenance] Modal en échec ({self.game}) : {error!r}")
        if interaction.response.is_done():
            await interaction.followup.send(":x: Échec de la publication.", ephemeral=True)
        else:
            await interaction.response.send_message(":x: Échec de la publication.", ephemeral=True)


class Maintenance(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = MaintenanceState()
        # Sérialise poll, expiration et commandes (même état, même fichier).
        self._lock = asyncio.Lock()
        self._next_fetch = {game: 0.0 for game in GAMES}
        self._dm_retry_at = {game: 0.0 for game in GAMES}
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    # ---------- Tâche récurrente ----------
    @tasks.loop(minutes=1)
    async def poll(self):
        log.debug("[Maintenance] poll #%d", self.poll.current_loop)
        results = await asyncio.gather(
            *(self._tick(game) for game in GAMES), return_exceptions=True
        )
        for game, result in zip(GAMES, results):
            if isinstance(result, Exception):
                log.error(f"[Maintenance] Erreur de poll pour {game} : {result}")

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()

    async def _tick(self, game: str):
        try:
            if time.monotonic() >= self._next_fetch[game]:
                self._next_fetch[game] = time.monotonic() + FETCH_INTERVAL
                await self._check_game(game)
        finally:
            await self._check_expiry(game)

    # ---------- Zendesk ----------
    async def _check_game(self, game: str):
        st = self.state.get(game)
        # déjà filtré "offline futur" ; non parsé si l'article n'a pas changé
        data = await get_maintenances(game, known_updated_at=st.get("article_updated_at"))
        if data is None or data.get("unchanged"):
            return  # erreur, ou pas de changement d'article → rien à faire

        window = extract_window(data)
        async with self._lock:
            st = self.state.get(game)
            new_state = {**st, "article_updated_at": data.get("article_updated_at")}
            new_state.pop("announced_offline_iso", None)  # ancien format

            if window is None:
                self.state.set(game, new_state)
                await self.state.save()
                return

            record = {**window, "source": "zendesk", "copy_text": format_discord_message(data)}
            previous = st.get("active")
            if previous:
                same = _signature(previous) == _signature(record)
            else:  # état d'avant /maintenance-update : même mise hors ligne = déjà annoncée
                same = window["offline_iso"] == st.get("announced_offline_iso")

            # Écrasement systématique de l'enregistrement actif.
            new_state["active"] = record
            if same:
                self.state.set(game, new_state)
                await self.state.save()
                return

            new_state["expiry_notified"] = False
            await self._announce(game, record)
            self.state.set(game, new_state)
            await self.state.save()
            log.info(f"[Maintenance] Alerte publiée pour {game} ({window['offline_iso']})")

    # ---------- Expiration ----------
    async def _check_expiry(self, game: str):
        async with self._lock:
            st = self.state.get(game)
            active = st.get("active")
            if not active or st.get("expiry_notified"):
                return
            end = active.get("online_unix") or (active["offline_unix"] + NO_END_GRACE)
            if time.time() < end or time.monotonic() < self._dm_retry_at[game]:
                return

            label = GAME_LABELS.get(game, game)
            sent = await self._dm_owner(
                f"⏰ **BotOfTheDisciple** : la maintenance **{label}** devait se terminer "
                f"<t:{int(end)}:R>.\n"
                f"Si elle est finie, tape `/maintenance-delete jeu:{label}` pour publier le "
                "message de fin et la clear (rien n'est publié automatiquement)."
            )
            if sent:
                self.state.set(game, {**st, "expiry_notified": True})
                await self.state.save()
            else:
                self._dm_retry_at[game] = time.monotonic() + DM_RETRY

    async def _dm_owner(self, content: str) -> bool:
        try:
            user = self.bot.get_user(OWNER_ID) or await self.bot.fetch_user(OWNER_ID)
            await user.send(content)
            return True
        except discord.DiscordException as e:
            log.warning(f"[Maintenance] DM de rappel impossible : {e}")
            return False

    # ---------- Publication ----------
    async def _announce(self, game: str, record: dict, *, ping: bool = True):
        await publish_to_subscribers(
            self.bot,
            f"maintenance_{game}",
            build=lambda: build_maintenance_embed(record, record.get("copy_text")),
            ping=ping,
        )

    async def declare(self, game: str, window: dict):
        """Mise à jour manuelle : écrase l'enregistrement actif et republie."""
        async with self._lock:
            st = self.state.get(game)
            self.state.set(game, {**st, "active": window, "expiry_notified": False})
            await self.state.save()
            await self._announce(game, window)
        log.info(f"[Maintenance] Déclaration manuelle pour {game} ({window['offline_unix']})")

    async def republish(self, game: str, *, ping: bool = False) -> bool:
        """Republie l'enregistrement actif (/refresh). False s'il n'y en a pas."""
        async with self._lock:
            active = self.state.get(game).get("active")
            if not active:
                return False
            await self._announce(game, active, ping=ping)
            return True

    async def finish(self, game: str) -> bool:
        """Publie le message de fin puis clear l'enregistrement actif."""
        async with self._lock:
            st = self.state.get(game)
            if not st.get("active"):
                return False
            await publish_to_subscribers(
                self.bot, f"maintenance_{game}", build=lambda: build_maintenance_end_embed(game)
            )
            self.state.set(game, {k: v for k, v in st.items() if k not in ("active", "expiry_notified")})
            await self.state.save()
        log.info(f"[Maintenance] Maintenance {game} terminée et clearée")
        return True

    # ---------- Commandes (auteur du bot) ----------
    @staticmethod
    async def _owner_only(interaction: discord.Interaction) -> bool:
        if interaction.user.id == OWNER_ID:
            return True
        await interaction.response.send_message(
            "🚫 Cette commande est réservée à l'auteur du bot.", ephemeral=True
        )
        return False

    @app_commands.command(
        name="maintenance-update",
        description="Déclare ou met à jour manuellement une maintenance (avec ping).",
    )
    @app_commands.describe(jeu="Jeu concerné")
    @app_commands.choices(jeu=GAME_CHOICES)
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def maintenance_update(self, interaction: discord.Interaction, jeu: str):
        if not await self._owner_only(interaction):
            return
        active = self.state.get(jeu).get("active") or {}
        await interaction.response.send_modal(
            MaintenanceModal(self, jeu, default_comment=active.get("event_type"))
        )

    @app_commands.command(
        name="maintenance-delete",
        description="Termine une maintenance : publie le message de fin et la clear.",
    )
    @app_commands.describe(jeu="Jeu concerné")
    @app_commands.choices(jeu=GAME_CHOICES)
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def maintenance_delete(self, interaction: discord.Interaction, jeu: str):
        if not await self._owner_only(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        label = GAME_LABELS[jeu]
        if await self.finish(jeu):
            await interaction.followup.send(
                f"🗑️ Maintenance {label} clearée, message de fin publié.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f":x: Aucune maintenance {label} enregistrée.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Maintenance(bot))
