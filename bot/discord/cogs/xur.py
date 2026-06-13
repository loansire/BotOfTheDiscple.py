# -*- coding: utf-8 -*-
"""Cog Xûr : publie l'inventaire hebdomadaire du marchand exotique.

Multi-message : Xûr peut occuper plusieurs messages (limite Discord 10
images/message). La publication est gérée ici (pas par publish_persistent_view,
mono-message) : on supprime les anciens messages mémorisés, on poste les
nouveaux, et on enregistre tous leurs IDs.

Logique calée sur le reset quotidien Bungie (cf. weekly.py) :
- VENDREDI -> résout les vendors et REPOSTE la série de messages (le repost
  ré-active la notification + le ping rôle, sur le 1er message seulement).
- MARDI    -> ÉDITE le 1er message en « Xûr est reparti » et SUPPRIME les
  autres (édition in-place -> pas de notification).
- Autres jours -> skip.

/xur-reset (réservé à l'auteur) force le repost via state.invalidate().
"""
import hashlib

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.bungie.reset import last_reset
from bot.embeds.xur import build_xur_departed_view, build_xur_views
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


def _resolve_destination(guild, dest_id, is_thread: bool):
    """Salon texte ou thread (même logique que le publisher)."""
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
            return  # reset déjà traité (rattrapage au redémarrage)

        weekday = last_reset().weekday()
        try:
            if weekday == FRIDAY:
                log.info("[Xûr] Reset du vendredi — publication de l'inventaire.")
                await self._publish()
            elif weekday == TUESDAY:
                log.info("[Xûr] Reset du mardi — Xûr est parti, édition.")
                await self._mark_departed()
            else:
                log.debug("[Xûr] Reset ordinaire — rien à faire.")
        except Exception as e:
            log.error(f"[Xûr] Échec du traitement du reset : {e}")
            return

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
        item_hashes = [str(it.item_hash) for v in vendors for it in v.items]
        xur_hash = _content_hash(item_hashes)

        for guild_id, dest_id, info in iter_subscribers(TOPIC):
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            dest = _resolve_destination(guild, dest_id, info.get("is_thread", False))
            if dest is None:
                continue

            entry = self.state.get(guild_id)
            if entry.get("message_ids") and entry.get("hash") == xur_hash:
                continue  # contenu inchangé -> rien à faire

            await self._repost_guild(guild, dest, vendors, departure, info, xur_hash)

    async def _repost_guild(self, guild, dest, vendors, departure, info, xur_hash):
        """Supprime les anciens messages du guild puis poste la nouvelle série."""
        # 1) Suppression des anciens messages mémorisés.
        for mid in self.state.get_message_ids(guild.id):
            try:
                old = await dest.fetch_message(int(mid))
                await old.delete()
            except discord.NotFound:
                pass
            except discord.DiscordException as e:
                log.warning(f"[Xûr] Suppression ancien message échouée : {e}")

        # 2) Construction des vues (1+ par vendor) et post séquentiel.
        views = await build_xur_views(vendors, departure_unix=departure)
        role_id = info.get("role")
        new_ids: list = []

        for idx, (view, files) in enumerate(views):
            # Ping rôle uniquement sur le PREMIER message de la série.
            if idx == 0 and role_id:
                view.add_item(discord.ui.TextDisplay(f"<@&{role_id}>"))
                allowed = discord.AllowedMentions(roles=True)
            else:
                allowed = discord.AllowedMentions.none()
            try:
                sent = await dest.send(view=view, files=files, allowed_mentions=allowed)
                new_ids.append(str(sent.id))
            except discord.DiscordException as e:
                log.error(f"[Xûr] Envoi message {idx} échoué dans {dest} : {e}")

        if new_ids:
            self.state.set(guild.id, message_ids=new_ids, content_hash=xur_hash)
            self.state.save()
            log.info(f"[Xûr] {len(new_ids)} message(s) publié(s) dans {guild.name}.")

    # ---------- Départ (mardi) : édition in-place ----------
    async def _mark_departed(self):
        """Édite le 1er message de chaque guild en « Xûr est reparti » et
        supprime les autres. Édition -> aucune notification."""
        return_unix = next_arrival_unix()
        view = build_xur_departed_view(return_unix)

        # Résolution salon par guild via les abonnements.
        dest_by_guild: dict = {}
        for guild_id, dest_id, info in iter_subscribers(TOPIC):
            dest_by_guild[guild_id] = (dest_id, info.get("is_thread", False))

        for guild_id, entry in self.state.iter_guilds():
            message_ids = entry.get("message_ids", [])
            if not message_ids:
                continue
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            dest_info = dest_by_guild.get(guild_id)
            if not dest_info:
                continue
            dest = _resolve_destination(guild, dest_info[0], dest_info[1])
            if dest is None:
                continue

            # 1er message -> édité « parti ».
            first_id = message_ids[0]
            try:
                msg = await dest.fetch_message(int(first_id))
                await msg.edit(view=view, attachments=[])
            except discord.NotFound:
                log.warning(f"[Xûr] 1er message {first_id} introuvable (guild {guild_id}).")
            except discord.DiscordException as e:
                log.error(f"[Xûr] Édition départ échouée (guild {guild_id}) : {e}")

            # Autres messages -> supprimés.
            for mid in message_ids[1:]:
                try:
                    extra = await dest.fetch_message(int(mid))
                    await extra.delete()
                except discord.NotFound:
                    pass
                except discord.DiscordException as e:
                    log.warning(f"[Xûr] Suppression message {mid} échouée : {e}")

            # On ne conserve que le 1er message dans le state.
            self.state.set(
                guild_id, message_ids=[first_id], content_hash=entry.get("hash", "")
            )
        self.state.save()

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
            self.state.invalidate()  # force le repost (hashes effacés)
            await self._publish()
        except Exception as e:
            log.error(f"[Xûr] /xur-reset a échoué : {e}")
            await interaction.followup.send(":x: Échec de la republication.", ephemeral=True)
            return
        await interaction.followup.send("✅ Inventaire de Xûr actualisé.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Xur(bot))