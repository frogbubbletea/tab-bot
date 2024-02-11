# import pymongo
from tinydb import TinyDB, Query
import discord

import io
import base64
import datetime
from zoneinfo import ZoneInfo

import mplcatppuccin
from mplcatppuccin.palette import load_color
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

import config
import get_quota

# Configure plot theme
plt.style.use(["ggplot", "latte"])

# Load line colors
quota_line_color = load_color("latte", "yellow")
quota_bg_color = load_color("macchiato", "yellow")  # Uncovered area is equal to enrolled
enrol_line_color = load_color("latte", "yellow")
enrol_bg_color = load_color("macchiato", "yellow")
avail_line_color = load_color("latte", "sky")
avail_bg_color = load_color("macchiato", "sky")
waitlist_line_color = load_color("latte", "red")
waitlist_bg_color = load_color("macchiato", "red")
axis_line_color = load_color("latte", "text")

# Configure plot font
# plt.rcParams["font.family"] = "Inter"

# Get default fig size to enlarge for reserved quota subplots
figsize = plt.rcParams.get('figure.figsize')

def compose_plot(course_code: str, section: str, page=0):
    # Displaying placeholder plot for now
    # fig, ax = plt.subplots()
    # ax.plot([0, 1, 2, 3], [1, 2, 3, 4])
    # return fig

    # Find all snapshots of specified section
    # course_col = get_quota.trend_db[course_code]
    course_col = get_quota.trend_db.table(course_code, cache_size=0)
    section_query = { "section_code": section }
    # section_snapshots = list(course_col.find(section_query, sort=[('time', 1)]))
    section_snapshots = sorted(course_col.search(Query().fragment(section_query)), key=lambda k: k['time'])

    # Add intermediate data points at 1 interval before recorded change if needed
    for i in section_snapshots:
        i_idx = section_snapshots.index(i)
        if section_snapshots[i_idx]["loop"] - section_snapshots[i_idx - 1]["loop"] > 1:
            section_snapshots.insert(
                i_idx,
                {
                    "section_code": section,
                    "class_nbr": section_snapshots[i_idx]["class_nbr"],
                    "time": section_snapshots[i_idx]["time"] - get_quota.trend_snapshot_interval,
                    "loop": section_snapshots[i_idx]["loop"] - 1,
                    "total": section_snapshots[i_idx - 1]["total"],  # Should have the same quotas as the last snapshot before recorded change
                    "reserved": section_snapshots[i_idx - 1]["reserved"]
                }
            )
    
    # Set latest data point at last update time if no change recorded at that time
    if section_snapshots[-1]["loop"] < get_quota.get_trend_update_time(True):
        section_snapshots.append(
            {
                "section_code": section,
                "class_nbr": section_snapshots[-1]["class_nbr"],
                "time": get_quota.get_trend_update_time(),
                "loop": get_quota.get_trend_update_time(True),
                "total": section_snapshots[-1]["total"],  # Should have the same quotas as the last snapshot before recorded change
                "reserved": section_snapshots[-1]["reserved"]
            }
        )

    # (Total) Format data into lines
    time_xpoints = np.array([get_quota.time_from_stamp(d.get('time', 0)) for d in section_snapshots])
    total_quota_ypoints = np.array([d.get('total', [0, 0, 0, 0])[0] for d in section_snapshots])
    total_enrol_ypoints = np.array([d.get('total', [0, 0, 0, 0])[1] for d in section_snapshots])
    total_avail_ypoints = np.array([d.get('total', [0, 0, 0, 0])[2] for d in section_snapshots])
    total_wait_ypoints = np.array([0 - d.get('total', [0, 0, 0, 0])[3] for d in section_snapshots])  # Display waitlist in negative Y axis
    total_wait_ypoints_ma = np.ma.masked_where(total_wait_ypoints >= 0, total_wait_ypoints)  # Don't display waitlist line when waitlist is 0

    # (Reserved) Format data into lines
    # Find list of reserved departments
    reserved_depts_list = []
    for snapshot in section_snapshots:
        reserved_quotas = snapshot.get("reserved", [])
        if reserved_quotas == []:
            continue
        else:
            for quota in reserved_quotas:
                try:
                    reserved_depts_list.append(quota[0])
                    reserved_depts_list = list(set(reserved_depts_list))  # Remove duplicates
                except KeyError:
                    continue

    # Get snapshots of reserved quotas for each department
    reserved_depts_dict = {}
    for dept in reserved_depts_list:
        # Prepare array for dept
        reserved_depts_dict[dept] = np.empty((0, 3))
        # Look through all snapshots to find reserved quota for dept
        for snapshot in section_snapshots:
            snapshot_reserved_list = snapshot.get("reserved", [])
            snapshot_reserved_quota_of_dept = [i[1: 4] for i in snapshot_reserved_list if i[0] == dept]
            if len(snapshot_reserved_quota_of_dept) <= 0:
                snapshot_reserved_quota_of_dept = [[0, 0, 0]]
            reserved_depts_dict[dept] = np.append(reserved_depts_dict[dept], snapshot_reserved_quota_of_dept, 0)
        # Store all snapshots of quota/enrol/avail in each row
        reserved_depts_dict[dept] = np.transpose(reserved_depts_dict[dept])

    # Create subplots for total and reserved quotas
    fig, axes = plt.subplots(len(reserved_depts_list) + 1, figsize=(figsize[0], figsize[1] * (len(reserved_depts_list) + 1)))
    # Determine if there is reserved quotas, assign the topmost subplot to ax (total quotas)
    ax = axes[0] if len(reserved_depts_list) > 0 else axes
    res_axes = axes[1: ] if len(reserved_depts_list) > 0 else []

    # Set axes limits 
    # Total
    ax.set_xlim([time_xpoints.min(), time_xpoints.max()])
    ylim_value = np.array([total_quota_ypoints.max(), abs(total_wait_ypoints.min())]).max()  # Determine largest magnitude on the graph
    ax.set_ylim([0 - ylim_value - 10, ylim_value + 10])
    # Reserved
    [rax.set_xlim([time_xpoints.min(), time_xpoints.max()]) for rax in res_axes]
    [rax.set_ylim([0, ylim_value + 10]) for rax in res_axes]

    # Set x-axis label to date and time (Timezone of HKUST)
    # https://stackoverflow.com/questions/70805592/pyplot-positive-values-on-y-axis-in-both-directions
    axis_timeformat = mdates.DateFormatter('%m/%d %H:%M', tz=get_quota.hkust_time_zone)
    # Total
    ax.xaxis.set_major_formatter(axis_timeformat)
    # Reserved
    [rax.xaxis.set_major_formatter(axis_timeformat) for rax in res_axes]

    # Set y-axis label to absolute value
    # https://stackoverflow.com/questions/70805592/pyplot-positive-values-on-y-axis-in-both-directions
    # Total
    ax.yaxis.set_major_formatter(lambda x, pos: f'{abs(x):g}')
    # Reserved
    [rax.yaxis.set_major_formatter(lambda x, pos: f'{abs(x):g}') for rax in res_axes]

    # Plot the graph
    # Total
    ax.plot(time_xpoints, total_quota_ypoints, color=quota_line_color, label="Quota")
    ax.fill_between(time_xpoints, total_quota_ypoints, color=quota_bg_color)

    # ax.plot(time_xpoints, total_enrol_ypoints, color=enrol_line_color)
    # ax.fill_between(time_xpoints, total_enrol_ypoints, color=enrol_bg_color, alpha=0.3)

    ax.plot(time_xpoints, total_avail_ypoints, color=avail_line_color, label="Avail")
    ax.fill_between(time_xpoints, total_avail_ypoints, color=avail_bg_color)

    ax.plot(time_xpoints, total_wait_ypoints_ma, color=waitlist_line_color, label="Wait")
    ax.fill_between(time_xpoints, total_wait_ypoints_ma, color=waitlist_bg_color)
    # Reserved
    [rax.plot(time_xpoints, reserved_depts_dict[reserved_depts_list[idx]][0], color=quota_line_color, label="Quota") for idx, rax in enumerate(res_axes)]
    [rax.fill_between(time_xpoints, reserved_depts_dict[reserved_depts_list[idx]][0], color=quota_bg_color) for idx, rax in enumerate(res_axes)]

    # [rax.plot(time_xpoints, reserved_depts_dict[reserved_depts_list[idx]][1], color=enrol_line_color, label="Enrol") for idx, rax in enumerate(res_axes)]
    # [rax.fill_between(time_xpoints, reserved_depts_dict[reserved_depts_list[idx]][1], color=enrol_bg_color) for idx, rax in enumerate(res_axes)]

    [rax.plot(time_xpoints, reserved_depts_dict[reserved_depts_list[idx]][2], color=avail_line_color, label="Avail") for idx, rax in enumerate(res_axes)]
    [rax.fill_between(time_xpoints, reserved_depts_dict[reserved_depts_list[idx]][2], color=avail_bg_color) for idx, rax in enumerate(res_axes)]

    # Highlight the x-axis
    # Total
    ax.plot(time_xpoints, np.zeros_like(time_xpoints), color=axis_line_color)
    # Reserved
    [rax.plot(time_xpoints, np.zeros_like(time_xpoints), color=axis_line_color) for rax in res_axes]

    # Rotate x-axis labels for date and time display
    fig.autofmt_xdate()

    # Add legend
    # Total
    ax.legend()
    # Reserved
    [rax.legend() for rax in res_axes]

    # Set axes labels and title
    # Main title
    main_title = f"{course_code[0: 4] + ' ' + course_code[4: ]} {section}"
    fig.suptitle(main_title)
    # Total
    ax.set_xlabel("Time")
    ax.set_ylabel("No. of people")
    ax.set_title("Total")
    # Reserved
    [rax.set_xlabel("Time") for rax in res_axes]
    [rax.set_ylabel("No. of people") for rax in res_axes]
    [rax.set_title(f"Reserved ({reserved_depts_list[idx]})") for idx, rax in enumerate(res_axes)]

    # Finish
    return fig

def compose_embed_with_plot(course_code: str, section: str, page=0):
    # Placeholder course code and section code
    # course_title = "COMP 4521 - Mobile Application Development (3 units)"
    # section_name = "L1 (2131)"

    quotas = get_quota.open_quotas()

    # Check if quotas file is available
    if not get_quota.check_quotas_validity():
        return "unavailable", None
    
    # Check if course code is valid
    try:
        course_dict = quotas[course_code]
    except KeyError:
        return "course_code", None
    else:
        if course_code == "time":
            return "course_code", None
    # Get the course title from the course code
    course_title = course_dict.get("title", "Error")
    
    # Check if section code is valid
    # Get list of (trimmed) section codes to compare against input
    section_codes = list(map(get_quota.trim_section, course_dict["sections"].keys()))
    try:
        section_idx = section_codes.index(section)
    except ValueError:
        return "section_code", None
    # Get the full section code from the input
    section_name = list(course_dict["sections"].keys())[section_idx]

    # Compose embed containing the plot
    embed_plot = discord.Embed(
        title=f"{course_title}: {section_name}",
        color=config.color_success,
        timestamp=get_quota.time_from_stamp(get_quota.get_trend_update_time())
    )

    # Set heading and footer
    embed_plot.set_author(name="🍊 Enrollment graph of")
    embed_plot.set_footer(text="🕒 Last updated")

    # Plot the section's statistics
    section_plot_fig = compose_plot(course_code, section)
    section_plot_stringIObytes = io.BytesIO()

    # Export image of plot to discord
    section_plot_fig.savefig(section_plot_stringIObytes, format='png')
    section_plot_stringIObytes.seek(0)
    section_plot_png_data = base64.b64encode(section_plot_stringIObytes.read()).decode()
    section_plot_image_file = discord.File(io.BytesIO(base64.b64decode(section_plot_png_data)), filename="section_plot.png")
    embed_plot.set_image(url="attachment://section_plot.png")

    return embed_plot, section_plot_image_file
    