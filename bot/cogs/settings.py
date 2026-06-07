import json
import discord
from discord.ext import commands
from discord import app_commands
from bot.utils.db import db
from bot.utils.translator import _
from config.settings import REGION_NAMES

def load_supported_languages():
    """Loads supported languages from config.json."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("supported_languages", [
                {"code": "auto", "label_key": "lang_auto"},
                {"code": "en", "label_key": "lang_en"},
                {"code": "zh-TW", "label_key": "lang_zh_tw"}
            ])
    except Exception: # pylint: disable=broad-exception-caught
        return [
            {"code": "auto", "label_key": "lang_auto"},
            {"code": "en", "label_key": "lang_en"},
            {"code": "zh-TW", "label_key": "lang_zh_tw"}
        ]

class SettingsView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, lang: str):
        super().__init__(timeout=60)
        self.user_id = interaction.user.id
        self.initial_interaction = interaction
        self.lang = lang
        self.supported_langs = load_supported_languages()
        self._add_selects()

    def _add_selects(self):
        # Server Select
        server_options = [
            discord.SelectOption(label=_("server_asia", self.lang, self.initial_interaction), value="os_asia"),
            discord.SelectOption(label=_("server_europe", self.lang, self.initial_interaction), value="os_euro"),
            discord.SelectOption(label=_("server_america", self.lang, self.initial_interaction), value="os_usa"),
            discord.SelectOption(label=_("server_cht", self.lang, self.initial_interaction), value="os_cht"),
        ]
        server_select = discord.ui.Select(
            placeholder=_("server_placeholder", self.lang, self.initial_interaction),
            options=server_options,
            custom_id="server_select"
        )
        server_select.callback = self.server_callback
        self.add_item(server_select)

        # Language Select
        lang_options = [
            discord.SelectOption(
                label=_(lang["label_key"], self.lang, self.initial_interaction), 
                value=lang["code"]
            )
            for lang in self.supported_langs
        ]
        lang_select = discord.ui.Select(
            placeholder=_("language_placeholder", self.lang, self.initial_interaction),
            options=lang_options,
            custom_id="lang_select"
        )
        lang_select.callback = self.lang_callback
        self.add_item(lang_select)

    async def server_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(_("settings_not_for_you", self.lang, interaction), ephemeral=True)
        
        value = interaction.data["values"][0]
        await db.update_user_setting(self.user_id, "default_server", value)
        
        user_settings = await db.get_user_settings(self.user_id)
        self.lang = user_settings["language"]
        
        embed = self.create_embed(user_settings, interaction)
        # Re-add items with new language
        self.clear_items()
        self._add_selects()
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def lang_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(_("settings_not_for_you", self.lang, interaction), ephemeral=True)
        
        value = interaction.data["values"][0]
        await db.update_user_setting(self.user_id, "language", value)
        
        user_settings = await db.get_user_settings(self.user_id)
        self.lang = user_settings["language"]
        
        embed = self.create_embed(user_settings, interaction)
        # Re-add items with new language
        self.clear_items()
        self._add_selects()
        
        await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self, settings, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_("settings_title", self.lang, interaction),
            description=_("settings_description", self.lang, interaction),
            color=discord.Color.blue()
        )
        
        default_server = settings.get("default_server")
        if default_server:
            server_key = f"server_{default_server.replace('os_', '').replace('euro', 'europe').replace('usa', 'america')}"
            server_name = _(server_key, self.lang, interaction)
        else:
            server_name = "N/A"
        
        lang_code = settings.get("language", "auto")
        lang_label_key = next((l["label_key"] for l in self.supported_langs if l["code"] == lang_code), "lang_auto")
        lang_name = _(lang_label_key, self.lang, interaction)
        
        embed.add_field(name=_("server_label", self.lang, interaction), value=server_name, inline=True)
        embed.add_field(name=_("language_label", self.lang, interaction), value=lang_name, inline=True)
        return embed

class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="settings", description=app_commands.locale_str("cmd_settings_desc"))
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def settings(self, interaction: discord.Interaction):
        user_settings = await db.get_user_settings(interaction.user.id)
        lang = user_settings["language"]
        
        view = SettingsView(interaction, lang)
        embed = view.create_embed(user_settings, interaction)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
