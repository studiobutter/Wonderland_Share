import discord
from discord.ext import commands
from discord import app_commands


class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="about", description="Learn about the Wonderland bot.")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Wonderland Explorer",
            color=15844367,
            description="This bot is made by Studio Butter ([@charaanimates](<discord://-/users/674463869816799243>)) and is open-source on [GitHub](<https://github.com/studiobutter/Wonderland_Share>). For questions or issues with this bot, DM me on Discord or open an issue on GitHub.\nTo contribute, DM me or open a PR on GitHub.\nThis bot is self-hosted in my house, so uptime is not guaranteed. If you wish to have it hosted 24/7, feel free to donate [here](<https://ko-fi.com/studiobutterteam>)\n\n[Join our Miliastra Discord Community](<https://discord.gg/2cJyk55Mz9>)",
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(InfoCog(bot))
