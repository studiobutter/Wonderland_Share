"""Image caching utilities.

Functions:
- ensure_cache_dir(cache_dir)
- download_image(url, guid=None, server=None, cache_dir='.cache') -> Path
- remove_cached_file(path)

These are async helpers intended to be used from cogs (which are async).
"""
from __future__ import annotations

import aiohttp
import asyncio
import imghdr
import os
import time
import uuid
from pathlib import Path
from typing import Optional
import discord
import logging

logger = logging.getLogger(__name__)

CACHE_DIR_DEFAULT = Path(".cache")


def ensure_cache_dir(cache_dir: Optional[Path | str] = None) -> Path:
    """Ensure cache directory exists and return the Path."""
    cache_path = Path(cache_dir) if cache_dir else CACHE_DIR_DEFAULT
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def _guess_extension_from_content(content: bytes, content_type: Optional[str] = None) -> str:
    """Return a file extension (without dot) based on content bytes or content-type header."""
    # First try imghdr
    kind = imghdr.what(None, h=content)
    if kind:
        return kind if kind != 'jpeg' else 'jpg'

    # Fallback to content-type header
    if content_type:
        if '/' in content_type:
            main, subtype = content_type.split('/', 1)
            if main == 'image':
                # strip parameters
                subtype = subtype.split(';', 1)[0]
                if subtype == 'jpeg':
                    return 'jpg'
                return subtype

    # Last resort
    return 'bin'


def _make_filename(guid: Optional[str], server: Optional[str], ext: str) -> str:
    """Create a unique filename for cached image."""
    timestamp = int(time.time())
    if guid and server:
        base = f"{guid}_{server}_{timestamp}"
    elif guid:
        base = f"{guid}_{timestamp}"
    else:
        base = f"{uuid.uuid4().hex}_{timestamp}"
    return f"{base}.{ext}"


async def download_image(url: str, guid: Optional[str] = None, server: Optional[str] = None,
                         cache_dir: Optional[Path | str] = None, timeout: int = 15) -> Path:
    """
    Download an image to the cache directory and return the saved Path.

    Args:
        url: Remote image URL
        guid: Optional GUID to include in filename
        server: Optional server string to include in filename
        cache_dir: Local cache directory (defaults to `.cache`)
        timeout: Request timeout in seconds

    Returns:
        Path to saved file

    Raises:
        aiohttp.ClientError on HTTP issues or ValueError if content is not downloadable
    """
    cache_path = ensure_cache_dir(cache_dir)

    # Use a short-lived ClientSession for this download
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise aiohttp.ClientResponseError(
                    status=resp.status, message=f"Failed to download image: {resp.status}", request_info=resp.request_info, history=resp.history
                )

            content = await resp.read()
            if not content:
                raise ValueError("Downloaded content is empty")

            content_type = resp.headers.get('Content-Type')
            ext = _guess_extension_from_content(content, content_type)

            filename = _make_filename(guid, server, ext)
            file_path = cache_path / filename

            # Write to disk
            with open(file_path, 'wb') as f:
                f.write(content)

            return file_path


def remove_cached_file(path: Path | str) -> bool:
    """Remove a cached file by path. Returns True if removed, False if not found."""
    p = Path(path)
    try:
        if p.exists():
            p.unlink()
            return True
        return False
    except Exception:
        return False


async def upload_file_via_interaction(interaction: discord.Interaction, file_path: Path | str,
                                       filename: Optional[str] = None, *, view: Optional[discord.ui.View] = None,
                                       embed: Optional[discord.Embed] = None, use_channel: bool = False):
    """
    Upload a local file using an Interaction followup and return the uploaded attachment URL.

    This sends the file as part of the interaction followup, so the attachment will be associated
    with the bot's message and Discord will host it on their CDN. The caller is responsible for
    deleting the local cached file afterwards.

    Returns the attachment URL string, or None if the upload fails.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Use the provided filename or the actual file name
    discord_file = discord.File(fp=str(file_path), filename=filename or file_path.name)

    # Send followup with file. Caller should have already called `interaction.response.defer()`.
    send_kwargs: dict = {"file": discord_file}
    if embed is not None:
        send_kwargs["embed"] = embed
    if view is not None:
        send_kwargs["view"] = view

    sent = None
    try:
        # If use_channel is True, send to the interaction channel (fallback), otherwise send as followup.
        if use_channel:
            channel = getattr(interaction, 'channel', None)
            if channel is None:
                raise RuntimeError("No channel available to send the file")
            sent = await channel.send(**send_kwargs)
        else:
            # Explicitly wait=True to get a Message object back
            sent = await interaction.followup.send(**send_kwargs, wait=True)
    except Exception as e:
        logger.error(f"Failed to send message with file: {e}", exc_info=True)
        # If sending fails, we can't do much else. The original `defer` will eventually time out.
        return None


    # Extract attachment URL from the sent message
    if sent:
        # Using .attachments on a Message object should work directly.
        # For a WebhookMessage, it might be empty.
        attachments = getattr(sent, "attachments", [])
        if attachments and len(attachments) > 0:
            url = attachments[0].url
            logger.info(f"Uploaded file to Discord: {url}")
            return url
        
        # If attachments are not present, it's likely a WebhookMessage.
        # Fallback to fetching the message via the API.
        logger.warning(
            f"Message sent (obj: {type(sent).__name__}) but attachments not in response; fetching via API"
        )
        try:
            bot = interaction.client
            if not bot:
                logger.error("No bot client available in interaction, cannot fetch message.")
            else:
                channel_id = (
                    sent.channel.id
                    if hasattr(sent, "channel") and sent.channel
                    else interaction.channel_id
                )
                if not channel_id:
                    logger.error("Cannot determine channel ID for fetching message.")
                else:
                    channel = await bot.fetch_channel(channel_id)
                    # Ensure the channel is of a type that has `fetch_message`
                    if isinstance(
                        channel,
                        (
                            discord.TextChannel,
                            discord.DMChannel,
                            discord.GroupChannel,
                            discord.Thread,
                        ),
                    ):
                        # Retry fetching a few times with increasing backoff
                        for attempt in range(1, 4): # Try 3 times
                            await asyncio.sleep(attempt * 1.5)  # 1.5s, 3s, 4.5s
                            try:
                                fetched_message = await channel.fetch_message(sent.id)
                                if fetched_message and fetched_message.attachments:
                                    url = fetched_message.attachments[0].url
                                    logger.info(f"Fetched message via API on attempt {attempt}; got attachment URL: {url}")
                                    return url
                                else:
                                    logger.warning(f"Attempt {attempt}: Fetched message but no attachments found yet.")
                            except discord.errors.NotFound:
                                logger.error(f"Failed to fetch message {sent.id} on attempt {attempt}, it may have been deleted.")
                                break  # Stop retrying if message is not found
                            except Exception as e:
                                logger.error(f"An unexpected error occurred while fetching message on attempt {attempt}: {e}")
                    else:
                        logger.error(f"Channel {channel_id} is not a messageable channel type.")
        except Exception as e:
            logger.error(f"Could not fetch message via API due to a fundamental error: {e}", exc_info=True)

    logger.warning(f"Failed to retrieve attachment URL for message {sent.id} after multiple attempts. The message will be left as-is, but the URL will not be cached.")
    return None
