# -*- coding: utf-8 -*-
"""Cog Xûr : publie l'inventaire hebdomadaire du marchand exotique (4 messages).

Structure des messages par guild :
- Message 1 (STATUT) : « Xûr est là / n'est pas là » + date départ/retour.
  Persistant — édité in-place, jamais supprimé. Porte le ping rôle au repost
  du vendredi.
- Messages 2-4 (CATÉGORIES) : Armes / Armures / Matériaux. Supprimés puis
  republiés le vendredi ; supprimés le mardi.

Logique calée sur le reset quotidien Bungie (cf. weekly.py) :
- VENDREDI -> « est là » : édite/poste le statut (+ ping rôle), supprime puis
  republie les 3 catégories (le repost ré-active la notification).
- MARDI    -> « n'est pas là » : édite le statut (pas de notif) et supprime
  les catégories.
- Autres jours -> skip (Xûr inchangé).

/xur-reset (réservé à l'auteur) force le repost via state.invalidate().
"""
import hashlib

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.bungie.reset import last_reset
from bot.embeds.xur import build_xur_category_views, build_xur_status_view
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
                log.info("[Xûr] Reset du mardi — Xûr est parti.")
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

    # ---------- Helpers messages ----------
    async def _delete_messages(self, dest, ids) -> None:
        """Supprime une liste de messages (ignore ceux déjà absents)."""
        for mid in ids:
            try:
                msg = await dest.fetch_message(int(mid))
                await msg.delete()
            except discord.NotFound:
                pass
            except discord.DiscordException as e:
                log.warning(f"[Xûr] Suppression message {mid} échouée : {e}")

    async def _upsert_status(
        self, dest, guild_id, view, role_id, *, repost: bool
    ) -> None:
        """Édite le message statut s'il existe, sinon le poste.

        `repost=True` (vendredi) → si le message existe on l'édite (donc pas de
        nouvelle notif d'arrivée portée par le statut lui-même) ; à la première
        publication on le poste avec le ping rôle. `repost=False` (mardi) →
        édition simple, jamais de ping."""
        status_id = self.state.status_id(guild_id)

        # Tentative d'édition si un message statut est connu.
        if status_id:
            try:
                msg = await dest.fetch_message(int(status_id))
                await msg.edit(view=view)
                return
            except discord.NotFound:
                log.warning(
                    f"[Xûr] Message statut {status_id} introuvable (guild {guild_id}) "
                    "— repost."
                )
            except discord.DiscordException as e:
                log.error(f"[Xûr] Édition statut échouée (guild {guild_id}) : {e}")
                return

        # Pas de statut connu (ou disparu) → on le poste.
        if repost and role_id:
            view.add_item(discord.ui.TextDisplay(f"<@&{role_id}>"))
            allowed = discord.AllowedMentions(roles=True)
        else:
            allowed = discord.AllowedMentions.none()
        try:
            sent = await dest.send(view=view, allowed_mentions=allowed)
            self.state.set(guild_id, status_id=str(sent.id))
        except discord.DiscordException as e:
            log.error(f"[Xûr] Envoi statut échoué (guild {guild_id}) : {e}")

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

            # Contenu inchangé ET catégories déjà présentes → rien à faire.
            if (
                self.state.content_hash(guild_id) == xur_hash
                and self.state.category_ids(guild_id)
            ):
                # On rafraîchit tout de même le statut (date de départ).
                status_view = build_xur_status_view(True, departure_unix=departure)
                await self._upsert_status(
                    dest, guild_id, status_view, info.get("role"), repost=True
                )
                self.state.save()
                continue

            await self._repost_guild(guild, dest, vendors, departure, info, xur_hash)

    async def _repost_guild(self, guild, dest, vendors, departure, info, xur_hash):
        """Statut « est là » + suppression/repost des 3 messages catégories."""
        guild_id = str(guild.id)
        role_id = info.get("role")

        # 1) Message statut « est là » (édité si présent, sinon posté + ping).
        status_view = build_xur_status_view(True, departure_unix=departure)
        await self._upsert_status(dest, guild_id, status_view, role_id, repost=True)

        # 2) Suppression des anciens messages catégories.
        await self._delete_messages(dest, self.state.category_ids(guild_id))

        # 3) Repost des catégories (sans ping : le statut porte la notif).
        views = await build_xur_category_views(vendors)
        new_ids: list = []
        for view, files in views:
            try:
                sent = await dest.send(
                    view=view, files=files, allowed_mentions=discord.AllowedMentions.none()
                )
                new_ids.append(str(sent.id))
            except discord.DiscordException as e:
                log.error(f"[Xûr] Envoi catégorie échoué dans {dest} : {e}")

        self.state.set(guild_id, category_ids=new_ids, content_hash=xur_hash)
        self.state.save()
        log.info(
            f"[Xûr] Statut + {len(new_ids)} catégorie(s) publié(s) dans {guild.name}."
        )

    # ---------- Départ (mardi) ----------
    async def _mark_departed(self):
        """Édite le statut en « n'est pas là » (+ date de retour) et supprime
        les messages catégories. Édition du statut -> aucune notification."""
        return_unix = next_arrival_unix()

        # Résolution salon par guild via les abonnements.
        dest_by_guild: dict = {}
        for guild_id, dest_id, info in iter_subscribers(TOPIC):
            dest_by_guild[guild_id] = (dest_id, info.get("is_thread", False))

        for guild_id, entry in self.state.iter_guilds():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            dest_info = dest_by_guild.get(guild_id)
            if not dest_info:
                continue
            dest = _resolve_destination(guild, dest_info[0], dest_info[1])
            if dest is None:
                continue

            # Statut → « n'est pas là » (édition in-place, pas de ping).
            status_view = build_xur_status_view(False, return_unix=return_unix)
            await self._upsert_status(
                dest, guild_id, status_view, role_id=None, repost=False
            )

            # Catégories → supprimées.
            await self._delete_messages(dest, entry["category_ids"])
            self.state.clear_categories(guild_id)

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