# -*- coding: utf-8 -*-
"""Cog Xûr : publie l'inventaire hebdomadaire du marchand exotique.

Logique calée sur le reset quotidien Bungie (cf. weekly.py) :
- VENDREDI (reset) → résout les 3 vendors et REPOSTE un message persistant
  (le repost ré-active la notification + le ping rôle : on VEUT prévenir de
  l'arrivée de Xûr).
- MARDI (reset)    → ÉDITE le message existant en « Xûr est reparti » (édition
  in-place, donc PAS de notification : son départ ne doit pas spammer).
- Autres jours     → skip.

/xur-reset (réservé à l'auteur) force le repost via state.invalidate().

L'édition du mardi ne passe PAS par publish_persistent_view (qui supprime +
reposte) : on utilise une méthode maison qui fetch_message + edit.
"""
import hashlib

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.bungie.reset import last_reset
from bot.discord.publisher import publish_persistent_view
from bot.embeds.xur import build_xur_departed_view, build_xur_view
from bot.features.xur import get_xur, next_arrival_unix, next_departure_unix
from bot.features.xur.constants import FRIDAY, TUESDAY
from bot.features.xur.state import TOPIC, XurMessageState
from bot.utils.logger import log
from bot.utils.subscriptions import iter_subscribers

# Seul utilisateur autorisé à déclencher /xur-reset (auteur du bot).
OWNER_ID = 222465158075777035


def _content_hash(parts) -> str:
    """Hash court et stable d'une liste de chaînes (ordre indépendant)."""
    joined = "|".join(sorted(parts))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def _resolve_destination(guild, dest_id: str, is_thread: bool):
    """Identique à la logique du publisher (salon texte ou thread)."""
    if is_thread:
        th = guild.get_thread(int(dest_id))
        return th if isinstance(th, discord.Thread) else None
    ch = guild.get_channel(int(dest_id))
    return ch if isinstance(ch, discord.TextChannel) else None


class Xur(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = XurMessageState()
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
        try:
            if weekday == FRIDAY:
                log.info("[Xûr] Reset du vendredi — publication de l'inventaire.")
                await self._publish()
            elif weekday == TUESDAY:
                log.info("[Xûr] Reset du mardi — Xûr est parti, édition du message.")
                await self._mark_departed()
            else:
                log.debug("[Xûr] Reset ordinaire — rien à faire (Xûr inchangé).")
        except Exception as e:
            log.error(f"[Xûr] Échec du traitement du reset : {e}")
            return

        # On ne mémorise le reset comme traité qu'après succès.
        self.state.last_reset_iso = current
        self.state.save()

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()

    # ---------- Publication (vendredi) ----------
    async def _publish(self):
        vendors = await get_xur()
        if not vendors:
            log.warning("[Xûr] Aucun vendor récupéré — publication annulée.")
            return

        departure = next_departure_unix()
        item_hashes = [
            str(it.item_hash) for v in vendors for it in v.items
        ]
        xur_hash = _content_hash(item_hashes)

        await publish_persistent_view(
            self.bot,
            TOPIC,
            build_view=lambda data=vendors, dep=departure: self._build(data, dep),
            content_hash=xur_hash,
            state=self.state,
        )

    async def _build(self, vendors, departure):
        return await build_xur_view(vendors, departure_unix=departure)

    # ---------- Départ (mardi) : édition in-place ----------
    async def _mark_departed(self):
        """Édite chaque message Xûr posté vendredi en « Xûr est reparti ».

        Édition (pas de repost) → aucune notification. On parcourt les
        abonnés pour résoudre le salon, puis on fetch + edit le message
        mémorisé dans le state."""
        return_unix = next_arrival_unix()
        view = build_xur_departed_view(return_unix)

        # Résolution salon par guild via les abonnements (is_thread).
        dest_by_guild: dict[str, tuple] = {}
        for guild_id, dest_id, info in iter_subscribers(TOPIC):
            dest_by_guild[guild_id] = (dest_id, info.get("is_thread", False))

        for guild_id, message_id in self.state.iter_messages(TOPIC):
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            dest_info = dest_by_guild.get(guild_id)
            if not dest_info:
                continue
            dest = _resolve_destination(guild, dest_info[0], dest_info[1])
            if dest is None:
                continue
            try:
                msg = await dest.fetch_message(int(message_id))
                await msg.edit(view=view, attachments=[])
            except discord.NotFound:
                log.warning(f"[Xûr] Message {message_id} introuvable (guild {guild_id}).")
            except discord.DiscordException as e:
                log.error(f"[Xûr] Édition départ échouée (guild {guild_id}) : {e}")

    # ---------- Commande admin (manuelle) ----------
    @app_commands.command(
        name="xur-reset",
        description="Republie/actualise l'inventaire de Xûr (force le repost).",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def xur_reset(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "🚫 Cette commande est réservée à l'auteur du bot.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            # Force le repost : invalide les hashes pour que publish supprime +
            # reposte systématiquement (réactive le ping rôle).
            self.state.invalidate()
            await self._publish()
        except Exception as e:
            log.error(f"[Xûr] /xur-reset a échoué : {e}")
            await interaction.followup.send(":x: Échec de la republication.", ephemeral=True)
            return
        await interaction.followup.send("✅ Inventaire de Xûr actualisé.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Xur(bot))
