import copy
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import logging
from pathlib import Path

from config.settings import ServerRegion, REGION_NAMES
from bot.utils.images import download_image, remove_cached_file, upload_file_via_interaction

# Need to work on GitHub Issue #3 regarding handling cover_img issue

class WonderlandCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        with open('ref/payload.json', 'r') as f:
            self.payload_template = json.load(f)
        with open('ref/embed.json', 'r') as f:
            self.embed_template = json.load(f)

    @app_commands.command(name="wonderland", description="Fetch information about a Wonderland level.")
    @app_commands.describe(
        guid="The GUID of the level.",
        server="The server the level is on."
    )
    @app_commands.choices(server=[
        app_commands.Choice(name=name, value=value) for value, name in REGION_NAMES.items()
    ])
    async def wonderland(self, interaction: discord.Interaction, guid: str, server: str):
        # Validate GUID: only numeric GUIDs are accepted
        if not guid.isdigit():
            error_embed = discord.Embed(
                title="An error occurred",
                description="Invalid GUID",
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
            logging.exception('Could not defer interaction; falling back to channel sends')

        payload = copy.deepcopy(self.payload_template['payload'])
        payload['level_id'] = guid
        payload['region'] = server

        url = self.payload_template['url']

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_embed = discord.Embed(
                        title="An error occurred",
                        description="The server returned an error.",
                        color=15158332
                    )
                    if use_channel_fallback:
                        channel = getattr(interaction, "channel", None)
                        if channel and hasattr(channel, "send"):
                            await channel.send(embed=error_embed)
                    else:
                        await interaction.followup.send(embed=error_embed, ephemeral=True)
                    return
                
                try:
                    data = await response.json()
                except json.JSONDecodeError:
                    error_embed = discord.Embed(
                        title="An error occurred",
                        description="Could not decode the response from the server.",
                        color=15158332
                    )
                    if use_channel_fallback:
                        channel = getattr(interaction, "channel", None)
                        if channel and hasattr(channel, "send"):
                            await channel.send(embed=error_embed)
                    else:
                        await interaction.followup.send(embed=error_embed, ephemeral=True)
                    return

        if data.get("retcode") != 0:
            error_embed = discord.Embed(
                title="An error occurred",
                description=data.get('message', 'Unknown error'),
                color=15158332
            )
            if use_channel_fallback:
                channel = getattr(interaction, "channel", None)
                if channel and hasattr(channel, "send"):
                    await channel.send(embed=error_embed)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        # Guard against nested API errors where level_detail.data can be null
        resp_map = data.get('data', {}).get('resp_map', {})
        level_detail = resp_map.get('level_detail', {}) if isinstance(resp_map, dict) else {}

        # If the nested level_detail reports an error or lacks data, surface its message
        if not level_detail or level_detail.get('retcode', 0) != 0 or not level_detail.get('data'):
            nested_msg = None
            if isinstance(level_detail, dict):
                nested_msg = level_detail.get('message')

            error_embed = discord.Embed(
                title="An error occurred",
                description=nested_msg or data.get('message', 'Level not found'),
                color=15158332
            )
            if use_channel_fallback:
                channel = getattr(interaction, "channel", None)
                if channel and hasattr(channel, "send"):
                    await channel.send(embed=error_embed)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        try:
            level_info = level_detail['data']['level_detail_response']['level_info']
        except (KeyError, TypeError):
            error_embed = discord.Embed(
                title="An error occurred",
                description="Could not find level information in the response.",
                color=15158332
            )
            if use_channel_fallback:
                channel = getattr(interaction, "channel", None)
                if channel and hasattr(channel, "send"):
                    await channel.send(embed=error_embed)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        embed_data = self.embed_template.copy()
        
        # Populate embed
        embed = embed_data['embeds'][0]
        embed['title'] = level_info.get('level_name', 'N/A')
        embed['description'] = level_info.get('desc', 'N/A')
        embed['image']['url'] = level_info.get('cover_img', {}).get('url')

        for field in embed['fields']:
            if field['value'] == 'level_id':
                field['value'] = level_info.get('level_id', 'N/A')
            elif field['value'] == 'server_region':
                field['value'] = REGION_NAMES.get(server, 'N/A')

        # Populate components
        components = embed_data['components']
        for row in components:
            for component in row['components']:
                if 'url' in component:
                    component['url'] = component['url'].replace('level_id', guid).replace('server_region', server)

        final_embed = discord.Embed.from_dict(embed)

        view = discord.ui.View()
        for row in components:
            for component_data in row['components']:
                if component_data['type'] == 2 and component_data['style'] == 5: # Button with link
                    view.add_item(discord.ui.Button(
                        label=component_data.get('label'),
                        url=component_data.get('url'),
                        style=discord.ButtonStyle.link
                    ))

        # Handle cover image: download and send as file attachment
        cover_url = level_info.get('cover_img', {}).get('url')
        if cover_url:
            file_path = None
            try:
                file_path = await download_image(cover_url, guid=guid, server=server, cache_dir='.cache')
                logging.info(f'Downloaded cover image for {guid} on {server}')
            except Exception:
                logging.exception('Failed to download cover image')
                # Send embed without image
                if use_channel_fallback:
                    channel = getattr(interaction, 'channel', None)
                    if channel and hasattr(channel, 'send'):
                        await channel.send(embed=final_embed, view=view)
                else:
                    await interaction.followup.send(embed=final_embed, view=view)
                return

            # Set embed image to attachment reference
            attachment_name = Path(file_path).name
            final_embed.set_image(url=f'attachment://{attachment_name}')

            try:
                # Send the file as attachment
                success = await upload_file_via_interaction(
                    interaction, file_path, filename=attachment_name, view=view, embed=final_embed,
                    use_channel=use_channel_fallback
                )
                if not success:
                    # Fallback: send without attachment
                    final_embed.set_image(url=None)
                    if use_channel_fallback:
                        channel = getattr(interaction, 'channel', None)
                        if channel and hasattr(channel, 'send'):
                            await channel.send(embed=final_embed, view=view)
                    else:
                        await interaction.followup.send(embed=final_embed, view=view)
            finally:
                # Always clean up local cached file
                try:
                    if file_path:
                        remove_cached_file(file_path)
                        logging.info(f'Cleaned up cached file: {file_path}')
                except Exception:
                    logging.exception('Failed to remove cached file')
            return

        # No cover URL: just send embed
        if use_channel_fallback:
            channel = getattr(interaction, 'channel', None)
            if channel:
                send_func = getattr(channel, 'send', None)
                if send_func:
                    await send_func(embed=final_embed, view=view)
            else:
                logging.warning('No fallback channel available to send the embed')
        else:
            await interaction.followup.send(embed=final_embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(WonderlandCog(bot))
