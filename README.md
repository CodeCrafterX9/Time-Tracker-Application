# ⏱️ TimeTrack — Time Tracker, Task Planner & Calendar

**TimeTrack** is an all-in-one desktop productivity app built with **Python and Tkinter**.

It combines a **Pomodoro/stopwatch timer, task manager, scheduling calendar, review & planning tools, analytics, and a notes scratchpad** in one place.

Everything is stored locally using **CSV and JSON files**, so your data stays safe on your machine.

> 🔒 **No account. No cloud. No internet required. Your data stays yours.**

---

## 📦 Download

**[⬇ Download the latest version (.exe)](https://github.com/CodeCrafterX9/Time-Tracker-Application/releases/download/v1.0.0/DailyPlanner-v1.0.0.exe)**

No Python needed — just download and run.

> The link above always points to the newest release automatically. If your asset filename is different (e.g. `TimeTracker.exe` or `TimeTrack-Setup.exe`), swap it into the URL above and in the table below.

### All versions

| Version | Release date | Notes | Download |
|---|---|---|---|
| v1.0.0 | 2026-08-30 | Initial release | [TimeTrack.exe](https://github.com/CodeCrafterX9/Time-Tracker-Application/releases/download/v1.0.0/DailyPlanner-v1.0.0.exe) |

See the full [Releases page](https://github.com/CodeCrafterX9/Time-Tracker-Application/releases) for release notes and older builds.

---

## ✨ Features

### ⏱ Focus Timer
- **Stopwatch** mode for open-ended work sessions
- **Pomodoro** mode with configurable work/break lengths and auto-cycling
- Tag each session with one or more custom tags (Deep Work, Low Energy, etc.)
- Every completed session is logged automatically

### 📝 Tasks
- Create, edit, and delete tasks with a title, description, and **multiple labels**
- Break a task into **sub-tasks**, each with its own done/pending checkbox
- Task titles are shared with the Timer, so you can time-track against real tasks
- See time spent per task, live, without leaving the list

### 🗓 Calendar
- A month-view diary, color-coded by how many hours you tracked each day
- Click any day to see that day's logged sessions
- **Schedule tasks for a specific day and time** — e.g. "Interview, Tuesday 2:00 PM" — right from the calendar with one click
- Days with upcoming scheduled tasks are marked with a 📌 pin

### 🔍 Review & Plan
- Pick any date range (Today / This Week / Last 7 Days / Last 30 Days / This Month / All Time, or a custom range)
- See what got **completed** in that range, what's still **pending**, and what's **overdue**
- Time-tracked-per-day chart and a completion-rate stat for quick decision-making

### 📜 History
- Full log of every timed session
- Filter by date, and assign or edit tags after the fact

### 📊 Analytics
- Hours by task, daily trend, and time-by-tag charts (matplotlib)
- Stat cards: total tracked time, sessions logged, average session length, most-tracked task, best day
- A plain-language insight line calling out gaps or imbalances

### 🗒 Notes
- A simple scratchpad for reminders, ideas, or anything you want to look back on later
- Stored permanently, searchable by browsing the list

## 🚀 Getting Started

### Option 1 — Run from source (recommended)

**Requirements:**
- Python 3.9+
- `tkinter` (ships with most Python installs; on Linux you may need `sudo apt install python3-tk`)
- `matplotlib`

```bash
git clone https://github.com/CodeCrafterX9/Time-Tracker-Application.git
cd Time-Tracker-Application
pip install matplotlib
python final_code.py
```

### Option 2 — Download a pre-built release (no Python needed)

See the [📦 Download](#-download) section above — grab the `.exe` and run it directly.

---

## 💾 Where your data is stored

All data is saved as plain CSV/JSON files in a dedicated folder in your **user home directory**, so it stays put no matter how the app is launched or packaged or updated:

```
Windows:  C:\Users\<you>\TimeTrackerData\
macOS:    /Users/<you>/TimeTrackerData/
Linux:    /home/<you>/TimeTrackerData/
```

Inside you'll find:

| File | Contains |
|---|---|
| `time_log.csv` | Every timed Timer session |
| `tasks.csv` | All tasks, sub-tasks, labels, and due dates |
| `notes.csv` | Everything saved on the Notes page |
| `app_config.json` | Your saved task/tag/label lists |

You can back these up, sync them, or open them directly in Excel/Google Sheets — they're just CSVs.

---

## 🛠 Building a custom standalone executable
Simply double-click `build_app.bat` to automatically build a versioned standalone Windows `.exe` using PyInstaller.

---

## 🧭 Roadmap ideas

- [ ] Export reports to PDF/Excel
- [ ] Recurring tasks
- [ ] Desktop notifications for scheduled tasks
- [ ] Dark mode
- [ ] Integration with existing Project Management Applications like JIRA etc. 

Contributions and suggestions welcome — open an issue or a PR.
