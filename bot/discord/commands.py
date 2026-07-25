# -*- coding: utf-8 -*-
import discord
from discord.ext import commands

from bot.config import CONTROL_GUILD_ID
from bot.utils.logger import log

# Liste centrale des cogs à charger
COGS = (
    "bot.discord.cogs.core",
    "bot.discord.cogs.maintenance",
    "bot.discord.cogs.wishwall",
    "bot.discord.cogs.alerts",
    "bot.discord.cogs.configbot",
    "bot.discord.cogs.pipeline",
)


def _scope_refresh_to_control_guild(bot: commands.Bot) -> None:
    """Restreint /refresh au SEUL serveur de contrôle (CONTROL_GUILD_ID).

    /refresh est enregistrée globalement par le cog Pipeline (au load). On la
    retire du périmètre global puis on la ré-ajoute en tant que commande DE
    GUILDE : elle n'apparaît alors que dans le serveur de contrôle, et reste
    invisible sur tous les autres serveurs où le bot est invité.

    Fail-safe : si CONTROL_GUILD_ID n'est pas défini, /refresh n'est ré-ajoutée
    nulle part → jamais exposée publiquement par oubli. On loggue un warning
    explicite pour signaler qu'il faut renseigner CONTROL_GUILD_ID au .env."""
    cmd = bot.tree.get_command("refresh")
    if cmd is None:
        log.warning("[Commands] /refresh introuvable dans l'arbre — scoping ignoré.")
        return

    bot.tree.remove_command("refresh")  # retrait du périmètre global
    if CONTROL_GUILD_ID:
        bot.tree.add_command(cmd, guild=discord.Object(id=CONTROL_GUILD_ID))
        log.info(
            f"[Commands] /refresh restreinte au serveur de contrôle {CONTROL_GUILD_ID}."
        )
    else:
        log.warning(
            "[Commands] CONTROL_GUILD_ID absent du .env : /refresh désactivée "
            "(ajoute CONTROL_GUILD_ID=<id_de_ton_serveur> pour l'activer)."
        )


async def setup(bot: commands.Bot):
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            log.info(f"Cog chargé : {cog}")
        except Exception as e:
            log.error(f"Échec du chargement de {cog} : {e}")

    # Doit être fait APRÈS le chargement du cog Pipeline (qui déclare /refresh).
    _scope_refresh_to_control_guild(bot)