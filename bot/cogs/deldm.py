import discord
from discord.ext import commands
from discord import app_commands

class DMCleanup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="del",
        description="Delete one of my own DM messages by message ID"
    )
    @app_commands.describe(
        message_id="ID of the message you want to delete."
    )
    async def delete_dm_message(
        self,
        interaction: discord.Interaction,
        message_id: str,
    ):
        # Ensure DM-only
        if interaction.guild is not None:
            await interaction.response.send_message(
                "❌ This command only works in DMs.",
                ephemeral=True
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.DMChannel):
            await interaction.response.send_message(
                "❌ Not a DM channel.",
                ephemeral=True
            )
            return

        try:
            msg = await channel.fetch_message(int(message_id))

            # Safety check: only delete bot's own messages
            if msg.author.id != self.bot.user.id:
                await interaction.response.send_message(
                    "❌ I can only delete my own messages.",
                    ephemeral=True
                )
                return

            await msg.delete()

            await interaction.response.send_message(
                "✅ Message deleted.",
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid message ID.",
                ephemeral=True
            )

        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Message not found.",
                ephemeral=True
            )

        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"❌ Failed to delete message: `{e}`",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(DMCleanup(bot))
