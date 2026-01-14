"""Main Discord bot instance."""
import discord
from discord.ext import commands, tasks
import os
import sys
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Literal, Optional
from pathlib import Path

from config.settings import DISCORD_TOKEN, BOT_PREFIX, BOT_STATUS, DEBUG, OWNER_ID
from bot.utils.images import cleanup_old_cache_files

# =====================
# Jishaku environment
# =====================
os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_NO_DM_TRACEBACK'] = 'True'
os.environ['JISHAKU_RETAIN'] = 'True'

# =====================
# Logging setup
# =====================
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "bot.log"

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    )

    # File handler (daily rotation)
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d.log"

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


setup_logging()
logger = logging.getLogger(__name__)

# =====================
# Bot setup
# =====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(BOT_PREFIX),
    intents=intents,
    help_command=None,
    owner_id=int(OWNER_ID) if OWNER_ID else None
)

# =====================
# Helpers
# =====================
def get_latest_version() -> str:
    """Get the latest version from changelogs.json."""
    try:
        changelogs_file = Path("changelogs.json")
        if changelogs_file.exists():
            with open(changelogs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                changelogs = data.get('changelogs', [])
                if changelogs:
                    return f"v{changelogs[-1].get('version', '1.0.0')}"
    except Exception as e:
        logger.warning("Failed to load version from changelogs: %s", e)
    return "v1.0.0"


# =====================
# Events
# =====================
@bot.event
async def on_ready():
    logger.info("✅ Bot connected as %s", bot.user)

    latest_version = get_latest_version()
    custom_status = discord.CustomActivity(
        name=f"{latest_version} | {BOT_STATUS}"
    )
    await bot.change_presence(activity=custom_status)

    await load_cogs()
    periodic_cache_cleanup.start()


@bot.event
async def on_error(event, *args, **kwargs):
    logger.exception("Unhandled error in event: %s", event)


# =====================
# Tasks
# =====================
@tasks.loop(hours=1)
async def periodic_cache_cleanup():
    try:
        deleted = await cleanup_old_cache_files(
            cache_dir='.cache',
            max_age_seconds=3600
        )
        if deleted > 0:
            logger.info(
                "Periodic cache cleanup removed %s old file(s)",
                deleted
            )
    except Exception:
        logger.exception("Error during periodic cache cleanup")


@periodic_cache_cleanup.before_loop
async def before_periodic_cleanup():
    await bot.wait_until_ready()


# =====================
# Cog loading
# =====================
async def load_cogs():
    if DEBUG:
        await bot.load_extension('jishaku')
        logger.info("✅ Loaded extension: jishaku")

    cogs_dir = Path(__file__).parent / "cogs"

    for file in cogs_dir.iterdir():
        if file.suffix == ".py" and file.name != "__init__.py":
            cog_name = file.stem
            try:
                await bot.load_extension(f"bot.cogs.{cog_name}")
                logger.info("✅ Loaded cog: %s", cog_name)
            except Exception:
                logger.exception("❌ Failed to load cog: %s", cog_name)

    try:
        synced = await bot.tree.sync()
        logger.info("✅ Synced %s slash command(s)", len(synced))
    except Exception:
        logger.exception("❌ Failed to sync application commands")


# =====================
# Owner commands
# =====================
@commands.guild_only()
@bot.command(name="sync")
@commands.is_owner()
async def sync(
    ctx: commands.Context,
    guilds: commands.Greedy[discord.Object],
    spec: Optional[Literal["~", "*", "^"]] = None,
) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} command(s)"
        )
        return

    success = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            success += 1

    await ctx.send(
        f"Synced commands to {success}/{len(guilds)} guild(s)"
    )


# =====================
# Shutdown
# =====================
def shutdown_handler():
    logger.info("🔌 Shutting down bot...")


# =====================
# Entrypoint
# =====================
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN environment variable not set")
        sys.exit(1)

    if DEBUG:
        print("🐛 Running in DEBUG mode")

    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("⚠️ Bot interrupted by user")
    finally:
        shutdown_handler()
