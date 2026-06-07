import discord
from discord.ext import commands
from discord import app_commands
from bot.utils.db import db
from bot.utils.translator import _

class DMCleanup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="del",
        description=app_commands.locale_str("cmd_del_desc")
    )
    @app_commands.describe(
        message_id=app_commands.locale_str("cmd_del_msg_id_desc")
    )
    async def delete_dm_message(
        self,
        interaction: discord.Interaction,
        message_id: str,
    ):
        user_settings = await db.get_user_settings(interaction.user.id)
        lang = user_settings["language"]

        # Ensure DM-only
        if interaction.guild is not None:
            await interaction.response.send_message(
                _("del_dm_only", lang, interaction),
                ephemeral=True
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.DMChannel):
            await interaction.response.send_message(
                _("del_not_dm", lang, interaction),
                ephemeral=True
            )
            return

        try:
            msg = await channel.fetch_message(int(message_id))

            # Safety check: only delete bot's own messages
            if msg.author.id != self.bot.user.id:
                await interaction.response.send_message(
                    _("del_own_only", lang, interaction),
                    ephemeral=True
                )
                return

            await msg.delete()

            await interaction.response.send_message(
                _("del_success", lang, interaction),
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                _("del_invalid_id", lang, interaction),
                ephemeral=True
            )

        except discord.NotFound:
            await interaction.response.send_message(
                _("del_not_found", lang, interaction),
                ephemeral=True
            )

        except discord.HTTPException as e:
            await interaction.response.send_message(
                _("del_failed", lang, interaction).format(error=e),
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(DMCleanup(bot))
