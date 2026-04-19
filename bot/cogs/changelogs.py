"""Changelogs cog for displaying bot changelogs."""
import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ChangelogPaginationView(discord.ui.View):
    """View for paginating through changelogs."""

    def __init__(self, changelogs: list, interaction: discord.Interaction, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.changelogs = changelogs
        self.interaction = interaction
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page."""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.changelogs) - 1

    def get_embed(self) -> discord.Embed:
        """Get embed for current page."""
        changelog = self.changelogs[self.current_page]
        version = changelog.get('version', 'Unknown')
        date = changelog.get('date', 'Unknown')
        changes = changelog.get('changes', [])

        embed = discord.Embed(
            title="📋 Bot Changelogs",
            description=f"v{version} - {date}",
            color=discord.Color.blurple()
        )

        changes_text = '\n'.join(f"• {change}" for change in changes) if changes else "No changes listed"
        embed.add_field(name="Changes", value=changes_text, inline=False)
        embed.set_footer(text=f"Version {self.current_page + 1} of {len(self.changelogs)}")

        return embed

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous changelog."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next changelog."""
        if self.current_page < len(self.changelogs) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)


class Changelogs(commands.Cog):
    """Commands for viewing bot changelogs."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.changelogs_file = Path("changelogs.json")

    def load_changelogs(self) -> list:
        """Load changelogs from changelogs.json, with latest first."""
        try:
            if self.changelogs_file.exists():
                with open(self.changelogs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    changelogs = data.get('changelogs', [])
                    return list(reversed(changelogs))  # Reverse to show latest first
            else:
                logger.warning(f"Changelogs file not found: {self.changelogs_file}")
                return []
        except Exception as e:
            logger.exception(f"Failed to load changelogs: {e}")
            return []

    @app_commands.command(name='changelogs', description='View bot version changelogs')
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def changelogs(self, interaction: discord.Interaction):
        """Display bot changelogs."""
        await interaction.response.defer(ephemeral=True)

        changelogs = self.load_changelogs()

        if not changelogs:
            await interaction.followup.send("❌ No changelogs found.", ephemeral=True)
            return

        # Create pagination view
        view = ChangelogPaginationView(changelogs, interaction)
        embed = view.get_embed()

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function to load the cog."""
    await bot.add_cog(Changelogs(bot))
    logger.info('✅ Loaded cog: changelogs')
