# -*- coding: utf-8 -*-
import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds.randomizer import build_randomizer_embed
from bot.features import randomizer as feature


def _make_autocomplete(keys: list[str]):
    async def autocomplete(interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=item, value=item)
            for item in keys
            if current.lower() in item.lower()
        ][:25]

    return autocomplete


class Randomizer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.raid_data = feature.load_data(feature.RAID_JSON)
        self.dungeon_data = feature.load_data(feature.DUNGEON_JSON)

        # Autocomplétions liées aux données chargées
        self._raid_ac = _make_autocomplete(list(self.raid_data.keys()))
        self._dungeon_ac = _make_autocomplete(list(self.dungeon_data.keys()))
        self.random_raidpick.autocomplete("raid1")(self._raid_ac)
        self.random_raidpick.autocomplete("raid2")(self._raid_ac)
        self.random_raidpick.autocomplete("raid3")(self._raid_ac)
        self.random_raidpick.autocomplete("raid4")(self._raid_ac)
        self.random_raidpick.autocomplete("raid5")(self._raid_ac)
        self.random_raidpick.autocomplete("raid6")(self._raid_ac)
        self.random_dungeonpick.autocomplete("donjon1")(self._dungeon_ac)
        self.random_dungeonpick.autocomplete("donjon2")(self._dungeon_ac)
        self.random_dungeonpick.autocomplete("donjon3")(self._dungeon_ac)

    async def _pick_and_send(self, interaction, choices, data, title, item_type):
        chosen, counts = feature.weighted_pick(choices, data)
        embed, files = build_randomizer_embed(
            chosen=chosen, counts=counts, data=data, title=title, item_type=item_type
        )
        await interaction.response.send_message(embed=embed, files=files)

    @app_commands.command(name="randomizer-raid", description="Choisir aléatoirement un raid")
    @app_commands.describe(
        raid1="Premier choix de raid",
        raid2="Deuxième choix de raid",
        raid3="Troisième choix de raid",
        raid4="Quatrième choix de raid",
        raid5="Cinquième choix de raid",
        raid6="Sixième choix de raid",
    )
    async def random_raidpick(
        self,
        interaction: discord.Interaction,
        raid1: str = None,
        raid2: str = None,
        raid3: str = None,
        raid4: str = None,
        raid5: str = None,
        raid6: str = None,
    ):
        await self._pick_and_send(
            interaction,
            [raid1, raid2, raid3, raid4, raid5, raid6],
            self.raid_data,
            "Raid",
            "Raid",
        )

    @app_commands.command(name="randomizer-dungeon", description="Choisir aléatoirement un donjon")
    @app_commands.describe(
        donjon1="Premier choix de donjon",
        donjon2="Deuxième choix de donjon",
        donjon3="Troisième choix de donjon",
    )
    async def random_dungeonpick(
        self,
        interaction: discord.Interaction,
        donjon1: str = None,
        donjon2: str = None,
        donjon3: str = None,
    ):
        await self._pick_and_send(
            interaction,
            [donjon1, donjon2, donjon3],
            self.dungeon_data,
            "Donjon",
            "Donjon",
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Randomizer(bot))