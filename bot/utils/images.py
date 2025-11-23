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
                                       embed: Optional[discord.Embed] = None, use_channel: bool = False) -> bool:
    """
    Send a file as part of an interaction followup or channel message.

    This sends the file directly as an attachment, which Discord will host on their CDN temporarily.
    The file path will be cleaned up by the caller.

    Returns True if sent successfully, False otherwise.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Use the provided filename or the actual file name
    discord_file = discord.File(fp=str(file_path), filename=filename or file_path.name)

    # Build send kwargs
    send_kwargs: dict = {"file": discord_file}
    if embed is not None:
        send_kwargs["embed"] = embed
    if view is not None:
        send_kwargs["view"] = view

    try:
        # If use_channel is True, send to the interaction channel (fallback), otherwise send as followup.
        if use_channel:
            channel = getattr(interaction, 'channel', None)
            if channel is None:
                logger.error("No channel available to send the file")
                return False
            await channel.send(**send_kwargs)
        else:
            await interaction.followup.send(**send_kwargs)
        
        logger.info(f"Sent file as attachment: {file_path.name}")
        return True
    except Exception as e:
        logger.exception(f"Failed to send file: {e}")
        return False
