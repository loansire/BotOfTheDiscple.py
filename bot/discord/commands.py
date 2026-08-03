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
    "bot.discord.cogs.distortion",
)

# Commandes réservées au SEUL serveur de contrôle (CONTROL_GUILD_ID) :
# enregistrées et visibles uniquement dans ce serveur, totalement invisibles
# partout ailleurs. Chaque nom doit correspondre à une commande déclarée par
# un cog chargé ci-dessus (sinon elle est simplement ignorée avec un warning).
CONTROL_GUILD_COMMANDS = (
    "refresh",    # cog Pipeline — administration (réservée à l'auteur)
    "wish-wall",  # cog WishWall — embed interactif de vœux
)


def _scope_commands_to_control_guild(bot: commands.Bot) -> None:
    """Restreint certaines commandes au SEUL serveur de contrôle (CONTROL_GUILD_ID).

    Ces commandes sont enregistrées globalement par leurs cogs respectifs (au
    load). On les retire du périmètre global puis on les ré-ajoute en tant que
    commandes DE GUILDE : elles n'apparaissent alors que dans le serveur de
    contrôle, et restent invisibles sur tous les autres serveurs où le bot est
    invité.

    Fail-safe : si CONTROL_GUILD_ID n'est pas défini, ces commandes ne sont
    ré-ajoutées nulle part → jamais exposées publiquement par oubli. On loggue
    un warning explicite pour signaler qu'il faut renseigner CONTROL_GUILD_ID
    au .env."""
    guild = discord.Object(id=CONTROL_GUILD_ID) if CONTROL_GUILD_ID else None

    for name in CONTROL_GUILD_COMMANDS:
        cmd = bot.tree.get_command(name)
        if cmd is None:
            log.warning(
                f"[Commands] /{name} introuvable dans l'arbre — scoping ignoré."
            )
            continue

        bot.tree.remove_command(name)  # retrait du périmètre global
        if guild is not None:
            bot.tree.add_command(cmd, guild=guild)
            log.info(
                f"[Commands] /{name} restreinte au serveur de contrôle {CONTROL_GUILD_ID}."
            )
        else:
            log.warning(
                f"[Commands] CONTROL_GUILD_ID absent du .env : /{name} désactivée "
                "(ajoute CONTROL_GUILD_ID=<id_de_ton_serveur> pour l'activer)."
            )


async def setup(bot: commands.Bot):
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            log.info(f"Cog chargé : {cog}")
        except Exception as e:
            log.error(f"Échec du chargement de {cog} : {e}")

    # Doit être fait APRÈS le chargement des cogs qui déclarent ces commandes
    # (Pipeline → /refresh, WishWall → /wish-wall).
    _scope_commands_to_control_guild(bot)