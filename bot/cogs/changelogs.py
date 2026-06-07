"""Changelogs cog for displaying bot changelogs."""
import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
from pathlib import Path
from bot.utils.db import db
from bot.utils.translator import _

logger = logging.getLogger(__name__)


class ChangelogPaginationView(discord.ui.View):
    """View for paginating through changelogs."""

    def __init__(self, changelogs: list, interaction: discord.Interaction, lang: str, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.changelogs = changelogs
        self.interaction = interaction
        self.lang = lang
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page."""
        self.previous_button.label = _("changelogs_prev", self.lang, self.interaction)
        self.next_button.label = _("changelogs_next", self.lang, self.interaction)
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.changelogs) - 1

    def get_embed(self) -> discord.Embed:
        """Get embed for current page."""
        changelog = self.changelogs[self.current_page]
        version = changelog.get('version', 'Unknown')
        date = changelog.get('date', 'Unknown')
        changes = changelog.get('changes', [])

        embed = discord.Embed(
            title=_("changelogs_title", self.lang),
            description=f"v{version} - {date}",
            color=discord.Color.blurple()
        )

        changes_text = '\n'.join(f"• {change}" for change in changes) if changes else _("changelogs_no_changes", self.lang)
        embed.add_field(name=_("changelogs_changes", self.lang), value=changes_text, inline=False)
        footer_text = _("changelogs_footer", self.lang).format(current=self.current_page + 1, total=len(self.changelogs))
        embed.set_footer(text=footer_text)

        return embed

    @discord.ui.button(style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous changelog."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(style=discord.ButtonStyle.gray)
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
        self.changelogs_dir = Path("changelogs")

    def load_changelogs(self, lang: str = "en", interaction: discord.Interaction = None) -> list:
        """Load changelogs from the language-specific JSON file, with latest first."""
        # Resolve 'auto' language if needed
        if lang == "auto" and interaction:
            from bot.utils.translator import translator
            lang = translator.get_lang_code(interaction.locale)
        elif lang == "auto":
            lang = "en"

        changelog_file = self.changelogs_dir / f"{lang}.json"

        # Fallback to English if the language file doesn't exist
        if not changelog_file.exists():
            changelog_file = self.changelogs_dir / "en.json"

        try:
            if changelog_file.exists():
                with open(changelog_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    changelogs = data.get('changelogs', [])
                    return list(reversed(changelogs))  # Reverse to show latest first
            else:
                logger.warning(f"Changelog file not found: {changelog_file}")
                return []
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.exception(f"Failed to load changelogs from {changelog_file}: {e}")
            return []

    @app_commands.command(name='changelogs', description=app_commands.locale_str('cmd_changelogs_desc'))
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def changelogs(self, interaction: discord.Interaction):
        """Display bot changelogs."""
        user_settings = await db.get_user_settings(interaction.user.id)
        lang = user_settings.get("language", "auto")

        await interaction.response.defer(ephemeral=True)

        changelogs = self.load_changelogs(lang, interaction)

        if not changelogs:
            await interaction.followup.send(_("changelogs_not_found", lang, interaction), ephemeral=True)
            return

        # Create pagination view
        view = ChangelogPaginationView(changelogs, interaction, lang)
        embed = view.get_embed()

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)



async def setup(bot: commands.Bot):
    """Setup function to load the cog."""
    await bot.add_cog(Changelogs(bot))
    logger.info('✅ Loaded cog: changelogs')
