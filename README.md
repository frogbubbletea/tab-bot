<h1 align="center">
    🍄
    <br>
    tab-bot
</h1>

<h2 align="center">
    Two Discord bots that does helpful things with course data in HKUST!
</h2>

<h3 align="center">
    🐈‍⬛
</h3>

<p align="center">
    Try them out in our <a href="https://discord.gg/RNmMMF6xHY">server</a>!
</p>

## 🥁 Tab
Tab searches the servers of HKUST to get course data and look for changes!

- Tab [sends](https://youtu.be/FXsGCieXm1E) notifications to you when changes are recorded!
- It updates every 1.5 minutes to catch changes as quickly as possible!

## 🍦 Hill
Hill uses data collected by Tab to provide course info on demand! Using its slash commands, you can look up:

- Quotas
- Sections (schedules, venues, instructors)
- General information (pre-reqs, exclusions, descriptions)
- Courses by course code prefix and Common Core area

Hill can also be added to other servers!

## 🍋 Course notifications
Our bots work together to notify you of changes to courses you care about! We offer two ways of receiving course notifications.

- **✨ New! ✨** Course subscriptions
<br>
Subscribe to a course using Hill's commands, and Tab will DM you about its changes! You're in control of what you receive, course by course!
<br>
    > [!NOTE]<br>
    > Discord only allows DMs between users sharing a mutual server. Even if you subscribed from another server, you're recommended to join our server so that Tab can DM you!
<br>
- Course channels
<br>
Tab also sends course notifications to our server, sorted into channels by course code prefix. You can toggle notifications for all courses with the same prefix by customizing notification settings for each course channel.

## 🖼️ Screenshots
|||
| :---         | :---    |
| Tab: a new course is added | ![Tab sends a message when a new course is added](sample_screenshots/tab/new_course.png) |
| Tab: a new section (of an existing course) is added | ![Tab sends a message when a new section (of an existing course) is added](sample_screenshots/tab/new_section.png) |
| Tab: the quota of a section is changed | ![Tab sends a message when the quota of a section is changed](sample_screenshots/tab/quota_changed.png) |
| Tab: the date & time of a section is changed | ![Tab sends a message when the date and time of a section is changed](sample_screenshots/tab/time_changed.png) |
| Tab: the venue of a section is changed | ![Tab sends a message when the venue of a section is changed](sample_screenshots/tab/venue_changed.png) |
| Tab: the instructor of a section is changed | ![Tab sends a message when the instructor of a section is changed](sample_screenshots/tab/inst_changed.png) |
| Tab: the remarks of a section is changed | ![Tab sends a message when the remarks of a section is changed](sample_screenshots/tab/remarks_changed.png) |
| Tab: the info of a course is changed | ![Tab sends a message when the info of a course is changed](sample_screenshots/tab/info_changed.png) |
| Tab: a course is deleted | ![Tab sends a message when a course is deleted](sample_screenshots/tab/course_deleted.png) |
| Tab: a section (of a course) is deleted | ![Tab sends a message when a section (of a course) is deleted](sample_screenshots/tab/section_deleted.png) |
|||
| Using Hill's command: `/info` | ![Using Hill's command: `/info`](sample_screenshots/hill/info.png) |
| Using Hill's command: `/sections` | ![Using Hill's command: `/sections`](sample_screenshots/hill/sections.png) |
| Using Hill's command: `/quota` | ![Using Hill's command: `/quota`](sample_screenshots/hill/quota.png) |
| Using Hill's command: `/list` to show all courses with given prefix | ![Using Hill's command: `/list` to show all courses with given prefix](sample_screenshots/hill/list_prefix.png) |
| Using Hill's command: `/list` to show all Common Core courses in a given area | ![Using Hill's command: `/list` to show all Common Core courses in a given area](sample_screenshots/hill/list_cc.png) |
| Using Hill's command: `/sub sub` | ![Using Hill's command: `/sub sub`](sample_screenshots/hill/sub_sub.png) |
| Using Hill's command: `/sub unsub` | ![Using Hill's command: `/sub unsub`](sample_screenshots/hill/sub_unsub.png) |
| Using Hill's command: `/sub show` | ![Using Hill's command: `/sub show`](sample_screenshots/hill/sub_show.png) |
---

## 🌟 Credits
Tab and Hill are made possible by the following projects:
- [evnchn/Course-Quota-Online](https://github.com/evnchn/Course-Quota-Online): Uses the same technologies as this project!
- [henveloper/discord-ustquotatracker](https://github.com/henveloper/discord-ustquotatracker): The original UST course quota tool!
- [HKUST Class Schedule & Quota](https://w5.ab.ust.hk/wcq/cgi-bin/): The *original* original course quota website from UST!