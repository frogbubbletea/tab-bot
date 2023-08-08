# hill.py
import discord
from discord import app_commands
from discord.ext import commands

import os
from dotenv import load_dotenv
import typing

import get_quota

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
TOKEN = os.getenv('HILL_TOKEN')

# Uncomment when running on replit (1/2)
# from keep_alive import keep_alive

# define bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=",", intents=intents, activity=discord.Game(name="Doki Doki Literature Club!"), help_command=None)

# On ready event
# Display bot guilds
@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(
            f'{bot.user} is connected to the following guild(s):\n'
            f'{guild.name}(id: {guild.id})'
        )

# Sync slash command tree with new guild
@bot.event
async def on_guild_join(guild):
    await bot.tree.sync()
    print(
        f'{bot.user} joined the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

# Slash commands start
# Compose page flip buttons for all commands
class QuotaPage(discord.ui.View):
    def __init__(self, *, timeout=180, mode="q", course_code="", page=0):
        super().__init__(timeout=timeout)
        self.mode = mode
        self.course_code = course_code
        self.page = page

    @discord.ui.button(label="Previous page", style=discord.ButtonStyle.gray, emoji="⬅️")
    async def previous_button(self,interaction:discord.Interaction, button:discord.ui.Button):
        if self.mode == "q":
            embed_quota_pageflip = get_quota.compose_message(self.course_code, self.page - 1)
        elif self.mode == "s":
            embed_quota_pageflip = get_quota.compose_sections(self.course_code, self.page - 1)
        elif self.mode == "l":
            embed_quota_pageflip = get_quota.compose_list(self.course_code, self.page - 1)
        # No pages for info command
        # elif self.mode == "i":
        #     button.disabled = True

        if embed_quota_pageflip == "p0":
            await interaction.response.send_message("🚫 You're already at the first page!", ephemeral=True)
        else:
            try:
                await interaction.response.edit_message(embed=embed_quota_pageflip, view=self)
            except:  # Highly unlikely to happen
                await interaction.response.send_message(f"⚠️ Error: {embed_quota_pageflip}!")
            else:
                self.page -= 1

    @discord.ui.button(label="Next page", style=discord.ButtonStyle.gray, emoji="➡️")
    async def next_button(self,interaction:discord.Interaction, button:discord.ui.Button):
        if self.mode == "q":
            embed_quota_pageflip = get_quota.compose_message(self.course_code, self.page + 1)
        elif self.mode == "s":
            embed_quota_pageflip = get_quota.compose_sections(self.course_code, self.page + 1)
        elif self.mode == "l":
            embed_quota_pageflip = get_quota.compose_list(self.course_code, self.page + 1)
        # No pages for info command
        # elif self.mode == "i":
        #     button.disabled = True

        if embed_quota_pageflip == "pmax":
            await interaction.response.send_message("🚫 You're already at the last page!", ephemeral=True)
        else:
            try:
                await interaction.response.edit_message(embed=embed_quota_pageflip, view=self)
            except:  # Highly unlikely to happen
                await interaction.response.send_message(f"⚠️ Error: {embed_quota_pageflip}!")
            else:
                self.page += 1

# Get source URL on original UST course quota website for "Source" button
def get_source_url(course_code, mode=None):
    if mode == "l":  # /list command, link to top of website
        source_url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{get_quota.semester_code}/subject/{course_code}"
    else:
        source_url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{get_quota.semester_code}/subject/{course_code[0: 4]}#{course_code}"
    return source_url

# "quota" command
# Lists quotas of all sections of a course
@bot.tree.command(description="Get quotas for a course!", guilds=bot.guilds)
async def quota(interaction: discord.Interaction, course_code: str):
    await interaction.response.defer(thinking=True)

    course_code = course_code.replace(" ", "").upper()
    embed_quota = get_quota.compose_message(course_code)
    
    # Error: Course data unavailable
    if embed_quota == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_quota == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    # Error: Course has no sections (unlikely)
    elif embed_quota == "no_sections":
        await interaction.edit_original_response(content="⚠️ This course has no sections!")
    else:
        try:
            view = QuotaPage(mode="q", course_code=course_code)
            view.add_item(discord.ui.Button(label="Source", style=discord.ButtonStyle.link, url=get_source_url(course_code)))
            await interaction.edit_original_response(embed=embed_quota, view=view)
        except:  # Deprecated: large numbers of sections should be displayed correctly with pagination
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, the sections field is limited to 1024 characters long.\nThis translates to around 15 sections.")

# "info" command
# Shows course info
@bot.tree.command(description="Get the information of a course!", guilds=bot.guilds)
async def info(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    course_code = course_code.replace(" ", "").upper()
    embed_info = get_quota.compose_info(course_code.replace(" ", "").upper())

    # Error: Course data unavailable
    if embed_info == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_info == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    else:
        try:
            view = QuotaPage(mode="i", course_code=course_code)
            view.clear_items()
            view.add_item(discord.ui.Button(label="Source", style=discord.ButtonStyle.link, url=get_source_url(course_code)))
            await interaction.edit_original_response(embed=embed_info, view=view)
        except:  # Deprecated: long course info text should be displayed correctly by splitting into multiple fields
            await interaction.edit_original_response(content="⚠️ Course info too long!\nDue to a Discord limitation, course info is limited to 1024 characters long.")

# "sections" command
# Lists sections of a course and their times, venues and instructors
@bot.tree.command(description="Get sections of a course!", guilds=bot.guilds)
async def sections(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    course_code = course_code.replace(" ", "").upper()
    embed_sections = get_quota.compose_sections(course_code)

    # Error: Course data unavailable
    if embed_sections == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_sections == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    # Error: Course has no sections (unlikely)
    elif embed_sections == "no_sections":
        await interaction.edit_original_response(content="⚠️ This course has no sections!")
    else:
        try:
            view = QuotaPage(mode="s", course_code=course_code)
            view.add_item(discord.ui.Button(label="Source", style=discord.ButtonStyle.link, url=get_source_url(course_code)))
            await interaction.edit_original_response(embed=embed_sections, view=view)
        except:  # Deprecated: large numbers of sections should be displayed correctly with pagination
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, courses with more than 25 sections cannot be displayed.")

# Autocomplete for "quota", "info", "sections" command
@quota.autocomplete('course_code')
@info.autocomplete('course_code')
@sections.autocomplete('course_code')
async def sections_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    courses = get_quota.get_course_list()
    data = [app_commands.Choice(name=course, value=course)
            for course in courses if current.replace(" ", "").upper() in course.upper()
            ][0: 25]
    return data

# "list" command
# List all courses with given prefix
@bot.tree.command(description="List all courses with a given prefix/area!", guilds=bot.guilds)
async def list(interaction: discord.Interaction, prefix: str) -> None:
    await interaction.response.defer(thinking=True)
    cc_areas = get_quota.get_cc_areas()

    if prefix not in cc_areas:  # Do not uppercase common core area arguments
        prefix = prefix.replace(" ", "").upper()
    embed_list = get_quota.compose_list(prefix)

    # Error: Course data unavailable
    if embed_list == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: invalid prefix
    elif embed_list == "key":
        await interaction.edit_original_response(content="⚠️ No courses found with this prefix!")
    else:
        view = QuotaPage(mode="l", course_code=prefix)
        # Do not add source link if common core is given
        if prefix not in cc_areas:
            view.add_item(discord.ui.Button(label="Source", style=discord.ButtonStyle.link, url=get_source_url(prefix, "l")))
        await interaction.edit_original_response(embed=embed_list, view=view)

# Autocomplete for "list" command
@list.autocomplete('prefix')
async def list_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    prefix_list = get_quota.get_prefix_list()
    cc_areas = get_quota.get_cc_areas()
    prefix_list.extend(cc_areas)
    data = [app_commands.Choice(name=prefix, value=prefix)
            for prefix in prefix_list if current.replace(" ", "").upper() in prefix.replace(" ", "").upper()
            ][0: 25]
    return data

# Slash commands end

# Text commands start
# "sync" command
# Syncs command tree with Discord
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
