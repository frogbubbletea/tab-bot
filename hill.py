# hill.py
import discord
from discord import app_commands
from discord.ext import commands

import os
from dotenv import load_dotenv
import typing

import get_quota
import config

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

# Load admin's ID and test server ID
admin_id = 740098404688068641
test_server_id = 958651015064854548

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

# "quota" command
# Lists quotas of all sections of a course
@bot.tree.command(description="Get quotas for a course!")
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
            view.add_item(discord.ui.Button(label="Source", style=discord.ButtonStyle.link, url=get_quota.get_source_url(course_code)))
            await interaction.edit_original_response(embed=embed_quota, view=view)
        except:  # Deprecated: large numbers of sections should be displayed correctly with pagination
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, the sections field is limited to 1024 characters long.\nThis translates to around 15 sections.")

# "info" command
# Shows course info
@bot.tree.command(description="Get the information of a course!")
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
            view.add_item(discord.ui.Button(label="Source", style=discord.ButtonStyle.link, url=get_quota.get_source_url(course_code)))
            await interaction.edit_original_response(embed=embed_info, view=view)
        except:  # Deprecated: long course info text should be displayed correctly by splitting into multiple fields
            await interaction.edit_original_response(content="⚠️ Course info too long!\nDue to a Discord limitation, course info is limited to 1024 characters long.")

# "sections" command
# Lists sections of a course and their times, venues and instructors
@bot.tree.command(description="Get sections of a course!")
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
            view.add_item(discord.ui.Button(label="Source", style=discord.ButtonStyle.link, url=get_quota.get_source_url(course_code)))
            await interaction.edit_original_response(embed=embed_sections, view=view)
        except:  # Deprecated: large numbers of sections should be displayed correctly with pagination
            await interaction.edit_original_response(content="⚠️ This course has too many sections!\nDue to a Discord limitation, courses with more than 25 sections cannot be displayed.")

# "list" command
# List all courses with given prefix
@bot.tree.command(description="List all courses with a given prefix/area!")
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
            view.add_item(discord.ui.Button(label="Source", style=discord.ButtonStyle.link, url=get_quota.get_source_url(prefix, "l")))
        await interaction.edit_original_response(embed=embed_list, view=view)

# "sub" command group
# List subscribed courses, subscribe to a course, unsubscribe from a course
subscribe_group = app_commands.Group(name="sub", description="Manage your course subscriptions!")

# "sub sub" command
@subscribe_group.command(description="Subscribe to a course! You'll be notified of its changes via DM.")
async def sub(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    course_code = course_code.replace(" ", "").upper()
    embed_subscribe = get_quota.compose_subscribe(course_code, interaction.user.id, 0)

    # Error: Course data unavailable
    if embed_subscribe == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_subscribe == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    
    else:
        # Send confirmation/failure message
        await interaction.edit_original_response(embed=embed_subscribe)

        # Display message for new/canceled subscribers
        if_new_sub = get_quota.check_if_new_sub(interaction.user.id, 0)
        if if_new_sub != 1:
            embed_new_sub, view = get_quota.compose_new_sub_confirmation(if_new_sub)
            await interaction.channel.send(embed=embed_new_sub, view=view)

# "sub unsub" command
@subscribe_group.command(description="Unsubscribe from a course!")
async def unsub(interaction: discord.Interaction, course_code: str) -> None:
    await interaction.response.defer(thinking=True)

    course_code = course_code.replace(" ", "").upper()

    # Detect unsubscribe all
    if course_code == "ALLCOURSES":
        operation = 2
    else:
        operation = 1
    
    embed_subscribe = get_quota.compose_subscribe(course_code, interaction.user.id, operation)

    # Error: Course data unavailable
    if embed_subscribe == "unavailable":
        await interaction.edit_original_response(embed=get_quota.embed_quota_unavailable)
    # Error: Invalid course code
    elif embed_subscribe == "key":
        await interaction.edit_original_response(content="⚠️ Check your course code!")
    
    else:
        # Send confirmation/failure message
        await interaction.edit_original_response(embed=embed_subscribe)

        # Display message for new/canceled subscribers
        if_new_sub = get_quota.check_if_new_sub(interaction.user.id, 1)
        if if_new_sub != 1:
            embed_new_sub, view = get_quota.compose_new_sub_confirmation(if_new_sub)
            await interaction.channel.send(embed=embed_new_sub, view=view)

# "sub show" command
@subscribe_group.command(description="Show all courses you're subscribed to!")
async def show(interaction: discord.Interaction) -> None:
    await interaction.response.defer(thinking=True)

    # Send message of subscriptions
    embed_show = get_quota.compose_show(interaction)
    await interaction.edit_original_response(embed=embed_show)

    # Display message for new subscribers
    if_new_sub = get_quota.check_if_new_sub(interaction.user.id, 1)
    if if_new_sub != 1:
        embed_new_sub, view = get_quota.compose_new_sub_confirmation(if_new_sub)
        await interaction.channel.send(embed=embed_new_sub, view=view)

# Add "sub" command group to command tree
bot.tree.add_command(subscribe_group)

# Autocomplete for "quota", "info", "sections", "sub sub" command
@quota.autocomplete('course_code')
@info.autocomplete('course_code')
@sections.autocomplete('course_code')
@sub.autocomplete('course_code')
async def sections_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    courses = get_quota.get_course_list()
    data = [app_commands.Choice(name=course, value=course)
            for course in courses if current.replace(" ", "").upper() in course.upper()
            ][0: 25]
    return data

# Autocomplete for "sub unsub" command
@unsub.autocomplete('course_code')
async def unsub_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    # Get subscription list of current user
    subs, entry = get_quota.find_sub(interaction.user.id)
    courses = entry['courses']
    courses.append("All courses") # Add option to unsub from all courses
    # Turn them into command autocomplete options
    data = [app_commands.Choice(name=course, value=course)
    for course in courses if current.replace(" ", "").upper() in course.upper()
    ][0: 25]
    return data

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

# "debug" command
# Upload bot and quota status to Discord for remote debug
# Only available in test server
@bot.tree.command(description="Upload bot and quota status for debug!", guild=discord.Object(test_server_id))
async def debug(interaction: discord.Interaction, file: str) -> None:
    await interaction.response.defer(thinking=True)

    # Send list of connected servers
    if file == "guild_list":
        # Put list of guilds into txt file
        guild_list_file = open('guild_list.txt', 'w')
        for guild in bot.guilds:
            guild_list_file.write(f'{guild.name}(id: {guild.id})\n')
        guild_list_file.close()

        # Send the txt file
        await interaction.edit_original_response(content=f"🎏 Bot is connected to {len(bot.guilds)} servers!")
        await interaction.channel.send(file=discord.File("guild_list.txt"))

        # Delete the txt file
        try:
            os.remove("guild_list.txt")
        except:
            pass
    
    # Send quotas file scraped by the bot
    else:
        await interaction.edit_original_response(content=f"🎏 Quotas file: `{file}.json`")
        await interaction.channel.send(file=discord.File(f"{file}.json"))

@debug.autocomplete('file')
async def debug_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    file_list = ['quotas', 'quotas_old', 'subscribers', 'guild_list']
    file_list = [app_commands.Choice(name=file, value=file) for file in file_list]
    return file_list

# Slash commands end

# Text commands start
# "sync" command
# Syncs command tree with Discord
@bot.command()
async def sync(ctx):
    if ctx.author.id == admin_id:  # Owner's ID
        # Sync global commands
        await bot.tree.sync()

        # Sync guild specific commands
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)

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
