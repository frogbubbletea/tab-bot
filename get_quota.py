# get_quota.py
import requests
import bs4

import discord

import os
import json
from datetime import datetime
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
semester_code = 2230

def trim_section(section_code):
    section_trim = re.findall("[A-Z]+[0-9]*[A-Z]*", section_code)[0]
    return section_trim

def update_time():
    now = datetime.now()
    date_time = now.strftime("%Y/%m/%d %H:%M:%S")
    return date_time

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
        color=config.color_success)
    
    quota_field = f"```\n{'Section':<8}| {'Quota':<6}{'Enrol':<6}{'Avail':<6}{'Wait':<6}\n"

    for key, value in sections_paged:
        quota_field += f"{trim_section(key):<8}| "
        for i in range(4, 8):
            quota_field += '{:<6}'.format(value[i].split("\n", 1)[0])
        quota_field += "\n"
    quota_field += "```"

    embed_quota.add_field(name="🍊 Sections", value=quota_field, inline=False)

    embed_quota.set_footer(text=f"📄 Page {page + 1} of {max_page + 1}\n🕒 Last updated:\n{quotas['time']}")
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
                               color=config.color_success)
    
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
    
    embed_info.set_footer(text=f"🕒 Last updated:\n{quotas['time']}")
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
                                   color=config.color_success)
    
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
        
    embed_sections.set_footer(text=f"📄 Page {page + 1} of {max_page + 1}\n🕒 Last updated:\n{quotas['time']}")
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
        # New course
        if key not in old_quotas:
            await channels.get(key[0: 4], channels['other']).send(f"🥑 **New course!**\n{value.get('title', 'Error')}\n{len(value['sections'])} sections")
            changed = True
        else:
            for key2, value2 in value['sections'].items():
                # New section
                if key2 not in old_quotas[key]['sections']:
                    quota_new = value2[4].split("\n", 1)[0]
                    await channels.get(key[0: 4], channels['other']).send(f"🍅 **New section!**\n{value.get('title', 'Error')}: {key2}\nQuota: {quota_new}")
                    changed = True
                # Quota change
                elif value2[4].split("\n", 1)[0] != old_quotas[key]['sections'][key2][4].split("\n", 1)[0]:  
                    quota_old = old_quotas[key]['sections'][key2][4].split("\n", 1)[0]
                    quota_new = value2[4].split("\n", 1)[0]
                    await channels.get(key[0: 4], channels['other']).send(f"🍋 **Quota changed!**\n{value.get('title', 'Error')}: {key2}\n{quota_old} -> {quota_new}")
                    changed = True
    
    for key3, value3 in old_quotas.items():
        # Skip "time" entry
        if key3 == "time":
            continue
        # Deleted course
        if key3 not in new_quotas:
            await channels.get(key3[0: 4], channels['other']).send(f"☕ **Course deleted!**\n{value3.get('title', 'Error')}\n{len(value3['sections'])} sections")
            changed = True
        else:
            for key4, value4 in value3['sections'].items():
                # Deleted section
                if key4 not in new_quotas[key3]['sections']:
                    await channels.get(key3[0: 4], channels['other']).send(f"🍹 **Section deleted!**\n{value3.get('title', 'Error')}: {key4}")
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
            course_dict = {}

            course_title = course.find("h2").get_text()
            
            course_code = course.select(".courseanchor > a")[0]["name"]
            
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