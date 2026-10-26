# -*- coding: utf-8 -*-
import asyncio

from bot.config import DISCORD_TOKEN
from bot.discord.client import bot
from bot.utils.http import close_session
from bot.utils.logger import log


async def main():
    try:
        async with bot:
            await bot.load_extension("bot.discord.commands")
            log.info("Démarrage du bot...")
            await bot.start(DISCORD_TOKEN)
    finally:
        await close_session()


if __name__ == "__main__":
    asyncio.run(main())