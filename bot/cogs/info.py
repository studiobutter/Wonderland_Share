


import discord
from discord.ext import commands
from discord import app_commands
from bot.utils.db import db
from bot.utils.translator import _


class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="about", description=app_commands.locale_str("cmd_about_desc"))
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def about(self, interaction: discord.Interaction):
        user_settings = await db.get_user_settings(interaction.user.id)
        lang = user_settings["language"]

        embed = discord.Embed(
            title=_("about_title", lang, interaction),
            color=15844367,
            description=_("about_description", lang, interaction),
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(InfoCog(bot))
