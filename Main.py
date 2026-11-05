# -*- coding: utf-8 -*-
import asyncio

from bot.core.config import DISCORD_TOKEN
from bot.discord.client import bot
from bot.core.http import close_session
from bot.core.logger import log
from bot.storage import close_storage, open_storage


async def main():
    try:
        # La base doit être prête AVANT le chargement des cogs : leurs états
        # sont lus en mémoire dès l'initialisation.
        await open_storage()
        async with bot:
            await bot.load_extension("bot.discord.commands")
            log.info("Démarrage du bot...")
            await bot.start(DISCORD_TOKEN)
    finally:
        await close_session()
        await close_storage()


if __name__ == "__main__":
    asyncio.run(main())
