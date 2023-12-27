<h1 align="center">
    🍄
    <br>
    tab-bot
</h1>

<h3 align="center">
    Two Discord bots that does helpful things with course data in HKUST!<br>
</h3>

<p align="center">
    🐈‍⬛
</p>

<p align="center">
    Try them out in our <a href="https://discord.gg/RNmMMF6xHY">server</a>!
</p>

## 🥁 Tab
Tab searches the servers of HKUST to get course data and look for changes!

- Tab sends notifications to you when changes are recorded!
- It updates every 1.5 minutes to catch changes as quickly as possible!

## 🍦 Hill
Hill uses data collected by Tab to provide course info on demand! Using its slash commands, you can look up:

- Quotas
- Sections (schedules, venues, instructors)
- General information (pre-reqs, exclusions, descriptions)
- Courses by course code prefix, Common Core area, and instructor

Hill can also be added to other servers!

## 🍋 Course notifications
Our bots work together to notify you of changes to courses you care about! There are two ways to receive course notifications.

- **✨ New! ✨** Course subscriptions<br>
Subscribe to a course using Hill's commands, and Tab will DM you about its changes! You're in control of what you receive, course by course!<br>
    > [⚠️](https://youtu.be/FXsGCieXm1E) Discord only allows DMs between users sharing a mutual server. Even if you subscribed from another server, you're recommended to join our server so Tab can DM you!
- Course channels<br>
Tab also sends course notifications to our server, sorted into channels by course code prefix. You can toggle notifications for all courses with the same prefix by customizing notification settings for each course channel.

## 🖼️ Screenshots
<details><summary>🥁 Tab</summary>

|||
| :---         | :---    |
| A new course is added | ![Tab sends a message when a new course is added](sample_screenshots/tab/new_course.png) |
| A new section (of an existing course) is added | ![Tab sends a message when a new section (of an existing course) is added](sample_screenshots/tab/new_section.png) |
| The quota of a section is changed | ![Tab sends a message when the quota of a section is changed](sample_screenshots/tab/quota_changed.png) |
| The date & time of a section is changed | ![Tab sends a message when the date and time of a section is changed](sample_screenshots/tab/time_changed.png) |
| The venue of a section is changed | ![Tab sends a message when the venue of a section is changed](sample_screenshots/tab/venue_changed.png) |
| The instructor of a section is changed | ![Tab sends a message when the instructor of a section is changed](sample_screenshots/tab/inst_changed.png) |
| The remarks of a section is changed | ![Tab sends a message when the remarks of a section is changed](sample_screenshots/tab/remarks_changed.png) |
| The info of a course is changed | ![Tab sends a message when the info of a course is changed](sample_screenshots/tab/info_changed.png) |
| A course is deleted | ![Tab sends a message when a course is deleted](sample_screenshots/tab/course_deleted.png) |
| A section (of a course) is deleted | ![Tab sends a message when a section (of a course) is deleted](sample_screenshots/tab/section_deleted.png) |
|||
</details>

<details><summary>🍦 Hill</summary>

|||
| :---         | :---    |
| `/info` | ![Using Hill's command: `/info` to get information about a course](sample_screenshots/hill/info.png) |
| `/sections` | ![Using Hill's command: `/sections` to get sections of a course](sample_screenshots/hill/sections.png) |
| `/quota` | ![Using Hill's command: `/quota` to get quotas of a course](sample_screenshots/hill/quota.png) |
| `/search` by course code prefix | ![Using Hill's command: `/search` to search courses by given prefix](sample_screenshots/hill/search_prefix.png) |
| `/search` by Common Core area | ![Using Hill's command: `/search` to search courses by given Common Core area](sample_screenshots/hill/search_cc.png) |
| `/search` by instructor | ![Using Hill's command: `/search` to search courses by given instructor name](sample_screenshots/hill/search_inst.png) |
| `/history info` | ![Using Hill's command: `/history info` to get information about a course in a previous semester](sample_screenshots/hill/history_info.png) |
| `/history sections` | ![Using Hill's command: `/history sections` to get sections of a course in a previous semester](sample_screenshots/hill/history_sections.png) |
| `/history quota` | ![Using Hill's command: `/history quota` to get sections of a course in a previous semester](sample_screenshots/hill/history_quota.png) |
| `/history search` | ![Using Hill's command: `/history search` to search courses in a previous semester](sample_screenshots/hill/history_search.png) |
| `/sub sub` | ![Using Hill's command: `/sub sub` to subscribe to a course](sample_screenshots/hill/sub_sub.png) |
| `/sub unsub` | ![Using Hill's command: `/sub unsub` to unsubscribe from a course](sample_screenshots/hill/sub_unsub.png) |
| `/sub show` | ![Using Hill's command: `/sub show` to show user's subscriptions](sample_screenshots/hill/sub_show.png) |
|||
</details>

---

## 🌟 Credits
Tab and Hill are made possible by the following projects:
- [evnchn/Course-Quota-Online](https://github.com/evnchn/Course-Quota-Online): Uses the same technologies as this project!
- [henveloper/discord-ustquotatracker](https://github.com/henveloper/discord-ustquotatracker): The original UST course quota tool!
- [HKUST Class Schedule & Quota](https://w5.ab.ust.hk/wcq/cgi-bin/): The *original* original course quota website from HKUST!
