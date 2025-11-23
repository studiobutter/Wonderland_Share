"""Main Discord bot instance."""
import discord
from discord.ext import commands, tasks
import os
import sys
import logging
from typing import Literal, Optional

from config.settings import DISCORD_TOKEN, BOT_PREFIX, BOT_STATUS, DEBUG, OWNER_ID
from bot.utils.images import cleanup_old_cache_files

# Jishaku settings
os.environ['JISHAKU_NO_UNDERSCORE'] = 'True'
os.environ['JISHAKU_NO_DM_TRACEBACK'] = 'True'
os.environ['JISHAKU_RETAIN'] = 'True'

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Create bot instance
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(BOT_PREFIX),
    intents=intents,
    help_command=None,
    owner_id=int(OWNER_ID) if OWNER_ID else None
)


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    logger.info('✅ Bot connected as %s', bot.user)
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=BOT_STATUS)
    )
    await load_cogs()
    periodic_cache_cleanup.start()


@tasks.loop(hours=1)
async def periodic_cache_cleanup():
    """Periodically clean up cache files older than 1 hour."""
    try:
        deleted = await cleanup_old_cache_files(cache_dir='.cache', max_age_seconds=3600)
        if deleted > 0:
            logger.info(f"Periodic cache cleanup removed {deleted} old file(s)")
    except Exception as e:
        logger.exception(f"Error in periodic cache cleanup: {e}")


@periodic_cache_cleanup.before_loop
async def before_periodic_cleanup():
    """Wait for bot to be ready before starting cleanup task."""
    await bot.wait_until_ready()


@bot.event
async def on_error(event, *args, **kwargs):
    """Handle errors."""
    logger.exception("Unhandled error in %s", event)


def shutdown_handler():
    """Handle bot shutdown."""
    logger.info('🔌 Shutting down bot...')


async def load_cogs():
    """Load all cogs."""
    await bot.load_extension('jishaku')
    logger.info('✅ Loaded extension: jishaku')

    cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
    for filename in os.listdir(cogs_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            cog_name = filename[:-3]
            try:
                await bot.load_extension(f'bot.cogs.{cog_name}')
                logger.info('✅ Loaded cog: %s', cog_name)
            except Exception:
                logger.exception('❌ Failed to load cog %s', cog_name)
    
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logger.exception(e)

@commands.guild_only()
@bot.command(name='sync')
@commands.is_owner()
async def sync(
  ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
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
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)} guilds.")


if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print('❌ Error: DISCORD_TOKEN environment variable not set')
        sys.exit(1)
    
    if DEBUG:
        print('🐛 Running in DEBUG mode')
    
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info('⚠️  Bot interrupted by user')
    finally:
        shutdown_handler()
