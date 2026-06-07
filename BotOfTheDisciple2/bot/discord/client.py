# -*- coding: utf-8 -*-
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True  # requis pour l'interception maintenance (on_message)

bot = commands.Bot(command_prefix="/", intents=intents)