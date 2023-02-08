# bot.py
import discord
from discord import app_commands
from discord.ext import commands, tasks

import os
import asyncio
from dotenv import load_dotenv

import config
import course_info
import quotas_operations

# Uncomment when running on Windows
# Fixes runtime error: asyncio.run() cannot be called from a running event loop
#import nest_asyncio
#nest_asyncio.apply()

# change working directory to wherever bot.py is in
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# load bot token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Uncomment when running on replit (1/2)
# from keep_alive import keep_alive

# define bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="-", intents=intents, activity=discord.Game(name="Portal 3"), help_command=None)

# Update quotas every minute
@tasks.loop(seconds=60.0)
async def update_quotas():
    update_time = course_info.download_quotas()
    print(f"{update_time}: {update_quotas.current_loop}")
    # Send update confirmation message to quota-updates channel
    update_channel = await bot.fetch_channel(1072569015089774622)
    await update_channel.send(f"🔃 Updated! {update_time}: {update_quotas.current_loop}")

# On ready event
# Display bot guilds
@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(
            f'{bot.user} is connected to the following guild(s):\n'
            f'{guild.name}(id: {guild.id})'
        )
    await update_quotas.start()

@bot.event
async def on_guild_join(guild):
    await bot.tree.sync()
    print(
        f'{bot.user} joined the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

# Slash commands start
# "test" command
# Tests bot status
@bot.tree.command(description="Tests bot status", guilds=bot.guilds)
async def test(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("meow")

@bot.tree.command(description="Get quota information for a course!", guilds=bot.guilds)
async def quota(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    embed_quota = quotas_operations.compose_message(course_code.replace(" ", "").upper())
    
    if embed_quota == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    else:
        try:
            await interaction.edit_original_response(embed=embed_quota)
        except:
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, the sections field is limited to 1024 characters long.\nThis translates to around 15 sections.")
# Slash commands end

# Text commands start
# "sync" command
# Syncs command tree with Discord
@commands.guild_only()
@bot.command()
async def sync(ctx):
    if ctx.author.id == 740098404688068641:
        await bot.tree.sync()
        await ctx.send("👍 Commands synced!")
    else:
        await ctx.send("🚫 This command can only be ran by the admin!")
# Text commands end

# Uncomment when running on replit (2/2)
# keep_alive()

# (text) command not found error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.ext.commands.CommandNotFound):
        return
    raise error

# Launch bot
bot.run(TOKEN)