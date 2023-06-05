# get_quota.py
import requests
import bs4

import discord

import os
import json
from datetime import datetime, timezone
import re

import config
import subject_channels

# Change working directory to wherever this is in
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# semester code of course quota website
# first 2 digits correspond to the year
# Last 2 digits correspond to season
# Fall: 10
# Winter: 20
# Spring: 30
# Summer: 40
semester_code = 2240

def trim_section(section_code):
    section_trim = re.findall("[A-Z]+[0-9]*[A-Z]*", section_code)[0]
    return section_trim

# Store current time (UTC) as last updated time when quota update is finished
def update_time():
    now = datetime.now(timezone.utc)
    date_time = int(datetime.timestamp(now))
    return date_time

# Convert time string formatted by update_time() to Discord timestamp
# List of styles: https://gist.github.com/LeviSnoot/d9147767abeef2f770e9ddcd91eb85aa
def disc_time(stamp, style=""):
    time_string = f"<t:{stamp}:{style}>"
    return time_string

# Convert UNIX timestamp to aware datetime object (UTC)
def time_from_stamp(stamp):
    time_object = datetime.fromtimestamp(stamp, timezone.utc)
    return time_object

# Find additions and removals between two lists
def list_diffs(temp1, temp2):
    additions = [x for x in temp1 if x not in set(temp2)]  # Elements in temp1 not in temp2
    removals = [x for x in temp2 if x not in set(temp1)]  # Elements in temp2 not in temp1
    return additions, removals  # Returns a tuple (additions, removals)

# Add diff highlighting to a list of strings
# Calls list_diffs() to find diffs
def diff_highlight(new, old):
    diff_tuple = list_diffs(new, old)
    new = [("+" + x.replace("\n", "\n+")) if x in diff_tuple[0] else (" " + x.replace("\n", "\n ")) for x in new]
    old = [("-" + x.replace("\n", "\n-")) if x in diff_tuple[1] else (" " + x.replace("\n", "\n ")) for x in old]
    return new, old  # Returns a tuple of new, old with diff highlighting

# Dict containing all subject channels
channels = None
async def get_channels(bot):
    global channels
    channels = await subject_channels.find_channels(bot)

def open_quotas():
    try:
        quotas = open('quotas.json', encoding='utf-8')
        quotas = json.load(quotas)
        return quotas
    except:
        return False

def open_old_quotas():
    try:
        quotas = open('quotas_old.json', encoding='utf-8')
        quotas = json.load(quotas)
        return quotas
    except:
        return False

# If quota searching is interrupted by network issues, quotas file is incomplete and does not contain the update time
def check_quotas_validity():
    quotas = open_quotas()
    if not quotas:
        return False
    try:
        if 'time' in quotas:
            return True
        else:
            return False
    except TypeError:  # Error raised if quotas file is corrupted
        return False

# Send message if course data is unavailable
embed_quota_unavailable = discord.Embed(title=f"⚠️ Course data is unavailable at the moment!",
                                        description="Try again in a minute.",
                                        color=config.color_failure)

# Calculate max page index
def find_max_page(dict, page_size):
    max_page = int(len(dict) / page_size)
    # Error: a course has no sections
    if len(dict) == 0:
        return -1
    # Edge case: number of sections is non-zero multiple of page size
    elif len(dict) % page_size == 0:
        max_page -= 1

    return max_page

# Compose message of course quotas for "quota" command
def compose_message(course_code, page=0):
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return "unavailable"

    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        return "key"
    else:
        if course_code == "time":
            return "key"
    
    # Calculate max page index
    page_size = 10
    max_page = find_max_page(course_dict['sections'], page_size)

    # Send error message if there is no sections (highly unlikely)
    if max_page == -1:
        return "no_sections"

    # Check if page number is valid
    if page < 0:
        return "p0"
    elif page > max_page:
        return "pmax"

    # Cut out one page of data
    try:
        sections_paged = list(course_dict['sections'].items())[page_size * page: page_size * (page + 1)]
    except IndexError:
        sections_paged = list(course_dict['sections'].items())[page_size * page: ]

    # Compose list
    embed_quota = discord.Embed(title=f"{course_dict['title']}",
                                color=config.color_success,
                                timestamp=time_from_stamp(quotas['time']))  # Quota update time
    
    quota_field = f"```\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"

    for key, value in sections_paged:
        quota_field += f"{trim_section(key):<8}| "
        for i in range(4, 8):
            quota_field += '{:<6}'.format(value[i].split("\n", 1)[0])
        quota_field += "\n"
    quota_field += "```"

    embed_quota.add_field(name="🍊 Sections", value=quota_field, inline=False)

    # Embed timestamp (update time) is shown behind footer
    embed_quota.set_footer(text=f"📄 Page {page + 1} of {max_page + 1}\n🕒 Last updated")
    embed_quota.set_author(name="🍊 Quotas of")

    return embed_quota

# Compose message of course info for "info" command
def compose_info(course_code):
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return "unavailable"
    
    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        return "key"
    else:
        if course_code == "time":
            return "key"
    
    embed_info = discord.Embed(title=f"{course_dict['title']}",
                               color=config.color_success,
                               timestamp=time_from_stamp(quotas['time']))  # Quota update time
    
    for key, value in course_dict['info'].items():
        key = key.capitalize()
        key = key.replace("\n", " ")

        # Split info into multiple fields
        for chunk in range(int(len(value) / 1024) + 1):
            if chunk == 0:
                field_title = f"🍊 {key}"
            else:
                field_title = f"🍊 {key} (cont.)"

            try:
                embed_info.add_field(name=field_title, value=value[1024 * chunk: 1024 * (chunk + 1)], inline=False)
            except IndexError:
                embed_info.add_field(name=field_title, value=value[1024 * chunk: ], inline=False)

    embed_info.set_footer(text=f"🕒 Last updated")
    embed_info.set_author(name="🍊 Information for")

    return embed_info

# Compose message of course sections, instructors, schedules for "sections" command
def compose_sections(course_code, page=0):
    quotas = open_quotas()

    # Check if quotas file is available
    if not check_quotas_validity():
        return "unavailable"
    
    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        return "key"
    else:
        if course_code == "time":
            return "key"
    
    embed_sections = discord.Embed(title=f"{course_dict['title']}",
                                   color=config.color_success,
                                   timestamp=time_from_stamp(quotas['time']))  # Quota update time
    
    # Calculate max page index
    page_size = 5
    max_page = find_max_page(course_dict['sections'], page_size)

    # Send error message if there is no sections
    if max_page == -1:
        return "no_sections"

    # Check if page number is valid
    if page < 0:
        return "p0"
    elif page > max_page:
        return "pmax"
    
    # Cut out one page of data
    try:
        sections_paged = list(course_dict['sections'].items())[page_size * page: page_size * (page + 1)]
    except IndexError:
        sections_paged = list(course_dict['sections'].items())[page_size * page: ]

    for key, value in sections_paged:
        section_id = key
        section_field = "```\n"

        time_list = value[1].split("\n\n\n")
        venue_list = value[2].split("\n\n\n")
        instructor_list = value[3].split("\n\n\n")

        # Make all strings single-line
        time_list = [t.replace('\n', ', ') for t in time_list]
        venue_list = [t.replace('\n', ', ') for t in venue_list]
        instructor_list = [t.replace('\n', ', ') for t in instructor_list]

        # Add strings to field
        # Add strings row by row
        for i in range(len(time_list)):
            section_field += f"{'Time':<6}| {time_list[i]}\n"
            section_field += f"{'Venue':<6}| {venue_list[i]}\n"
            section_field += f"{'By':<6}| {instructor_list[i]}\n"
            section_field += "\n"

        section_field += "```"
        embed_sections.add_field(name=f"🍊 {key}",
                                 value=section_field,
                                 inline=False)

    # Embed timestamp (update time) is shown behind footer
    embed_sections.set_footer(text=f"📄 Page {page + 1} of {max_page + 1}\n🕒 Last updated")
    embed_sections.set_author(name="🍊 Sections of")

    return embed_sections

# Helper function to check if course/section/quota changed
async def check_diffs(new_quotas=None, old_quotas=None):
    # Open quotas files
    if not new_quotas:
        new_quotas = open_quotas()
    if not old_quotas:
        old_quotas = open('quotas_old.json', encoding='utf-8')
        try:
            old_quotas = json.load(old_quotas)
        except:
            print("Old quotas file corrupted! Restart the bot.")
            return

    # No comparison if current quotas file or last quotas file is corrupted
    if (not check_quotas_validity()) or (old_quotas == {}) or ('time' not in new_quotas):
        return
    
    changed = False
    for key, value in new_quotas.items():
        # Skip 'time' entry
        if key == 'time':
            continue

        # 🥑 New course!
        if key not in old_quotas:
            # await channels.get(key[0: 4], channels['other']).send(f"🥑 **New course!**\n{value.get('title', 'Error')}\n{len(value['sections'])} sections")
            # Prepare change announcement embed: course name
            embed_new_course = discord.Embed(
                title=f"{value.get('title', 'Error')}",
                color=0x8bd5ca  # Teal
            )
            # Prepare header of change announcement
            embed_new_course.set_author(name="🥑 New course!")

            # Display list of sections
            new_course_sections = "```\n"
            new_course_sections += "\n".join(list(value['sections'].keys()))
            new_course_sections += "\n```"

            # Add field
            embed_new_course.add_field(
                name=f"🥑 {len(value['sections'])} sections",
                value=new_course_sections,
                inline=False
            )

            # Send the announcement
            await channels.get(key[0: 4], channels['other']).send(embed=embed_new_course)
            changed = True

        else:
            for key2, value2 in value['sections'].items():
                # 🍅 New section!
                if key2 not in old_quotas[key]['sections']:
                    # Quota of the new section
                    quota_new = value2[4].split("\n", 1)[0]
                    # await channels.get(key[0: 4], channels['other']).send(f"🍅 **New section!**\n{value.get('title', 'Error')}: {key2}\nQuota: {quota_new}")
                    
                    # Prepare change announcement embed: course name, section name
                    embed_new_section = discord.Embed(
                        title=f"{value.get('title', 'Error')}: {key2}",
                        color=0xed8796  # Red
                    )
                    # Prepare header of change announcement
                    embed_new_section.set_author(name="🍅 New section!")

                    # Display quota of section
                    new_section_quotas = f"```\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"
                    new_section_quotas += f"{trim_section(key2):<8}| "
                    for i in range(4, 8):
                        new_section_quotas += '{:<6}'.format(value2[i].split("\n", 1)[0])
                    new_section_quotas += "\n```"

                    # Add field
                    embed_new_section.add_field(
                        name="🍅 Quota",
                        value=new_section_quotas,
                        inline=False
                    )
                    
                    # Send the announcement
                    await channels.get(key[0: 4], channels['other']).send(embed=embed_new_section)
                    changed = True
                
                else:
                    # 🍋 Quota changed!
                    if value2[4].split("\n", 1)[0] != old_quotas[key]['sections'][key2][4].split("\n", 1)[0]:
                        # Original quota and new quota
                        quota_old = old_quotas[key]['sections'][key2][4].split("\n", 1)[0]
                        quota_new = value2[4].split("\n", 1)[0]
                        # await channels.get(key[0: 4], channels['other']).send(f"🍋 **Quota changed!**\n{value.get('title', 'Error')}: {key2}\n{quota_old} -> {quota_new}")
                        
                        # Prepare change announcement embed: course name, section name
                        embed_quota_change = discord.Embed(
                            title=f"{value.get('title', 'Error')}: {key2}",
                            color=0xeed49f  # Yellow
                        )
                        # Prepare header of change announcement
                        embed_quota_change.set_author(name="🍋 Quota changed!")

                        # Display quota change
                        changed_section_quotas = f"```\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"
                        changed_section_quotas += f"{trim_section(key2):<8}| "
                        for i in range(4, 8):
                            changed_section_quotas += '{:<6}'.format(value2[i].split("\n", 1)[0])
                        changed_section_quotas += "\n```"

                        # Add field
                        embed_quota_change.add_field(
                            name=f"🍋 {quota_old} -> {quota_new}",
                            value=changed_section_quotas,
                            inline=False
                        )

                        # Display magnitude of quota change
                        # Determine if quota added or removed
                        quota_change_mag = int(quota_new) - int(quota_old)
                        if quota_change_mag > 0:
                            quota_change_footer = f"🍋 Added {quota_change_mag} quotas"
                        else:
                            quota_change_footer = f"🍋 Removed {-quota_change_mag} quotas"
                        # Set footer
                        embed_quota_change.set_footer(text=quota_change_footer)

                        # Send the announcement
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_quota_change)
                        changed = True
                    
                    # 🥭 Date & Time changed!
                    # Initialize list of values
                    # Time list elements are guaranteed to be unique
                    time_list_new = value2[1].split("\n\n\n")
                    time_list_old = old_quotas[key]['sections'][key2][1].split("\n\n\n")

                    # Prepare change announcement text: course name, section name, section ID
                    embed_time_change = discord.Embed(
                        title=f"{value.get('title', 'Error')}: {key2}",
                        color=0xee99a0  # Maroon
                    )
                    # Prepare header of change announcement
                    embed_time_change.set_author(name="🥭 Date & Time changed!")

                    # Check additions and removals
                    time_deltas = list_diffs(time_list_new, time_list_old)
                    time_diffed = diff_highlight(time_list_new, time_list_old)

                    # Add old date & time field
                    time_old_field = "```diff\n"  # Diff syntax highlighting
                    time_old_field += "\n\n".join(time_diffed[1])
                    time_old_field += "\n```"
                    # Add field to embed
                    embed_time_change.add_field(
                        name="🥭 Old",
                        value=time_old_field,
                        inline=True  # Split view comparison
                    )

                    # Add new date & time field
                    time_new_field = "```diff\n"  # Diff syntax highlighting
                    time_new_field += "\n\n".join(time_diffed[0])
                    time_new_field += "\n```"
                    # Add field to embed
                    embed_time_change.add_field(
                        name="🥭 New",
                        value=time_new_field,
                        inline=True  # Split view comparison
                    )

                    # Display number of changes
                    embed_time_change.set_footer(text=f"🥭 {len(time_deltas[0])} additions, {len(time_deltas[1])} removals")

                    # If there is time change, send the announcement
                    if time_deltas != ([], []):
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_time_change)
                        changed = True

                    # 🥝 Venue changed!
                    # Initialize list of values
                    venue_list_new = value2[2].split("\n")
                    venue_list_old = old_quotas[key]['sections'][key2][2].split("\n")
                    # Remove empty list elements
                    venue_list_new = [venue for venue in venue_list_new if venue != ""]
                    venue_list_old = [venue for venue in venue_list_old if venue != ""]
                    # Remove duplicates
                    # Create a dict using the list items as keys to automatically remove any duplicates because dicts cannot have duplicate keys
                    # Convert dict back into a list, assign it to the list of venues
                    venue_list_new = list(dict.fromkeys(venue_list_new))
                    venue_list_old = list(dict.fromkeys(venue_list_old))

                    # Prepare change announcement text: Header, course name, section name, section ID
                    embed_venue_change = discord.Embed(
                        title=f"{value.get('title', 'Error')}: {key2}",
                        color=0xa6da95  # Green
                    )
                    # Prepare header of change announcement
                    embed_venue_change.set_author(name="🥝 Venue changed!")

                    # Check additions and removals
                    venue_deltas = list_diffs(venue_list_new, venue_list_old)
                    venue_diffed = diff_highlight(venue_list_new, venue_list_old)

                    # Add old venue field
                    venue_old_field = "```diff\n"  # Diff syntax highlighting
                    venue_old_field += "\n".join(venue_diffed[1])
                    venue_old_field += "\n```"
                    # Add field to embed
                    embed_venue_change.add_field(
                        name="🥝 Old",
                        value=venue_old_field,
                        inline=True  # Split view comparison
                    )

                    # Add new venue field
                    venue_new_field = "```diff\n"  # Diff syntax highlighting
                    venue_new_field += "\n".join(venue_diffed[0])
                    venue_new_field += "\n```"
                    # Add field to embed
                    embed_venue_change.add_field(
                        name="🥝 New",
                        value=venue_new_field,
                        inline=True  # Split view comparison
                    )
                    
                    # Display number of changes
                    embed_venue_change.set_footer(text=f"🥝 {len(venue_deltas[0])} additions, {len(venue_deltas[1])} removals")

                    # If there is venue change, send the announcement
                    if venue_deltas != ([], []):
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_venue_change)
                        changed = True
                    
                    # 🍇 Instructor changed!
                    # Initialize list of values
                    inst_list_new = value2[3].split("\n")
                    inst_list_old = old_quotas[key]['sections'][key2][3].split("\n")
                    # Remove empty list elements
                    inst_list_new = [inst for inst in inst_list_new if inst != ""]
                    inst_list_old = [inst for inst in inst_list_old if inst != ""]
                    # Remove duplicates
                    # Create a dict using the list items as keys to automatically remove any duplicates because dicts cannot have duplicate keys
                    # Convert dict back into a list, assign it to the list of instructors
                    inst_list_new = list(dict.fromkeys(inst_list_new))
                    inst_list_old = list(dict.fromkeys(inst_list_old))

                    # Prepare change announcement text: Header, course name, section name, section ID
                    embed_inst_change = discord.Embed(
                        title=f"{value.get('title', 'Error')}: {key2}",
                        color=0xc6a0f6  # Mauve
                    )
                    # Prepare header of change announcement
                    embed_inst_change.set_author(name="🍇 Instructor changed!")

                    # Check additions and removals
                    inst_deltas = list_diffs(inst_list_new, inst_list_old)
                    inst_diffed = diff_highlight(inst_list_new, inst_list_old)

                    # Add old instructor field
                    inst_old_field = "```diff\n"  # Diff syntax highlighting
                    inst_old_field += "\n".join(inst_diffed[1])
                    inst_old_field += "\n```"
                    # Add field to embed
                    embed_inst_change.add_field(
                        name="🍇 Old",
                        value=inst_old_field,
                        inline=True  # Split view comparison
                    )

                    # Add new instructor field
                    inst_new_field = "```diff\n"  # Diff syntax highlighting
                    inst_new_field += "\n".join(inst_diffed[0])
                    inst_new_field += "\n```"
                    # Add field to embed
                    embed_inst_change.add_field(
                        name="🍇 New",
                        value=inst_new_field,
                        inline=True  # Split view comparison
                    )
                    
                    # Display number of changes
                    embed_inst_change.set_footer(text=f"🍇 {len(inst_deltas[0])} additions, {len(inst_deltas[1])} removals")

                    # If there is instructor change, send the announcement
                    if inst_deltas != ([], []):
                        await channels.get(key[0: 4], channels['other']).send(embed=embed_inst_change)
                        changed = True

    for key3, value3 in old_quotas.items():
        # Skip "time" entry
        if key3 == "time":
            continue
        # ☕ Course deleted!
        if key3 not in new_quotas:
            # await channels.get(key3[0: 4], channels['other']).send(f"☕ **Course deleted!**\n{value3.get('title', 'Error')}\n{len(value3['sections'])} sections")
            # Prepare change announcement embed: course name
            embed_delete_course = discord.Embed(
                title=f"{value3.get('title', 'Error')}",
                color=0xf4dbd6  # Rosewater
            )
            # Prepare header of change announcement
            embed_delete_course.set_author(name="☕ Course deleted!")

            # Display list of sections
            delete_course_sections = "```\n"
            delete_course_sections += "\n".join(list(value3['sections'].keys()))
            delete_course_sections += "\n```"

            # Add field
            embed_delete_course.add_field(
                name=f"☕ {len(value3['sections'])} sections",
                value=delete_course_sections,
                inline=False
            )

            # Send the announcement
            await channels.get(key3[0: 4], channels['other']).send(embed=embed_delete_course)
            changed = True

        else:
            for key4, value4 in value3['sections'].items():
                # 🍹 Section deleted!
                if key4 not in new_quotas[key3]['sections']:
                    # await channels.get(key3[0: 4], channels['other']).send(f"🍹 **Section deleted!**\n{value3.get('title', 'Error')}: {key4}")
                    # Prepare change announcement embed: course name, section name
                    embed_delete_section = discord.Embed(
                        title=f"{value3.get('title', 'Error')}: {key4}",
                        color=0xf5a97f  # Peach
                    )
                    # Prepare header of change announcement
                    embed_delete_section.set_author(name="🍹 Section deleted!")

                    # Display quota of section
                    delete_section_quotas = f"```\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"
                    delete_section_quotas += f"{trim_section(key4):<8}| "
                    for i in range(4, 8):
                        delete_section_quotas += '{:<6}'.format(value4[i].split("\n", 1)[0])
                    delete_section_quotas += "\n```"
                    
                    # Add field
                    embed_delete_section.add_field(
                        name="🍹 Quota",
                        value=delete_section_quotas,
                        inline=False
                    )
                    
                    # Send the announcement
                    await channels.get(key3[0: 4], channels['other']).send(embed=embed_delete_section)
                    changed = True

    return changed

async def download_quotas(current_loop):
    url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/"
    
    try:
        page = requests.get(url)

        soup = bs4.BeautifulSoup(page.content, "html.parser")
    
        letters = soup.select('.depts')[0]
    except:
        return update_time()

    quotas = {}

    for letter in letters:
        sub_url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/subject/{letter.get_text()}"

        try:
            sub_page = requests.get(sub_url, timeout=10)
        except:
            print("Timed out!")
            return update_time()

        sub_soup = bs4.BeautifulSoup(sub_page.content, "html.parser")

        classes = sub_soup.select('#classes > .course')

        for course in classes:
            try:
                course_dict = {}

                course_title = course.find("h2").get_text()
            
                course_code = course.select(".courseanchor > a")[0]["name"]
            except:
                continue
            
            # No more course info im lazy
            # Course info start
            course_info = course.select(".courseinfo > .courseattr.popup > .popupdetail > table")[0]
            course_info_rows = course_info.select('tr')
            info_dict = {}

            for row in course_info_rows:
                try:
                    heading = row.find('th')
                    heading = heading.get_text("\n")

                    data = row.select('td')[0]
                    data = data.get_text("\n")

                    info_dict[heading] = data
                except:
                    continue
            # Course info end
            
            section_dict = {}
            course_sections = course.select(".sections")[0]
            course_sections = course_sections.find_all("tr", ["newsect secteven", "newsect sectodd", "secteven", "sectodd"])

            for idx, section in enumerate(course_sections):
                # Append extra section times/instructor information to section entry (1/2)
                if section['class'][0] in ["secteven", "sectodd"]:
                    continue

                section_data = section.select("td")
                section_cols = []
                for col in section_data:
                    section_cols.append(col.get_text("\n"))
                
                # Append extra section times/instructor information to section entry (2/2)
                # try:
                #     next_section = course_sections[idx + 1]
                #     if next_section['class'] in ["secteven", "sectodd"]:
                #         extra_data = next_section.select("td")

                #         for idx2, datum in enumerate(extra_data):
                #             section_cols[idx2 + 1] += f"\n{datum}"
                # except IndexError:
                #     pass
                    
                section_dict[section_cols[0]] = section_cols

                try:
                    next = 1
                    while course_sections[idx + next]['class'][0] in ["secteven", "sectodd"]:
                        next_section = course_sections[idx + next]
                        if next_section['class'][0] in ["secteven", "sectodd"]:
                            extra_data = next_section.select("td")

                            for idx2, datum in enumerate(extra_data):
                                section_dict[section_cols[0]][idx2 + 1] += "\n\n\n" + datum.get_text("\n")
                        
                        next += 1
                except IndexError:
                    pass
            
            # Add data to dictionary for course
            course_dict['title'] = course_title
            course_dict['sections'] = section_dict
            course_dict['info'] = info_dict

            quotas[course_code] = course_dict
    
    quotas['time'] = update_time()
    
    # Move quotas of last minute to another file if quotas changed
    # oldfile = open('quotas_old.json', 'w', encoding='utf-8')
    # old_quotas = open_quotas()
    # if check_quotas_validity():
    #     json.dump(old_quotas, oldfile, indent = 4)
    # # Make old quotas file empty if quota file is corrupted
    # else:
    #     json.dump({}, oldfile, indent = 4)
    if current_loop == 0:
        oldfile = open('quotas_old.json', 'w', encoding='utf-8')
        try:
            json.dump(quotas, oldfile, indent=4)
        except:
            json.dump({}, oldfile, indent=4)
    elif await check_diffs(quotas, open_old_quotas()):
        oldfile = open('quotas_old.json', 'w', encoding='utf-8')
        try:
            json.dump(quotas, oldfile, indent=4)
        except:
            json.dump({}, oldfile, indent=4)

    # Save quotas to json file
    outfile = open('quotas.json', 'w', encoding='utf-8')
    try:
        json.dump(quotas, outfile, indent = 4)
    except:
        json.dump({}, outfile, indent=4)

    return update_time() 
