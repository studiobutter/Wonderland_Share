# --- BLOCK 1: Standard Library (Built-in Python stuff) ---
import copy
import json
import logging
from pathlib import Path

# --- BLOCK 2: Third-Party (Pip installed stuff) ---
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# --- BLOCK 3: Local Application (Your own files) ---
from bot.utils.images import (
    download_image,
    remove_cached_file,
    upload_file_via_interaction,
)
from bot.utils.db import db
from bot.utils.translator import _

MAX_DESC_LENGTH = 1024  # Mobile-friendly summary limit
logger = logging.getLogger(__name__)

from config.settings import REGION_NAMES, ServerRegion

def truncate_description(text: str, limit: int = 2048, lang: str = "en", interaction: discord.Interaction = None) -> str:
    if not text:
        return _("wonderland_no_desc", lang, interaction)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


class WonderlandCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        ref_dir = Path(__file__).parent.parent.parent / "ref"
        with open(ref_dir / "payload.json", "r") as f:
            self.payload_template = json.load(f)
        with open(ref_dir / "embed.json", "r") as f:
            self.embed_template = json.load(f)

    @app_commands.command(
        name="wonderland", description=app_commands.locale_str("cmd_wonderland_desc")
    )
    @app_commands.describe(
        guid=app_commands.locale_str("cmd_wonderland_guid_desc"), 
        server=app_commands.locale_str("cmd_wonderland_server_desc")
    )
    @app_commands.choices(
        server=[
            app_commands.Choice(name=name, value=value)
            for value, name in REGION_NAMES.items()
        ]
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def wonderland(
        self, interaction: discord.Interaction, guid: str, server: str = None
    ):
        user_settings = await db.get_user_settings(interaction.user.id)
        lang = user_settings["language"]
        
        if server is None:
            server = user_settings.get("default_server")
            if server is None:
                return await interaction.response.send_message(
                    _("wonderland_server_not_set", lang, interaction),
                    ephemeral=True
                )

        # Validate GUID: only numeric GUIDs are accepted (9-12 digits)
        if not guid.isdigit() or len(guid) not in range(9, 12):
            error_embed = discord.Embed(
                title=_("wonderland_invalid_guid", lang, interaction), 
                description=_("wonderland_guid_desc", lang, interaction), 
                color=15158332
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        use_channel_fallback = False
        try:
            await interaction.response.defer(thinking=True)
        except Exception as e:
            # If the interaction is no longer valid (Unknown interaction), fallback to channel sends.
            # This can happen if the interaction token expired or was invalidated.
            use_channel_fallback = True
            logger.exception(
                "Could not defer interaction; falling back to channel sends"
            )

        payload = copy.deepcopy(self.payload_template["payload"])
        payload["level_id"] = guid
        payload["region"] = server

        url = self.payload_template["url"]
        headers = copy.deepcopy(self.payload_template.get("headers", {}))
        
        # Get resolved API language code (xx-xx format)
        from bot.utils.translator import translator
        rpc_lang = translator.get_api_lang_code(lang, interaction)
        headers["x-rpc-language"] = rpc_lang

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_embed = discord.Embed(
                        title=_("wonderland_server_error", lang, interaction),
                        description=_("wonderland_server_error", lang, interaction),
                        color=15158332,
                    )
                    if use_channel_fallback:
                        channel = getattr(interaction, "channel", None)
                        if channel and hasattr(channel, "send"):
                            await channel.send(embed=error_embed)
                    else:
                        await interaction.followup.send(
                            embed=error_embed, ephemeral=True
                        )
                    return

                try:
                    data = await response.json()
                except json.JSONDecodeError:
                    error_embed = discord.Embed(
                        title=_("wonderland_decode_error", lang, interaction),
                        description=_("wonderland_decode_error", lang, interaction),
                        color=15158332,
                    )
                    if use_channel_fallback:
                        channel = getattr(interaction, "channel", None)
                        if channel and hasattr(channel, "send"):
                            await channel.send(embed=error_embed)
                    else:
                        await interaction.followup.send(
                            embed=error_embed, ephemeral=True
                        )
                    return

        if data.get("retcode") != 0:
            error_embed = discord.Embed(
                title=_("wonderland_server_error", lang, interaction),
                description=data.get("message", "Unknown error"),
                color=15158332,
            )
            if use_channel_fallback:
                channel = getattr(interaction, "channel", None)
                if channel and hasattr(channel, "send"):
                    await channel.send(embed=error_embed)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        # Guard against nested API errors where level_detail.data can be null
        resp_map = data.get("data", {}).get("resp_map", {})
        level_detail = (
            resp_map.get("level_detail", {}) if isinstance(resp_map, dict) else {}
        )

        # If the nested level_detail reports an error or lacks data, surface its message
        if (
            not level_detail
            or level_detail.get("retcode", 0) != 0
            or not level_detail.get("data")
        ):
            nested_msg = None
            if isinstance(level_detail, dict):
                nested_msg = level_detail.get("message")

            # Check for specific "not found" retcode
            if level_detail.get("retcode") == -2000431:
                server_name = _(f"server_{server.replace('os_', '').replace('euro', 'europe').replace('usa', 'america')}", lang, interaction)
                error_embed = discord.Embed(
                    title=_("wonderland_not_found_title", lang, interaction),
                    description=_("wonderland_not_found_desc", lang, interaction).format(guid=guid, server=server_name),
                    color=15158332,
                )
            else:
                error_embed = discord.Embed(
                    title=_("wonderland_server_error", lang, interaction),
                    description=nested_msg or data.get("message", "Level not found"),
                    color=15158332,
                )
            if use_channel_fallback:
                channel = getattr(interaction, "channel", None)
                if channel and hasattr(channel, "send"):
                    await channel.send(embed=error_embed)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        try:
            level_info = level_detail["data"]["level_detail_response"]["level_info"]
        except (KeyError, TypeError):
            error_embed = discord.Embed(
                title=_("wonderland_info_not_found", lang, interaction),
                description=_("wonderland_info_not_found", lang, interaction),
                color=15158332,
            )
            if use_channel_fallback:
                channel = getattr(interaction, "channel", None)
                if channel and hasattr(channel, "send"):
                    await channel.send(embed=error_embed)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        embed_data = copy.deepcopy(self.embed_template)

        # Populate embed
        raw_desc = level_info.get("desc", "")
        embed = embed_data["embeds"][0]
        embed["title"] = level_info.get("level_name", "N/A")
        embed["description"] = truncate_description(raw_desc, MAX_DESC_LENGTH, lang, interaction)
        embed["image"]["url"] = level_info.get("cover_img", {}).get("url")
        for field in embed["fields"]:
            # Translate field name using key from template
            field["name"] = _(field["name"], lang, interaction)
            
            if field["value"] == "level_id":
                field["value"] = level_info.get("level_id", "N/A")
            elif field["value"] == "server_region":
                server_name = _(f"server_{server.replace('os_', '').replace('euro', 'europe').replace('usa', 'america')}", lang, interaction)
                field["value"] = server_name

        # Dynamically populate footer data
        footer_data = {
            "good_rate": level_info.get("good_rate", "N/A"),
            "hot_score": level_info.get("hot_score", "N/A"),
            "show_limit_play_num_str": level_info.get("show_limit_play_num_str", "N/A")
        }
        embed["footer"]["text"] = embed["footer"]["text"].format(**footer_data)

        # Populate components
        components = embed_data["components"]
        for row in components:
            for component in row["components"]:
                if "url" in component:
                    component["url"] = (
                        component["url"]
                        .replace("level_id", guid)
                        .replace("server_region", server)
                    )

        final_embed = discord.Embed.from_dict(embed)

        view = discord.ui.View()
        for row in components:
            for component_data in row["components"]:
                if (
                    component_data["type"] == 2 and component_data["style"] == 5
                ):  # Button with link
                    view.add_item(
                        discord.ui.Button(
                            label=_(component_data.get("label"), lang, interaction),
                            url=component_data.get("url"),
                            style=discord.ButtonStyle.link,
                        )
                    )

        # Handle cover image: download and send as file attachment
        cover_url = level_info.get("cover_img", {}).get("url")
        if cover_url:
            file_path = None
            try:
                file_path = await download_image(
                    cover_url, guid=guid, server=server, cache_dir=".cache"
                )
                logger.info(f"Downloaded cover image for {guid} on {server}")
            except Exception:
                logger.exception("Failed to download cover image")
                # Send embed without image
                if use_channel_fallback:
                    channel = getattr(interaction, "channel", None)
                    if channel and hasattr(channel, "send"):
                        await channel.send(embed=final_embed, view=view)
                else:
                    await interaction.followup.send(embed=final_embed, view=view)
                return

            # Set embed image to attachment reference
            attachment_name = Path(file_path).name
            final_embed.set_image(url=f"attachment://{attachment_name}")

            try:
                # Send the file as attachment
                success = await upload_file_via_interaction(
                    interaction,
                    file_path,
                    filename=attachment_name,
                    view=view,
                    embed=final_embed,
                    use_channel=use_channel_fallback,
                )
                if not success:
                    # Fallback: send without attachment
                    final_embed.set_image(url=None)
                    if use_channel_fallback:
                        channel = getattr(interaction, "channel", None)
                        if channel and hasattr(channel, "send"):
                            await channel.send(embed=final_embed, view=view)
                    else:
                        await interaction.followup.send(embed=final_embed, view=view)
            finally:
                # Always clean up local cached file
                try:
                    if file_path:
                        remove_cached_file(file_path)
                        logger.info(f"Cleaned up cached file: {file_path}")
                except Exception:
                    logger.exception("Failed to remove cached file")
            return

        # No cover URL: just send embed
        if use_channel_fallback:
            channel = getattr(interaction, "channel", None)
            if channel:
                send_func = getattr(channel, "send", None)
                if send_func:
                    await send_func(embed=final_embed, view=view)
            else:
                logger.warning("No fallback channel available to send the embed")
        else:
            await interaction.followup.send(embed=final_embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(WonderlandCog(bot))
