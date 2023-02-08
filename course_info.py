# info.py
import requests
import bs4

import os
import json
from datetime import datetime

from quotas_operations import open_quotas, check_quotas_validity

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

# Structure of the quotas dictionary
# {
    # course1: {
    #     course1_title: "",
    #     sections: {
    #         section1: [],
    #         section2: [],
    #         section3: []
    #     }
    # },
    # time: ""
# }

def update_time():
    now = datetime.now()
    date_time = now.strftime("%Y/%m/%d %H:%M:%S")
    return date_time

def download_quotas():
    url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/"
    page = requests.get(url)

    soup = bs4.BeautifulSoup(page.content, "html.parser")
    
    letters = soup.select('.depts')[0]

    quotas = {}

    for letter in letters:
        sub_url = f"https://w5.ab.ust.hk/wcq/cgi-bin/{semester_code}/subject/{letter.get_text()}"

        sub_page = requests.get(sub_url)

        sub_soup = bs4.BeautifulSoup(sub_page.content, "html.parser")

        classes = sub_soup.select('#classes > .course')

        for course in classes:
            course_dict = {}

            course_title = course.find("h2").get_text()
            
            course_code = course.select(".courseanchor > a")[0]["name"]
            
            # No more course info im lazy
            # course_info = course.select(".courseinfo > .courseattr.popup > .popupdetail > table")[0]
            # course_info_rows = course_info.select('tr')
            # course_headings = []
            # course_datas = []
            # for row in course_info_rows:
            #     heading = row.select('th')[0]
            #     heading = heading.get_text("\n")
            #     print(heading)
            #     course_headings.append(heading)
            #     data = row.select('td')[0]
            #     data = data.get_text("\n")
            #     course_datas.append(data)
            
            section_dict = {}
            course_sections = course.select(".sections")[0]
            course_sections = course_sections.find_all("tr", ["newsect secteven", "newsect sectodd"])

            for section in course_sections:
                section_data = section.select("td")
                section_cols = []
                for col in section_data:
                    section_cols.append(col.get_text("\n"))
                section_dict[section_cols[0]] = section_cols
            
            # Add data to dictionary for course
            course_dict['title'] = course_title
            course_dict['sections'] = section_dict

            quotas[course_code] = course_dict
    
    quotas['time'] = update_time()
    
    # Move quotas of last minute to another file
    oldfile = open('quotas_old.json', 'w', encoding='utf-8')
    old_quotas = open_quotas()
    if check_quotas_validity():
        json.dump(old_quotas, oldfile, indent = 4)
    # Make old quotas file empty if quota file is corrupted
    else:
        json.dump({}, oldfile, indent = 4)

    # Save quotas to json file
    outfile = open('quotas.json', 'w', encoding='utf-8')
    json.dump(quotas, outfile, indent = 4)

    return update_time() 

# Test run
# download_quotas()         