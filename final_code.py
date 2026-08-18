"""
Time Tracker App v4
--------------------
A multi-screen tkinter desktop app:

  Screens (left sidebar navigation):
    - Timer         : Stopwatch / Pomodoro, task dropdown, multi-tag picker
    - Tasks         : Full to-do / task tracker - create, edit, delete tasks with
                       a description and multiple labels; shows time spent per task
    - Calendar      : Diary/calendar view - a month grid colored by hours tracked
                       each day, click a day to see that day's sessions
    - Review & Plan : Pick any date range and see what got done (completed tasks +
                       time tracked) vs. what's still pending/overdue, for planning
    - History       : Every logged session, filter by date, assign/edit tags later
    - Analytics     : Real charts (matplotlib) - time per task, daily trend, tag split
                       plus stat cards for quick insight

Data files (created automatically next to this script):
    time_log.csv    -> every timed session (the time "memory")
    tasks.csv       -> every task: title, description, labels, status, dates
    app_config.json -> saved task list, tag list, and label list (dropdowns grow with use)

Run with:  python time_tracker.py
Requires:  tkinter (ships with standard Python), matplotlib
           pip install matplotlib   (if not already installed)
"""

import csv
import json
import os
import uuid
import calendar as _calendar_module
from datetime import datetime, timedelta
from collections import defaultdict

import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(APP_DIR, "time_log.csv")
TASKS_CSV_PATH = os.path.join(APP_DIR, "tasks.csv")
NOTES_CSV_PATH = os.path.join(APP_DIR, "notes.csv")
CONFIG_PATH = os.path.join(APP_DIR, "app_config.json")

CSV_HEADERS = ["ID", "Date", "Task", "Mode", "Start Time", "End Time",
               "Duration (HH:MM:SS)", "Duration (seconds)", "Tags"]

TASKS_HEADERS = ["ID", "Title", "Description", "Subtasks", "Labels", "Status",
                  "Created Date", "Due Date", "Due Time", "Completed Date"]
TASK_STATUSES = ["Pending", "In Progress", "Completed"]

NOTES_HEADERS = ["ID", "Date", "Time", "Note"]

DEFAULT_TASKS = ["Morning Study", "Afternoon Study", "Night Study",
                  "Work", "Reading", "Exercise", "Admin / Errands"]
DEFAULT_TAGS = ["Deep Work", "Revision", "Low Energy", "High Focus",
                "Interrupted", "Practice", "Theory"]
DEFAULT_LABELS = ["Urgent", "Personal", "Study", "Work",
                   "High Priority", "Low Priority"]

# ---------------------------------------------------------------------------
# Color palette (used throughout the UI)
# ---------------------------------------------------------------------------
COLORS = {
    "sidebar": "#1e2233",
    "sidebar_active": "#4f5bd5",
    "sidebar_text": "#c7cbe0",
    "sidebar_text_active": "#ffffff",
    "bg": "#f5f6fb",
    "card": "#ffffff",
    "accent": "#4f5bd5",
    "accent_soft": "#e7e9fb",
    "text": "#1f2333",
    "text_muted": "#6b7080",
    "success": "#22a06b",
    "warning": "#e0872c",
    "border": "#e4e6ef",
    "chip_bg": "#eef0fc",
    "chip_text": "#4f5bd5",
}

CHART_PALETTE = ["#4f5bd5", "#22a06b", "#e0872c", "#d64550", "#2ca9e1",
                  "#8e6fce", "#e0b93c", "#37b7a3", "#c95bb0", "#6b7080"]

FONT_FAMILY = "Segoe UI"


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def ensure_csv():
    """
    Create the CSV if missing. If it already exists but was written by an
    older version of this app (missing ID / Tags columns, different column
    order, etc.), migrate it in place to the current schema so nothing is
    lost and the app doesn't crash on old data.
    """
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_HEADERS)
        return

    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing_fieldnames = reader.fieldnames or []
        old_rows = list(reader)

    if existing_fieldnames == CSV_HEADERS:
        return  # already current schema, nothing to do

    migrated_rows = []
    for row in old_rows:
        migrated_rows.append({
            "ID": row.get("ID") or uuid.uuid4().hex[:10],
            "Date": row.get("Date", ""),
            "Task": row.get("Task", ""),
            "Mode": row.get("Mode", ""),
            "Start Time": row.get("Start Time", ""),
            "End Time": row.get("End Time", ""),
            "Duration (HH:MM:SS)": row.get("Duration (HH:MM:SS)", "00:00:00"),
            "Duration (seconds)": row.get("Duration (seconds)", "0"),
            "Tags": row.get("Tags", ""),
        })

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in migrated_rows:
            writer.writerow(row)


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("tasks", list(DEFAULT_TASKS))
                data.setdefault("tags", list(DEFAULT_TAGS))
                data.setdefault("labels", list(DEFAULT_LABELS))
                return data
        except Exception:
            pass
    return {"tasks": list(DEFAULT_TASKS), "tags": list(DEFAULT_TAGS),
            "labels": list(DEFAULT_LABELS)}


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def format_hms(total_seconds) -> str:
    total_seconds = int(total_seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def truncate_text(text, max_len=45):
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 1].rstrip() + "…"


def log_session(task, mode, start_dt, end_dt, duration_seconds, tags):
    ensure_csv()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            uuid.uuid4().hex[:10],
            start_dt.strftime("%Y-%m-%d"),
            task,
            mode,
            start_dt.strftime("%H:%M:%S"),
            end_dt.strftime("%H:%M:%S"),
            format_hms(duration_seconds),
            int(duration_seconds),
            ";".join(tags),
        ])


def load_all_rows():
    ensure_csv()
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def row_duration_seconds(row):
    """
    Safely get a row's duration in seconds. Falls back to parsing the
    HH:MM:SS column if the seconds column is missing or malformed, so a
    stray/old row can never crash the app.
    """
    val = row.get("Duration (seconds)")
    try:
        return int(val)
    except (TypeError, ValueError):
        pass
    hms = row.get("Duration (HH:MM:SS)", "")
    try:
        h, m, s = hms.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return 0


def rewrite_all_rows(rows):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# Tasks (To-Do) persistence -- separate CSV file: tasks.csv
# ---------------------------------------------------------------------------
def ensure_tasks_csv():
    if not os.path.exists(TASKS_CSV_PATH):
        with open(TASKS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(TASKS_HEADERS)
        return
    with open(TASKS_CSV_PATH, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing_fieldnames = reader.fieldnames or []
        old_rows = list(reader)
    if existing_fieldnames == TASKS_HEADERS:
        return
    migrated = []
    for row in old_rows:
        migrated.append({h: row.get(h, "") for h in TASKS_HEADERS})
    with open(TASKS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TASKS_HEADERS)
        writer.writeheader()
        for row in migrated:
            writer.writerow(row)


def load_all_tasks():
    ensure_tasks_csv()
    with open(TASKS_CSV_PATH, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rewrite_all_tasks(rows):
    with open(TASKS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TASKS_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def encode_subtasks(subtasks):
    """subtasks: list of (text, done) tuples -> stored string like '1|Text;0|Other'."""
    parts = []
    for text, done in subtasks:
        safe_text = str(text).replace("|", "/").replace(";", ",").strip()
        if not safe_text:
            continue
        parts.append(f"{'1' if done else '0'}|{safe_text}")
    return ";".join(parts)


def decode_subtasks(raw):
    """Reverse of encode_subtasks. Also reads older plain-text subtask lists
    (no status prefix) as not-done, for backward compatibility."""
    if not raw:
        return []
    items = []
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        if "|" in part:
            status, text = part.split("|", 1)
            done = status == "1"
        else:
            text, done = part, False
        items.append((text, done))
    return items


def create_task(title, description, subtasks, labels, status, due_date, due_time=""):
    ensure_tasks_csv()
    rows = load_all_tasks()
    today = datetime.now().strftime("%Y-%m-%d")
    rows.append({
        "ID": uuid.uuid4().hex[:10],
        "Title": title,
        "Description": description,
        "Subtasks": encode_subtasks(subtasks),
        "Labels": ";".join(labels),
        "Status": status,
        "Created Date": today,
        "Due Date": due_date,
        "Due Time": due_time,
        "Completed Date": today if status == "Completed" else "",
    })
    rewrite_all_tasks(rows)


def update_task(task_id, title, description, subtasks, labels, status, due_date, due_time=""):
    rows = load_all_tasks()
    for r in rows:
        if r["ID"] == task_id:
            was_completed = r.get("Status") == "Completed"
            r["Title"] = title
            r["Description"] = description
            r["Subtasks"] = encode_subtasks(subtasks)
            r["Labels"] = ";".join(labels)
            r["Status"] = status
            r["Due Date"] = due_date
            r["Due Time"] = due_time
            if status == "Completed" and not was_completed:
                r["Completed Date"] = datetime.now().strftime("%Y-%m-%d")
            elif status != "Completed":
                r["Completed Date"] = ""
            break
    rewrite_all_tasks(rows)


def set_task_subtasks(task_id, subtasks):
    """Update just a task's subtask checklist (used for quick toggling in the details panel)."""
    rows = load_all_tasks()
    for r in rows:
        if r["ID"] == task_id:
            r["Subtasks"] = encode_subtasks(subtasks)
            break
    rewrite_all_tasks(rows)


def delete_task(task_id):
    rows = load_all_tasks()
    rows = [r for r in rows if r["ID"] != task_id]
    rewrite_all_tasks(rows)


def task_time_spent_map():
    """Returns {task_title: total_seconds} by matching Task names in time_log.csv."""
    totals = defaultdict(int)
    for r in load_all_rows():
        totals[r.get("Task", "")] += row_duration_seconds(r)
    return totals


def format_due(task):
    """Combine Due Date + Due Time into one display string, e.g. '2026-08-19 · 2:00 PM'."""
    due_date = task.get("Due Date", "")
    due_time = task.get("Due Time", "")
    if not due_date:
        return ""
    if due_time:
        return f"{due_date}  {due_time}"
    return due_date


def get_task_title_options(app):
    """Merged list of quick-list tasks + every task title ever created, for dropdowns."""
    quick_list = list(app.config["tasks"])
    task_titles = [t["Title"] for t in load_all_tasks() if t.get("Title")]
    return quick_list + [t for t in task_titles if t not in quick_list]


# ---------------------------------------------------------------------------
# Notes persistence -- separate CSV file: notes.csv (a simple mental-notes log)
# ---------------------------------------------------------------------------
def ensure_notes_csv():
    if not os.path.exists(NOTES_CSV_PATH):
        with open(NOTES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(NOTES_HEADERS)
        return
    with open(NOTES_CSV_PATH, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing_fieldnames = reader.fieldnames or []
        old_rows = list(reader)
    if existing_fieldnames == NOTES_HEADERS:
        return
    migrated = [{h: row.get(h, "") for h in NOTES_HEADERS} for row in old_rows]
    with open(NOTES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=NOTES_HEADERS)
        writer.writeheader()
        for row in migrated:
            writer.writerow(row)


def load_all_notes():
    ensure_notes_csv()
    with open(NOTES_CSV_PATH, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rewrite_all_notes(rows):
    with open(NOTES_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=NOTES_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def add_note(text):
    ensure_notes_csv()
    rows = load_all_notes()
    now = datetime.now()
    rows.append({
        "ID": uuid.uuid4().hex[:10],
        "Date": now.strftime("%Y-%m-%d"),
        "Time": now.strftime("%H:%M:%S"),
        "Note": text,
    })
    rewrite_all_notes(rows)


def delete_note(note_id):
    rows = load_all_notes()
    rows = [r for r in rows if r["ID"] != note_id]
    rewrite_all_notes(rows)


# ---------------------------------------------------------------------------
# Small reusable widget: a wrapping "chip" tag picker
# ---------------------------------------------------------------------------
class TagPicker(ttk.Frame):
    """
    Lets the user pick multiple tags for a session.
    - Shows known tags as clickable chip buttons (toggle selected/unselected)
    - Has a small entry to type + add a brand-new tag on the fly
    - self.get_selected() returns the list of chosen tags
    """

    def __init__(self, parent, known_tags_getter, on_new_tag=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.known_tags_getter = known_tags_getter
        self.on_new_tag = on_new_tag
        self.selected = set()
        self.chip_buttons = {}

        self.chips_frame = ttk.Frame(self)
        self.chips_frame.pack(fill="x", pady=(2, 6))

        add_row = ttk.Frame(self)
        add_row.pack(fill="x")
        self.new_tag_entry = ttk.Entry(add_row, width=18)
        self.new_tag_entry.pack(side="left", padx=(0, 6))
        self.new_tag_entry.bind("<Return>", lambda e: self._add_new_tag())
        ttk.Button(add_row, text="+ Add tag", command=self._add_new_tag).pack(side="left")

        self.refresh_chips()

    def refresh_chips(self):
        for w in self.chips_frame.winfo_children():
            w.destroy()
        self.chip_buttons = {}

        tags = self.known_tags_getter()
        row = ttk.Frame(self.chips_frame)
        row.pack(fill="x")
        col_count = 0
        max_per_row = 4
        current_row = row
        for tag in tags:
            if col_count == max_per_row:
                current_row = ttk.Frame(self.chips_frame)
                current_row.pack(fill="x", pady=2)
                col_count = 0
            is_selected = tag in self.selected
            btn = tk.Button(
                current_row, text=tag,
                relief="flat", bd=0, padx=10, pady=4,
                font=(FONT_FAMILY, 9),
                bg=COLORS["accent"] if is_selected else COLORS["chip_bg"],
                fg="#ffffff" if is_selected else COLORS["chip_text"],
                activebackground=COLORS["accent"],
                cursor="hand2",
                command=lambda t=tag: self._toggle(t),
            )
            btn.pack(side="left", padx=3)
            self.chip_buttons[tag] = btn
            col_count += 1

    def _toggle(self, tag):
        if tag in self.selected:
            self.selected.remove(tag)
        else:
            self.selected.add(tag)
        self.refresh_chips()

    def _add_new_tag(self):
        new_tag = self.new_tag_entry.get().strip()
        if not new_tag:
            return
        self.selected.add(new_tag)
        if self.on_new_tag:
            self.on_new_tag(new_tag)
        self.new_tag_entry.delete(0, tk.END)
        self.refresh_chips()

    def set_selected(self, tags):
        self.selected = set(tags)
        self.refresh_chips()

    def get_selected(self):
        return sorted(self.selected)

    def clear(self):
        self.selected = set()
        self.refresh_chips()


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
class Sidebar(ttk.Frame):
    def __init__(self, parent, nav_items, on_select):
        super().__init__(parent, style="Sidebar.TFrame", width=170)
        self.pack_propagate(False)
        self.on_select = on_select
        self.buttons = {}

        title = tk.Label(self, text="⏱  TimeTrack", bg=COLORS["sidebar"],
                          fg="#ffffff", font=(FONT_FAMILY, 14, "bold"))
        title.pack(pady=(24, 30), padx=16, anchor="w")

        for key, label in nav_items:
            btn = tk.Label(self, text=label, bg=COLORS["sidebar"],
                            fg=COLORS["sidebar_text"], font=(FONT_FAMILY, 11),
                            anchor="w", padx=18, pady=10, cursor="hand2")
            btn.pack(fill="x")
            btn.bind("<Button-1>", lambda e, k=key: self.on_select(k))
            self.buttons[key] = btn

    def set_active(self, key):
        for k, btn in self.buttons.items():
            if k == key:
                btn.config(bg=COLORS["sidebar_active"], fg=COLORS["sidebar_text_active"])
            else:
                btn.config(bg=COLORS["sidebar"], fg=COLORS["sidebar_text"])


# ---------------------------------------------------------------------------
# Timer Page
# ---------------------------------------------------------------------------
class TimerPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Content.TFrame")
        self.app = app

        self.mode = tk.StringVar(value="Stopwatch")
        self.running = False
        self.paused = False
        self.session_start_dt = None
        self.elapsed_seconds = 0
        self._after_id = None
        self.pomo_phase = "Work"
        self.pomo_remaining = 0

        self._build()

    def _task_options(self):
        quick_list = list(self.app.config["tasks"])
        task_titles = [t["Title"] for t in load_all_tasks() if t.get("Title")]
        merged = quick_list + [t for t in task_titles if t not in quick_list]
        return merged

    def refresh_task_options(self):
        current = self.task_combo.get()
        self.task_combo["values"] = self._task_options()
        self.task_combo.set(current)

    def _build(self):
        header = tk.Label(self, text="Focus Timer", bg=COLORS["bg"],
                           fg=COLORS["text"], font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=28, pady=(24, 4))
        sub = tk.Label(self, text="Track a stopwatch session or run a Pomodoro cycle.",
                        bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, 10))
        sub.pack(anchor="w", padx=28, pady=(0, 16))

        card = tk.Frame(self, bg=COLORS["card"], highlightbackground=COLORS["border"],
                         highlightthickness=1)
        card.pack(fill="x", padx=28, pady=6)

        # Task row
        row1 = tk.Frame(card, bg=COLORS["card"])
        row1.pack(fill="x", padx=20, pady=(20, 8))
        tk.Label(row1, text="Task", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 10, "bold")).pack(anchor="w")
        self.task_combo = ttk.Combobox(row1, values=self._task_options(),
                                        font=(FONT_FAMILY, 11))
        self.task_combo.pack(fill="x", pady=(4, 0))
        self.task_combo.set(self.app.config["tasks"][0] if self.app.config["tasks"] else "")

        # Tags row
        row2 = tk.Frame(card, bg=COLORS["card"])
        row2.pack(fill="x", padx=20, pady=(14, 8))
        tk.Label(row2, text="Tags (optional, pick any that apply)", bg=COLORS["card"],
                  fg=COLORS["text"], font=(FONT_FAMILY, 10, "bold")).pack(anchor="w")
        self.tag_picker = TagPicker(row2, known_tags_getter=lambda: self.app.config["tags"],
                                     on_new_tag=self.app.add_known_tag)
        self.tag_picker.configure(style="Content.TFrame")
        self.tag_picker.pack(fill="x", pady=(4, 0))

        # Mode row
        row3 = tk.Frame(card, bg=COLORS["card"])
        row3.pack(fill="x", padx=20, pady=(10, 4))
        tk.Label(row3, text="Mode", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 10, "bold")).pack(anchor="w")
        mode_row = tk.Frame(row3, bg=COLORS["card"])
        mode_row.pack(anchor="w", pady=(4, 0))
        ttk.Radiobutton(mode_row, text="Stopwatch", variable=self.mode,
                         value="Stopwatch", command=self._on_mode_change).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(mode_row, text="Pomodoro", variable=self.mode,
                         value="Pomodoro", command=self._on_mode_change).pack(side="left")

        # Pomodoro settings
        self.pomo_frame = tk.Frame(card, bg=COLORS["card"])
        tk.Label(self.pomo_frame, text="Work (min)", bg=COLORS["card"],
                  fg=COLORS["text_muted"], font=(FONT_FAMILY, 9)).grid(row=0, column=0, padx=(0, 4))
        self.work_min_var = tk.IntVar(value=25)
        ttk.Spinbox(self.pomo_frame, from_=1, to=180, width=5,
                    textvariable=self.work_min_var).grid(row=0, column=1, padx=(0, 16))
        tk.Label(self.pomo_frame, text="Break (min)", bg=COLORS["card"],
                  fg=COLORS["text_muted"], font=(FONT_FAMILY, 9)).grid(row=0, column=2, padx=(0, 4))
        self.break_min_var = tk.IntVar(value=5)
        ttk.Spinbox(self.pomo_frame, from_=1, to=60, width=5,
                    textvariable=self.break_min_var).grid(row=0, column=3)
        self.phase_label = tk.Label(self.pomo_frame, text="", bg=COLORS["card"],
                                     fg=COLORS["accent"], font=(FONT_FAMILY, 9, "bold"))
        self.phase_label.grid(row=0, column=4, padx=16)

        # Big timer display
        self.time_label = tk.Label(card, text="00:00:00", bg=COLORS["card"],
                                    fg=COLORS["accent"], font=("Consolas", 44, "bold"))
        self.time_label.pack(pady=(20, 10))

        # Controls
        controls = tk.Frame(card, bg=COLORS["card"])
        controls.pack(pady=(0, 22))
        self.start_btn = tk.Button(controls, text="▶  Start", command=self.start,
                                    bg=COLORS["accent"], fg="white", relief="flat",
                                    font=(FONT_FAMILY, 10, "bold"), padx=18, pady=8, cursor="hand2")
        self.start_btn.grid(row=0, column=0, padx=6)
        self.pause_btn = tk.Button(controls, text="⏸  Pause", command=self.pause,
                                    bg=COLORS["warning"], fg="white", relief="flat",
                                    font=(FONT_FAMILY, 10, "bold"), padx=18, pady=8,
                                    state="disabled", cursor="hand2")
        self.pause_btn.grid(row=0, column=1, padx=6)
        self.stop_btn = tk.Button(controls, text="■  Stop & Save", command=self.stop,
                                   bg=COLORS["success"], fg="white", relief="flat",
                                   font=(FONT_FAMILY, 10, "bold"), padx=18, pady=8,
                                   state="disabled", cursor="hand2")
        self.stop_btn.grid(row=0, column=2, padx=6)

        self._on_mode_change()

    def _on_mode_change(self):
        if self.mode.get() == "Pomodoro":
            self.pomo_frame.pack(fill="x", padx=20, pady=(4, 4))
            self.phase_label.config(text=f"Phase: {self.pomo_phase}")
        else:
            self.pomo_frame.pack_forget()
        if not self.running:
            if self.mode.get() == "Pomodoro":
                self.time_label.config(text=format_hms(self.work_min_var.get() * 60))
            else:
                self.time_label.config(text="00:00:00")

    def start(self):
        task = self.task_combo.get().strip()
        if not task:
            messagebox.showwarning("Task required", "Please choose or type a task before starting.")
            return
        self.app.add_known_task(task)

        if not self.running:
            self.session_start_dt = datetime.now()
            self.elapsed_seconds = 0
            if self.mode.get() == "Pomodoro":
                self.pomo_phase = "Work"
                self.pomo_remaining = self.work_min_var.get() * 60
                self.phase_label.config(text=f"Phase: {self.pomo_phase}")

        self.running = True
        self.paused = False
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text="⏸  Pause")
        self.stop_btn.config(state="normal")
        self.task_combo.config(state="disabled")
        self._tick()

    def pause(self):
        if not self.running:
            return
        if not self.paused:
            self.paused = True
            self.pause_btn.config(text="▶  Resume")
            if self._after_id:
                self.after_cancel(self._after_id)
        else:
            self.paused = False
            self.pause_btn.config(text="⏸  Pause")
            self._tick()

    def stop(self):
        if not self.running:
            return
        if self._after_id:
            self.after_cancel(self._after_id)
        self.running = False
        self.paused = False

        task = self.task_combo.get().strip() or "General"
        tags = self.tag_picker.get_selected()
        end_dt = datetime.now()

        if self.mode.get() == "Stopwatch":
            if self.elapsed_seconds > 0:
                log_session(task, "Stopwatch", self.session_start_dt, end_dt,
                            self.elapsed_seconds, tags)
        else:
            if self.elapsed_seconds > 0:
                log_session(task, f"Pomodoro-{self.pomo_phase}", self.session_start_dt,
                            end_dt, self.elapsed_seconds, tags)

        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="⏸  Pause")
        self.stop_btn.config(state="disabled")
        self.task_combo.config(state="normal")
        self.elapsed_seconds = 0
        self.tag_picker.clear()
        self._on_mode_change()
        self.app.refresh_all_data_views()

    def _tick(self):
        if not self.running or self.paused:
            return
        if self.mode.get() == "Stopwatch":
            self.elapsed_seconds += 1
            self.time_label.config(text=format_hms(self.elapsed_seconds))
        else:
            self.elapsed_seconds += 1
            self.pomo_remaining -= 1
            self.time_label.config(text=format_hms(max(self.pomo_remaining, 0)))
            if self.pomo_remaining <= 0:
                self._pomo_phase_complete()
                return
        self._after_id = self.after(1000, self._tick)

    def _pomo_phase_complete(self):
        task = self.task_combo.get().strip() or "General"
        tags = self.tag_picker.get_selected()
        end_dt = datetime.now()

        if self.pomo_phase == "Work":
            log_session(task, "Pomodoro-Work", self.session_start_dt, end_dt,
                        self.elapsed_seconds, tags)
            messagebox.showinfo("Work session done", "Nice work! Time for a break.")
            self.pomo_phase = "Break"
            self.pomo_remaining = self.break_min_var.get() * 60
        else:
            messagebox.showinfo("Break over", "Break's done. Ready for another work session?")
            self.pomo_phase = "Work"
            self.pomo_remaining = self.work_min_var.get() * 60

        self.phase_label.config(text=f"Phase: {self.pomo_phase}")
        self.session_start_dt = datetime.now()
        self.elapsed_seconds = 0
        self.app.refresh_all_data_views()
        self._after_id = self.after(1000, self._tick)


# ---------------------------------------------------------------------------
# History Page (view sessions + assign / edit tags later)
# ---------------------------------------------------------------------------
class HistoryPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Content.TFrame")
        self.app = app
        self._build()

    def _build(self):
        header = tk.Label(self, text="Session History", bg=COLORS["bg"],
                           fg=COLORS["text"], font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=28, pady=(24, 4))
        sub = tk.Label(self, text="Browse past sessions and assign tags whenever you get time.",
                        bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, 10))
        sub.pack(anchor="w", padx=28, pady=(0, 14))

        filter_row = tk.Frame(self, bg=COLORS["bg"])
        filter_row.pack(fill="x", padx=28, pady=(0, 10))
        tk.Label(filter_row, text="Filter by date (YYYY-MM-DD, blank = all):",
                  bg=COLORS["bg"], fg=COLORS["text"], font=(FONT_FAMILY, 9)).pack(side="left")
        self.date_filter = ttk.Entry(filter_row, width=14)
        self.date_filter.pack(side="left", padx=8)
        tk.Button(filter_row, text="Apply", command=self.refresh, bg=COLORS["accent"],
                  fg="white", relief="flat", padx=10, pady=3, cursor="hand2").pack(side="left")
        tk.Button(filter_row, text="Clear", command=self._clear_filter, bg=COLORS["border"],
                  fg=COLORS["text"], relief="flat", padx=10, pady=3, cursor="hand2").pack(side="left", padx=6)
        tk.Button(filter_row, text="Edit Tags for Selected", command=self._edit_tags,
                  bg=COLORS["success"], fg="white", relief="flat", padx=10, pady=3,
                  cursor="hand2").pack(side="right")

        table_card = tk.Frame(self, bg=COLORS["card"], highlightbackground=COLORS["border"],
                               highlightthickness=1)
        table_card.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        cols = ("date", "task", "mode", "start", "end", "duration", "tags")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", height=14)
        headings = {"date": "Date", "task": "Task", "mode": "Mode", "start": "Start",
                    "end": "End", "duration": "Duration", "tags": "Tags"}
        widths = {"date": 90, "task": 140, "mode": 110, "start": 70, "end": 70,
                  "duration": 80, "tags": 180}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10, side="left")

        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        self._row_id_map = {}

    def _clear_filter(self):
        self.date_filter.delete(0, tk.END)
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._row_id_map = {}

        rows = load_all_rows()
        date_filter = self.date_filter.get().strip()
        rows.sort(key=lambda r: (r["Date"], r["Start Time"]), reverse=True)

        for r in rows:
            if date_filter and r["Date"] != date_filter:
                continue
            item = self.tree.insert("", "end", values=(
                r["Date"], r["Task"], r["Mode"], r["Start Time"], r["End Time"],
                r["Duration (HH:MM:SS)"], r.get("Tags", "").replace(";", ", ")
            ))
            self._row_id_map[item] = r["ID"]

    def _edit_tags(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Select a session", "Select one session in the table first.")
            return
        item = selection[0]
        row_id = self._row_id_map.get(item)
        rows = load_all_rows()
        target = next((r for r in rows if r["ID"] == row_id), None)
        if target is None:
            return

        dialog = tk.Toplevel(self)
        dialog.title(f"Edit tags — {target['Task']} ({target['Date']})")
        dialog.configure(bg=COLORS["card"])
        dialog.geometry("360x220")

        tk.Label(dialog, text=f"{target['Task']}  ·  {target['Date']}  ·  {target['Duration (HH:MM:SS)']}",
                  bg=COLORS["card"], fg=COLORS["text"], font=(FONT_FAMILY, 10, "bold")).pack(
            anchor="w", padx=16, pady=(16, 8))

        picker_wrapper = tk.Frame(dialog, bg=COLORS["card"])
        picker_wrapper.pack(fill="both", expand=True, padx=16)
        picker = TagPicker(picker_wrapper, known_tags_getter=lambda: self.app.config["tags"],
                            on_new_tag=self.app.add_known_tag)
        picker.pack(fill="x")
        existing_tags = [t for t in target.get("Tags", "").split(";") if t]
        picker.set_selected(existing_tags)

        def save_and_close():
            new_tags = picker.get_selected()
            for r in rows:
                if r["ID"] == row_id:
                    r["Tags"] = ";".join(new_tags)
                    break
            rewrite_all_rows(rows)
            dialog.destroy()
            self.refresh()
            self.app.refresh_all_data_views()

        tk.Button(dialog, text="Save Tags", command=save_and_close, bg=COLORS["accent"],
                  fg="white", relief="flat", padx=14, pady=6, cursor="hand2").pack(pady=16)


# ---------------------------------------------------------------------------
# Notes Page (rough / scratch notes)
# ---------------------------------------------------------------------------
class NotesPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Content.TFrame")
        self.app = app
        self._row_id_map = {}
        self._build()

    def _build(self):
        header = tk.Label(
            self,
            text="Notes",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 20, "bold")
        )
        header.pack(anchor="w", padx=28, pady=(24, 4))

        sub = tk.Label(
            self,
            text="Quickly scribble ideas, reminders, rough work, or anything you don't want to forget.",
            bg=COLORS["bg"],
            fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 10)
        )
        sub.pack(anchor="w", padx=28, pady=(0, 14))

        # ---------------------------------------------------------------
        # Toolbar
        # ---------------------------------------------------------------
        toolbar = tk.Frame(self, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=28, pady=(0, 10))

        tk.Button(
            toolbar,
            text="+ New Note",
            command=self.new_note,
            bg=COLORS["accent"],
            fg="white",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            font=(FONT_FAMILY, 9, "bold")
        ).pack(side="left")

        tk.Button(
            toolbar,
            text="Save Note",
            command=self.save_note,
            bg=COLORS["success"],
            fg="white",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            font=(FONT_FAMILY, 9, "bold")
        ).pack(side="left", padx=8)

        tk.Button(
            toolbar,
            text="Delete Selected",
            command=self.delete_selected,
            bg=COLORS["card"],
            fg=COLORS["warning"],
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            highlightbackground=COLORS["border"],
            highlightthickness=1
        ).pack(side="left")

        tk.Button(
            toolbar,
            text="Edit Selected",
            command=self.edit_selected,
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            font=(FONT_FAMILY, 9, "bold")
        ).pack(side="left", padx=8)

        # ---------------------------------------------------------------
        # Main area
        # ---------------------------------------------------------------
        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        # ---------------------------------------------------------------
        # Left: notes list
        # ---------------------------------------------------------------
        list_card = tk.Frame(
            body,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            width=280
        )
        list_card.pack(side="left", fill="y")
        list_card.pack_propagate(False)

        tk.Label(
            list_card,
            text="Saved Notes",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 10, "bold")
        ).pack(anchor="w", padx=12, pady=(12, 8))

        self.notes_tree = ttk.Treeview(
            list_card,
            columns=("date", "time", "preview"),
            show="headings"
        )

        self.notes_tree.heading("date", text="Date")
        self.notes_tree.heading("time", text="Time")
        self.notes_tree.heading("preview", text="Note")

        self.notes_tree.column("date", width=82)
        self.notes_tree.column("time", width=65)
        self.notes_tree.column("preview", width=110)

        self.notes_tree.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=(0, 8)
        )

        self.notes_tree.bind(
            "<<TreeviewSelect>>",
            self._on_note_selected
        )

        # ---------------------------------------------------------------
        # Right: editor
        # ---------------------------------------------------------------
        editor_card = tk.Frame(
            body,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        editor_card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(14, 0)
        )

        tk.Label(
            editor_card,
            text="Scratch Pad",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 11, "bold")
        ).pack(anchor="w", padx=16, pady=(14, 6))

        self.note_info = tk.Label(
            editor_card,
            text="New note",
            bg=COLORS["card"],
            fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 9)
        )
        self.note_info.pack(anchor="w", padx=16, pady=(0, 8))

        text_wrap = tk.Frame(editor_card, bg=COLORS["card"])
        text_wrap.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(0, 16)
        )

        self.note_text = tk.Text(
            text_wrap,
            wrap="word",
            font=(FONT_FAMILY, 11),
            undo=True,
            relief="solid",
            bd=1,
            padx=10,
            pady=10
        )
        self.note_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            text_wrap,
            orient="vertical",
            command=self.note_text.yview
        )
        scrollbar.pack(side="right", fill="y")

        self.note_text.configure(
            yscrollcommand=scrollbar.set
        )

        self.current_note_id = None

        self.refresh()

    def refresh(self):
        """Reload notes from notes.csv."""
        for item in self.notes_tree.get_children():
            self.notes_tree.delete(item)

        self._row_id_map = {}

        notes = load_all_notes()

        # Newest first
        notes.sort(
            key=lambda r: (r.get("Date", ""), r.get("Time", "")),
            reverse=True
        )

        for note in notes:
            preview = truncate_text(
                note.get("Note", "").replace("\n", " "),
                max_len=45
            )

            item = self.notes_tree.insert(
                "",
                "end",
                values=(
                    note.get("Date", ""),
                    note.get("Time", ""),
                    preview
                )
            )

            self._row_id_map[item] = note.get("ID")

    def new_note(self):
        """Start a fresh note."""
        self.current_note_id = None
        self.note_text.delete("1.0", tk.END)
        self.note_info.config(text="New note")
        self.note_text.focus_set()

        self.notes_tree.selection_remove(
            self.notes_tree.selection()
        )

    def save_note(self):
        """Save the current editor contents."""
        text = self.note_text.get("1.0", "end-1c").strip()

        if not text:
            messagebox.showwarning(
                "Empty note",
                "Write something in the note first."
            )
            return

        # ---------------------------------------------------------------
        # New note
        # ---------------------------------------------------------------
        if self.current_note_id is None:
            add_note(text)

        # ---------------------------------------------------------------
        # Editing existing note
        # ---------------------------------------------------------------
        else:
            rows = load_all_notes()

            for row in rows:
                if row["ID"] == self.current_note_id:
                    row["Note"] = text
                    break

            rewrite_all_notes(rows)

        self.refresh()

        messagebox.showinfo(
            "Saved",
            "Your note has been saved."
        )

        # Keep editor open after saving
        self.note_info.config(
            text=f"Saved {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _on_note_selected(self, event=None):
        selection = self.notes_tree.selection()

        if not selection:
            return

        item = selection[0]
        note_id = self._row_id_map.get(item)

        if not note_id:
            return

        notes = load_all_notes()

        note = next(
            (n for n in notes if n["ID"] == note_id),
            None
        )

        if not note:
            return

        self.current_note_id = note_id

        self.note_text.delete("1.0", tk.END)
        self.note_text.insert(
            "1.0",
            note.get("Note", "")
        )

        self.note_info.config(
            text=f"{note.get('Date', '')}  {note.get('Time', '')}"
        )

    def delete_selected(self):
        """Delete the currently selected note."""
        selection = self.notes_tree.selection()

        if not selection:
            messagebox.showinfo(
                "Select a note",
                "Select a note from the list first."
            )
            return

        item = selection[0]
        note_id = self._row_id_map.get(item)

        if not note_id:
            return

        notes = load_all_notes()

        target = next(
            (n for n in notes if n["ID"] == note_id),
            None
        )

        if not target:
            return

        if not messagebox.askyesno(
            "Delete note",
            "Delete this note permanently?"
        ):
            return

        delete_note(note_id)

        self.current_note_id = None
        self.note_text.delete("1.0", tk.END)
        self.note_info.config(text="New note")

        self.refresh()

    def edit_selected(self):
        """Load the selected note into the editor for editing."""
        selection = self.notes_tree.selection()

        if not selection:
            messagebox.showinfo(
                "Select a note",
                "Please select a note from the list first."
            )
            return

        item = selection[0]
        note_id = self._row_id_map.get(item)

        if not note_id:
            return

        notes = load_all_notes()
        note = next(
            (n for n in notes if n["ID"] == note_id),
            None
        )

        if not note:
            return

        self.current_note_id = note_id

        self.note_text.delete("1.0", tk.END)
        self.note_text.insert("1.0", note.get("Note", ""))

        self.note_info.config(
            text=f"Editing note · {note.get('Date', '')} {note.get('Time', '')}"
        )

        self.note_text.focus_set()

# ---------------------------------------------------------------------------
# Task Add / Edit Dialog (used by TasksPage)
# ---------------------------------------------------------------------------
class TaskDialog(tk.Toplevel):
    def __init__(self, parent, app, on_saved, existing_task=None, prefill_date=None):
        super().__init__(parent)
        self.app = app
        self.on_saved = on_saved
        self.existing_task = existing_task
        self.subtasks = []  # list of [text, done] pairs

        self.title("Edit Task" if existing_task else "New Task")
        self.configure(bg=COLORS["card"])
        self.geometry("480x720")
        self.resizable(False, False)
        self.grab_set()

        pad = {"padx": 18, "pady": (10, 0)}

        tk.Label(self, text="Title (pick a task you've done before, or type a new one)",
                  bg=COLORS["card"], fg=COLORS["text"], font=(FONT_FAMILY, 10, "bold")).pack(
            anchor="w", **pad)
        self.title_entry = ttk.Combobox(self, values=get_task_title_options(app),
                                         font=(FONT_FAMILY, 11))
        self.title_entry.pack(fill="x", padx=18, pady=(4, 0))

        tk.Label(self, text="Description (optional)", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", **pad)
        self.desc_text = tk.Text(self, height=3, font=(FONT_FAMILY, 10), wrap="word",
                                  relief="solid", bd=1)
        self.desc_text.pack(fill="x", padx=18, pady=(4, 0))

        # ---- Subtasks / work log, each with a done/pending status ----
        tk.Label(self, text="Sub-tasks / what was worked on (check off as you finish each one)",
                  bg=COLORS["card"], fg=COLORS["text"], font=(FONT_FAMILY, 10, "bold")).pack(
            anchor="w", padx=18, pady=(10, 0))

        subtask_add_row = tk.Frame(self, bg=COLORS["card"])
        subtask_add_row.pack(fill="x", padx=18, pady=(4, 0))
        self.subtask_entry = ttk.Entry(subtask_add_row, font=(FONT_FAMILY, 10))
        self.subtask_entry.pack(side="left", fill="x", expand=True)
        self.subtask_entry.bind("<Return>", lambda e: self._add_subtask())
        tk.Button(subtask_add_row, text="+ Add", command=self._add_subtask,
                  bg=COLORS["accent"], fg="white", relief="flat", padx=10, pady=3,
                  cursor="hand2", font=(FONT_FAMILY, 9)).pack(side="left", padx=(6, 0))

        list_wrap = tk.Frame(self, bg=COLORS["card"])
        list_wrap.pack(fill="x", padx=18, pady=(6, 0))
        self.subtask_listbox = tk.Listbox(list_wrap, height=6, font=(FONT_FAMILY, 9),
                                           relief="solid", bd=1, activestyle="none",
                                           selectbackground=COLORS["accent"])
        self.subtask_listbox.pack(side="left", fill="x", expand=True)
        self.subtask_listbox.bind("<Double-1>", lambda e: self._toggle_subtask())
        sb_vsb = ttk.Scrollbar(list_wrap, orient="vertical", command=self.subtask_listbox.yview)
        sb_vsb.pack(side="left", fill="y")
        self.subtask_listbox.configure(yscrollcommand=sb_vsb.set)

        hint = tk.Label(self, text="Double-click a sub-task to mark it done / not done",
                         bg=COLORS["card"], fg=COLORS["text_muted"], font=(FONT_FAMILY, 8, "italic"))
        hint.pack(anchor="w", padx=18, pady=(2, 0))

        tk.Button(self, text="Remove Selected Sub-task", command=self._remove_subtask,
                  bg=COLORS["card"], fg=COLORS["warning"], relief="flat", padx=8, pady=2,
                  cursor="hand2", font=(FONT_FAMILY, 8),
                  highlightbackground=COLORS["border"], highlightthickness=1).pack(
            anchor="w", padx=18, pady=(4, 0))

        tk.Label(self, text="Labels", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", padx=18, pady=(12, 0))
        label_wrap = tk.Frame(self, bg=COLORS["card"])
        label_wrap.pack(fill="x", padx=18)
        self.label_picker = TagPicker(label_wrap, known_tags_getter=lambda: self.app.config["labels"],
                                       on_new_tag=self.app.add_known_label)
        self.label_picker.pack(fill="x")

        row = tk.Frame(self, bg=COLORS["card"])
        row.pack(fill="x", padx=18, pady=(10, 0))
        tk.Label(row, text="Status", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(row, text="Due date (YYYY-MM-DD)", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 10, "bold")).grid(row=0, column=1, sticky="w", padx=(20, 0))
        tk.Label(row, text="Due time (optional)", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 10, "bold")).grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.status_var = tk.StringVar(value="Pending")
        ttk.Combobox(row, textvariable=self.status_var, values=TASK_STATUSES,
                     state="readonly", width=13).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.due_entry = ttk.Entry(row, width=13)
        self.due_entry.grid(row=1, column=1, sticky="w", padx=(20, 0), pady=(4, 0))
        self.due_time_entry = ttk.Entry(row, width=10)
        self.due_time_entry.grid(row=1, column=2, sticky="w", padx=(20, 0), pady=(4, 0))
        tk.Label(self, text='e.g. "2:00 PM" or "14:00" — leave blank if it\'s just a day, not a specific slot',
                  bg=COLORS["card"], fg=COLORS["text_muted"], font=(FONT_FAMILY, 8, "italic")).pack(
            anchor="w", padx=18, pady=(2, 0))

        if existing_task:
            self.title_entry.set(existing_task.get("Title", ""))
            self.desc_text.insert("1.0", existing_task.get("Description", ""))
            for text, done in decode_subtasks(existing_task.get("Subtasks", "")):
                self.subtasks.append([text, done])
            self._render_subtask_listbox()
            labels = [l for l in existing_task.get("Labels", "").split(";") if l]
            self.label_picker.set_selected(labels)
            self.status_var.set(existing_task.get("Status") or "Pending")
            self.due_entry.insert(0, existing_task.get("Due Date", ""))
            self.due_time_entry.insert(0, existing_task.get("Due Time", ""))
        elif prefill_date:
            self.due_entry.insert(0, prefill_date)

        btn_row = tk.Frame(self, bg=COLORS["card"])
        btn_row.pack(fill="x", padx=18, pady=18, side="bottom")
        tk.Button(btn_row, text="Save Task", command=self._save, bg=COLORS["accent"],
                  fg="white", relief="flat", padx=16, pady=8, cursor="hand2").pack(side="left")
        tk.Button(btn_row, text="Cancel", command=self.destroy, bg=COLORS["border"],
                  fg=COLORS["text"], relief="flat", padx=16, pady=8, cursor="hand2").pack(side="left", padx=8)

    def _render_subtask_listbox(self):
        self.subtask_listbox.delete(0, tk.END)
        for text, done in self.subtasks:
            glyph = "☑" if done else "☐"
            self.subtask_listbox.insert("end", f"{glyph}  {text}")

    def _add_subtask(self):
        text = self.subtask_entry.get().strip()
        if not text:
            return
        self.subtasks.append([text, False])
        self._render_subtask_listbox()
        self.subtask_entry.delete(0, tk.END)

    def _remove_subtask(self):
        selection = self.subtask_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        del self.subtasks[idx]
        self._render_subtask_listbox()

    def _toggle_subtask(self):
        selection = self.subtask_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        self.subtasks[idx][1] = not self.subtasks[idx][1]
        self._render_subtask_listbox()
        self.subtask_listbox.selection_set(idx)

    def _save(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Title required", "Please give the task a title.")
            return
        description = self.desc_text.get("1.0", "end").strip()
        labels = self.label_picker.get_selected()
        status = self.status_var.get()
        due_date = self.due_entry.get().strip()
        due_time = self.due_time_entry.get().strip()
        subtasks = [(t, d) for t, d in self.subtasks]

        if self.existing_task:
            update_task(self.existing_task["ID"], title, description, subtasks,
                        labels, status, due_date, due_time)
        else:
            create_task(title, description, subtasks, labels, status, due_date, due_time)

        self.app.add_known_task(title)
        self.destroy()
        self.on_saved()


# ---------------------------------------------------------------------------
# Tasks Page (To-Do / Task Tracker: create, update, delete, label tasks)
# ---------------------------------------------------------------------------
class TasksPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Content.TFrame")
        self.app = app
        self.status_filter = tk.StringVar(value="All")
        self._row_id_map = {}
        self._build()

    def _build(self):
        header = tk.Label(self, text="Tasks", bg=COLORS["bg"], fg=COLORS["text"],
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=28, pady=(24, 4))
        sub = tk.Label(self, text="Create, update, and organize your tasks with labels and sub-tasks.",
                        bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, 10))
        sub.pack(anchor="w", padx=28, pady=(0, 14))

        toolbar = tk.Frame(self, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=28, pady=(0, 10))
        tk.Button(toolbar, text="+ New Task", command=self._new_task, bg=COLORS["accent"],
                  fg="white", relief="flat", padx=14, pady=6, cursor="hand2",
                  font=(FONT_FAMILY, 9, "bold")).pack(side="left")
        tk.Button(toolbar, text="Edit Selected", command=self._edit_selected, bg=COLORS["card"],
                  fg=COLORS["text"], relief="flat", padx=12, pady=6, cursor="hand2",
                  highlightbackground=COLORS["border"], highlightthickness=1).pack(side="left", padx=8)
        tk.Button(toolbar, text="Delete Selected", command=self._delete_selected, bg=COLORS["card"],
                  fg=COLORS["warning"], relief="flat", padx=12, pady=6, cursor="hand2",
                  highlightbackground=COLORS["border"], highlightthickness=1).pack(side="left")

        tk.Label(toolbar, text="Status:", bg=COLORS["bg"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 9)).pack(side="left", padx=(20, 4))
        status_combo = ttk.Combobox(toolbar, textvariable=self.status_filter, state="readonly",
                                     values=["All"] + TASK_STATUSES, width=12)
        status_combo.pack(side="left")
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # ---- main body: task list (left) + live details panel (right) ----
        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        table_card = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"],
                               highlightthickness=1)
        table_card.pack(side="left", fill="both", expand=True)

        cols = ("title", "subtasks", "labels", "status", "due", "time_spent")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", height=16)
        headings = {"title": "Title", "subtasks": "Sub-tasks (preview)", "labels": "Labels",
                    "status": "Status", "due": "Due", "time_spent": "Time Spent"}
        widths = {"title": 150, "subtasks": 200, "labels": 110, "status": 90,
                  "due": 130, "time_spent": 90}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10, side="left")
        self.tree.bind("<Double-1>", lambda e: self._edit_selected())
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        # ---- details panel: click a task, see everything without opening it ----
        detail_card = tk.Frame(body, bg=COLORS["card"], highlightbackground=COLORS["border"],
                                highlightthickness=1, width=300)
        detail_card.pack(side="left", fill="y", padx=(14, 0))
        detail_card.pack_propagate(False)

        self.detail_title = tk.Label(detail_card, text="Select a task to preview it here",
                                      bg=COLORS["card"], fg=COLORS["text"],
                                      font=(FONT_FAMILY, 12, "bold"), wraplength=270, justify="left")
        self.detail_title.pack(anchor="w", padx=14, pady=(14, 2))

        self.detail_meta = tk.Label(detail_card, text="", bg=COLORS["card"], fg=COLORS["text_muted"],
                                     font=(FONT_FAMILY, 9), wraplength=270, justify="left")
        self.detail_meta.pack(anchor="w", padx=14, pady=(0, 8))

        tk.Label(detail_card, text="Description", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", padx=14)
        self.detail_desc = tk.Label(detail_card, text="—", bg=COLORS["card"], fg=COLORS["text"],
                                     font=(FONT_FAMILY, 9), wraplength=270, justify="left")
        self.detail_desc.pack(anchor="w", padx=14, pady=(2, 10))

        tk.Label(detail_card, text="Sub-tasks", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", padx=14)
        self.detail_subtasks = tk.Label(detail_card, text="—", bg=COLORS["card"], fg=COLORS["text"],
                                         font=(FONT_FAMILY, 9), wraplength=270, justify="left")
        self.detail_subtasks.pack(anchor="w", padx=14, pady=(2, 10))

        self.detail_time = tk.Label(detail_card, text="", bg=COLORS["card"], fg=COLORS["accent"],
                                     font=(FONT_FAMILY, 10, "bold"))
        self.detail_time.pack(anchor="w", padx=14, pady=(6, 14), side="bottom")

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._row_id_map = {}

        tasks = load_all_tasks()
        time_map = task_time_spent_map()
        status_filter = self.status_filter.get()

        for t in tasks:
            if status_filter != "All" and t.get("Status") != status_filter:
                continue
            labels = t.get("Labels", "").replace(";", ", ")
            subtasks_list = [s for s in t.get("Subtasks", "").split(";") if s]
            subtasks_preview = truncate_text(" • ".join(subtasks_list)) if subtasks_list else (
                truncate_text(t.get("Description", "")) if t.get("Description") else "—")
            spent = format_hms(time_map.get(t.get("Title", ""), 0))
            item = self.tree.insert("", "end", values=(
                t.get("Title", ""), subtasks_preview, labels, t.get("Status", ""),
                format_due(t), spent
            ))
            self._row_id_map[item] = t["ID"]

        # keep detail panel in sync if nothing's selected anymore
        if not self.tree.selection():
            self._clear_detail()

    def _on_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            self._clear_detail()
            return
        task_id = self._row_id_map.get(selection[0])
        tasks = load_all_tasks()
        task = next((t for t in tasks if t["ID"] == task_id), None)
        if not task:
            self._clear_detail()
            return

        time_map = task_time_spent_map()
        self.detail_title.config(text=task.get("Title", ""))
        meta_bits = [task.get("Status", "")]
        if task.get("Due Date"):
            meta_bits.append(f"Due {format_due(task)}")
        labels = task.get("Labels", "").replace(";", ", ")
        if labels:
            meta_bits.append(labels)
        self.detail_meta.config(text="  ·  ".join(meta_bits))

        self.detail_desc.config(text=task.get("Description", "").strip() or "—")

        subtasks_list = [s for s in task.get("Subtasks", "").split(";") if s]
        if subtasks_list:
            self.detail_subtasks.config(text="\n".join(f"• {s}" for s in subtasks_list))
        else:
            self.detail_subtasks.config(text="—")

        spent = format_hms(time_map.get(task.get("Title", ""), 0))
        self.detail_time.config(text=f"Time spent: {spent}")

    def _clear_detail(self):
        self.detail_title.config(text="Select a task to preview it here")
        self.detail_meta.config(text="")
        self.detail_desc.config(text="—")
        self.detail_subtasks.config(text="—")
        self.detail_time.config(text="")

    def _new_task(self):
        TaskDialog(self, self.app, on_saved=self._on_task_saved)

    def _get_selected_task(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Select a task", "Select a task in the table first.")
            return None
        task_id = self._row_id_map.get(selection[0])
        tasks = load_all_tasks()
        return next((t for t in tasks if t["ID"] == task_id), None)

    def _edit_selected(self):
        task = self._get_selected_task()
        if task:
            TaskDialog(self, self.app, on_saved=self._on_task_saved, existing_task=task)

    def _delete_selected(self):
        task = self._get_selected_task()
        if not task:
            return
        if messagebox.askyesno("Delete task", f"Delete task '{task['Title']}'? This won't remove any time already logged for it."):
            delete_task(task["ID"])
            self._on_task_saved()

    def _on_task_saved(self):
        self.refresh()
        self.app.refresh_all_data_views()


# ---------------------------------------------------------------------------
# Calendar Page (diary view: how much time was spent, day by day)
# ---------------------------------------------------------------------------
class CalendarPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Content.TFrame")
        self.app = app
        today = datetime.now()
        self.year = today.year
        self.month = today.month
        self.selected_date = today.strftime("%Y-%m-%d")
        self._build()

    def _build(self):
        header = tk.Label(self, text="Calendar", bg=COLORS["bg"], fg=COLORS["text"],
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=28, pady=(24, 4))
        sub = tk.Label(self, text="Your day-by-day diary of tracked time.",
                        bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, 10))
        sub.pack(anchor="w", padx=28, pady=(0, 14))

        nav = tk.Frame(self, bg=COLORS["bg"])
        nav.pack(fill="x", padx=28)
        tk.Button(nav, text="◀", command=self._prev_month, bg=COLORS["card"], fg=COLORS["text"],
                  relief="flat", padx=10, pady=4, cursor="hand2").pack(side="left")
        self.month_label = tk.Label(nav, text="", bg=COLORS["bg"], fg=COLORS["text"],
                                     font=(FONT_FAMILY, 13, "bold"))
        self.month_label.pack(side="left", padx=14)
        tk.Button(nav, text="▶", command=self._next_month, bg=COLORS["card"], fg=COLORS["text"],
                  relief="flat", padx=10, pady=4, cursor="hand2").pack(side="left")

        main = tk.Frame(self, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=28, pady=14)

        self.grid_frame = tk.Frame(main, bg=COLORS["bg"])
        self.grid_frame.pack(side="left", fill="both", expand=True)

        detail_card = tk.Frame(main, bg=COLORS["card"], highlightbackground=COLORS["border"],
                                highlightthickness=1, width=320)
        detail_card.pack(side="left", fill="y", padx=(14, 0))
        detail_card.pack_propagate(False)

        self.detail_title = tk.Label(detail_card, text="", bg=COLORS["card"], fg=COLORS["text"],
                                      font=(FONT_FAMILY, 11, "bold"), wraplength=290, justify="left")
        self.detail_title.pack(anchor="w", padx=14, pady=(14, 4))

        tk.Button(detail_card, text="+ Schedule task for this day", command=self._schedule_for_selected_day,
                  bg=COLORS["accent"], fg="white", relief="flat", padx=10, pady=5,
                  cursor="hand2", font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", padx=14, pady=(0, 10))

        # ---- scheduled tasks due this day (upcoming or past) ----
        tk.Label(detail_card, text="📌 Scheduled", bg=COLORS["card"], fg=COLORS["accent"],
                  font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", padx=14)
        sched_cols = ("time", "title", "status")
        self.scheduled_tree = ttk.Treeview(detail_card, columns=sched_cols, show="headings", height=4)
        self.scheduled_tree.heading("time", text="Time")
        self.scheduled_tree.heading("title", text="Task")
        self.scheduled_tree.heading("status", text="Status")
        self.scheduled_tree.column("time", width=60, anchor="center")
        self.scheduled_tree.column("title", width=150)
        self.scheduled_tree.column("status", width=80)
        self.scheduled_tree.pack(fill="x", padx=14, pady=(2, 10))
        self.scheduled_tree.bind("<Double-1>", self._edit_scheduled_task)

        # ---- time actually tracked / logged this day ----
        tk.Label(detail_card, text="⏱ Time Logged", bg=COLORS["card"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", padx=14)
        cols = ("task", "duration", "tags")
        self.detail_tree = ttk.Treeview(detail_card, columns=cols, show="headings", height=8)
        self.detail_tree.heading("task", text="Task")
        self.detail_tree.heading("duration", text="Time")
        self.detail_tree.heading("tags", text="Tags")
        self.detail_tree.column("task", width=120)
        self.detail_tree.column("duration", width=65, anchor="center")
        self.detail_tree.column("tags", width=100)
        self.detail_tree.pack(fill="both", expand=True, padx=14, pady=(2, 8))

        self.detail_total = tk.Label(detail_card, text="", bg=COLORS["card"], fg=COLORS["accent"],
                                      font=(FONT_FAMILY, 10, "bold"))
        self.detail_total.pack(anchor="w", padx=14, pady=(0, 14))

        self._scheduled_row_id_map = {}

        self.refresh()

    def _prev_month(self):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self.refresh()

    def _next_month(self):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self.refresh()

    def refresh(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        self.month_label.config(text=f"{_calendar_module.month_name[self.month]} {self.year}")

        rows = load_all_rows()
        day_totals = defaultdict(int)
        month_prefix = f"{self.year:04d}-{self.month:02d}"
        for r in rows:
            if r.get("Date", "").startswith(month_prefix):
                day_totals[r["Date"]] += row_duration_seconds(r)

        all_tasks = load_all_tasks()
        day_scheduled_counts = defaultdict(int)
        for t in all_tasks:
            due = t.get("Due Date", "")
            if due.startswith(month_prefix) and t.get("Status") != "Completed":
                day_scheduled_counts[due] += 1

        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, wd in enumerate(weekday_names):
            tk.Label(self.grid_frame, text=wd, bg=COLORS["bg"], fg=COLORS["text_muted"],
                      font=(FONT_FAMILY, 9, "bold")).grid(row=0, column=i, pady=(0, 4))

        cal = _calendar_module.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self.year, self.month)
        today_str = datetime.now().strftime("%Y-%m-%d")

        for r_idx, week in enumerate(weeks, start=1):
            for c_idx, day_num in enumerate(week):
                if day_num == 0:
                    tk.Frame(self.grid_frame, bg=COLORS["bg"], width=70, height=56).grid(
                        row=r_idx, column=c_idx, padx=3, pady=3)
                    continue
                date_str = f"{self.year:04d}-{self.month:02d}-{day_num:02d}"
                secs = day_totals.get(date_str, 0)
                hours = secs / 3600

                if secs == 0:
                    bg, fg = COLORS["card"], COLORS["text_muted"]
                elif hours < 1:
                    bg, fg = COLORS["accent_soft"], COLORS["text"]
                elif hours < 3:
                    bg, fg = "#c3c9f7", COLORS["text"]
                else:
                    bg, fg = COLORS["accent"], "#ffffff"

                border_color = COLORS["success"] if date_str == today_str else COLORS["border"]
                cell = tk.Frame(self.grid_frame, bg=bg, width=70, height=56,
                                 highlightbackground=border_color,
                                 highlightthickness=2 if date_str == today_str else 1,
                                 cursor="hand2")
                cell.grid(row=r_idx, column=c_idx, padx=3, pady=3)
                cell.grid_propagate(False)

                top_row = tk.Frame(cell, bg=bg)
                top_row.pack(fill="x", padx=6, pady=(4, 0))
                day_lbl = tk.Label(top_row, text=str(day_num), bg=bg, fg=fg, font=(FONT_FAMILY, 10, "bold"))
                day_lbl.pack(side="left")
                sched_count = day_scheduled_counts.get(date_str, 0)
                pin_lbl = None
                if sched_count:
                    pin_lbl = tk.Label(top_row, text=f"📌{sched_count}", bg=bg,
                                        fg=(fg if bg == COLORS["accent"] else COLORS["accent"]),
                                        font=(FONT_FAMILY, 8, "bold"))
                    pin_lbl.pack(side="right")
                hrs_lbl = tk.Label(cell, text=(format_hms(secs) if secs else "—"), bg=bg, fg=fg,
                                    font=(FONT_FAMILY, 8))
                hrs_lbl.pack(anchor="w", padx=6)

                bind_targets = [cell, top_row, day_lbl, hrs_lbl]
                if pin_lbl:
                    bind_targets.append(pin_lbl)
                for widget in bind_targets:
                    widget.bind("<Button-1>", lambda e, d=date_str: self._select_day(d))

        self._select_day(self.selected_date if self.selected_date.startswith(month_prefix) else
                          f"{self.year:04d}-{self.month:02d}-01")

    def _select_day(self, date_str):
        self.selected_date = date_str
        self.detail_title.config(text=f"{date_str}")

        # ---- scheduled tasks due this day ----
        for row in self.scheduled_tree.get_children():
            self.scheduled_tree.delete(row)
        self._scheduled_row_id_map = {}

        tasks_due = [t for t in load_all_tasks() if t.get("Due Date") == date_str]
        tasks_due.sort(key=lambda t: t.get("Due Time", "") or "99:99")
        for t in tasks_due:
            item = self.scheduled_tree.insert("", "end", values=(
                t.get("Due Time", "") or "—", t.get("Title", ""), t.get("Status", "")
            ))
            self._scheduled_row_id_map[item] = t["ID"]

        # ---- time logged this day ----
        for row in self.detail_tree.get_children():
            self.detail_tree.delete(row)

        rows = [r for r in load_all_rows() if r.get("Date") == date_str]
        total = 0
        for r in rows:
            secs = row_duration_seconds(r)
            total += secs
            tags = r.get("Tags", "").replace(";", ", ")
            self.detail_tree.insert("", "end", values=(r.get("Task", ""), r.get("Duration (HH:MM:SS)", ""), tags))

        self.detail_total.config(text=f"Total: {format_hms(total)}" if rows else "No sessions logged this day.")

    def _schedule_for_selected_day(self):
        TaskDialog(self, self.app, on_saved=self._on_task_dialog_saved, prefill_date=self.selected_date)

    def _edit_scheduled_task(self, event=None):
        selection = self.scheduled_tree.selection()
        if not selection:
            return
        task_id = self._scheduled_row_id_map.get(selection[0])
        tasks = load_all_tasks()
        task = next((t for t in tasks if t["ID"] == task_id), None)
        if task:
            TaskDialog(self, self.app, on_saved=self._on_task_dialog_saved, existing_task=task)

    def _on_task_dialog_saved(self):
        self.refresh()
        self.app.refresh_all_data_views()


# ---------------------------------------------------------------------------
# Planner Page (Review & Plan: filter what got done vs what's pending
# in any date range, for better decision making)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Planner Page (Review & Plan)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Planner Page (Review & Plan)
# ---------------------------------------------------------------------------
class PlannerPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Content.TFrame")
        self.app = app
        self._build()

    def _build(self):
        # ---------------------------------------------------------------
        # Header
        # ---------------------------------------------------------------
        header = tk.Label(
            self,
            text="Review & Plan",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 20, "bold")
        )
        header.pack(
            anchor="w",
            padx=28,
            pady=(18, 2)
        )

        sub = tk.Label(
            self,
            text="Pick a date range to see what got done and what's still pending.",
            bg=COLORS["bg"],
            fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 9)
        )
        sub.pack(
            anchor="w",
            padx=28,
            pady=(0, 8)
        )

        # ---------------------------------------------------------------
        # Date range controls
        # ---------------------------------------------------------------
        control_row = tk.Frame(
            self,
            bg=COLORS["bg"]
        )
        control_row.pack(
            fill="x",
            padx=28
        )

        tk.Label(
            control_row,
            text="From:",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 9)
        ).pack(side="left")

        self.from_entry = ttk.Entry(
            control_row,
            width=12
        )
        self.from_entry.pack(
            side="left",
            padx=(4, 10)
        )

        tk.Label(
            control_row,
            text="To:",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 9)
        ).pack(side="left")

        self.to_entry = ttk.Entry(
            control_row,
            width=12
        )
        self.to_entry.pack(
            side="left",
            padx=(4, 10)
        )

        tk.Button(
            control_row,
            text="Apply",
            command=self.refresh,
            bg=COLORS["accent"],
            fg="white",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            font=(FONT_FAMILY, 8)
        ).pack(side="left")

        # ---------------------------------------------------------------
        # Presets
        # ---------------------------------------------------------------
        preset_row = tk.Frame(
            self,
            bg=COLORS["bg"]
        )
        preset_row.pack(
            fill="x",
            padx=28,
            pady=(6, 2)
        )

        presets = [
            ("Today", 0),
            ("This Week", "week"),
            ("Last 7 Days", 7),
            ("Last 30 Days", 30),
            ("This Month", "month"),
            ("All Time", "all")
        ]

        for label, kind in presets:
            tk.Button(
                preset_row,
                text=label,
                command=lambda k=kind: self._set_preset(k),
                bg=COLORS["card"],
                fg=COLORS["text"],
                relief="flat",
                padx=8,
                pady=3,
                cursor="hand2",
                highlightbackground=COLORS["border"],
                highlightthickness=1,
                font=(FONT_FAMILY, 8)
            ).pack(
                side="left",
                padx=3
            )

        self._set_preset(
            7,
            apply_refresh=False
        )

        # ---------------------------------------------------------------
        # Stats
        # ---------------------------------------------------------------
        self.stats_row = tk.Frame(
            self,
            bg=COLORS["bg"]
        )
        self.stats_row.pack(
            fill="x",
            padx=28,
            pady=8
        )

        # ---------------------------------------------------------------
        # Main body
        # ---------------------------------------------------------------
        body = tk.Frame(
            self,
            bg=COLORS["bg"]
        )
        body.pack(
            fill="both",
            expand=True,
            padx=28,
            pady=(0, 12)
        )

        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # ===============================================================
        # COMPLETED CARD
        # ===============================================================
        done_card = tk.Frame(
            body,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )

        done_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 6),
            pady=(0, 6)
        )

        tk.Label(
            done_card,
            text="✅ Completed in range",
            bg=COLORS["card"],
            fg=COLORS["success"],
            font=(FONT_FAMILY, 10, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=(8, 4)
        )

        done_cols = (
            "title",
            "labels",
            "completed",
            "time"
        )

        self.done_tree = ttk.Treeview(
            done_card,
            columns=done_cols,
            show="headings",
            height=7
        )

        for c, w, t in [
            ("title", 150, "Title"),
            ("labels", 100, "Labels"),
            ("completed", 90, "Completed"),
            ("time", 80, "Time Spent")
        ]:
            self.done_tree.heading(
                c,
                text=t
            )

            self.done_tree.column(
                c,
                width=w,
                anchor="w"
            )

        self.done_tree.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=(0, 8)
        )

        # ===============================================================
        # PENDING TASKS CARD
        # ===============================================================
        pending_card = tk.Frame(
            body,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )

        pending_card.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(6, 0),
            pady=(0, 6)
        )

        tk.Label(
            pending_card,
            text="🕓 Pending Tasks",
            bg=COLORS["card"],
            fg=COLORS["warning"],
            font=(FONT_FAMILY, 10, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=(8, 4)
        )

        pending_cols = (
            "title",
            "labels",
            "status",
            "due"
        )

        self.pending_tree = ttk.Treeview(
            pending_card,
            columns=pending_cols,
            show="headings",
            height=7
        )

        for c, w, t in [
            ("title", 150, "Title"),
            ("labels", 100, "Labels"),
            ("status", 90, "Status"),
            ("due", 90, "Due Date")
        ]:
            self.pending_tree.heading(
                c,
                text=t
            )

            self.pending_tree.column(
                c,
                width=w,
                anchor="w"
            )

        self.pending_tree.tag_configure(
            "overdue",
            foreground=COLORS["warning"]
        )

        self.pending_tree.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=(0, 8)
        )

        # ===============================================================
        # PENDING SUBTASKS CARD
        # ===============================================================
        self.subtask_card = tk.Frame(
            body,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )

        self.subtask_card.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(6, 0)
        )

        # Header
        subtask_header = tk.Frame(
            self.subtask_card,
            bg=COLORS["card"]
        )
        subtask_header.pack(
            fill="x",
            padx=10,
            pady=(8, 4)
        )

        tk.Label(
            subtask_header,
            text="📌 Pending Subtasks",
            bg=COLORS["card"],
            fg=COLORS["accent"],
            font=(FONT_FAMILY, 10, "bold")
        ).pack(
            side="left"
        )

        self.subtask_count_label = tk.Label(
            subtask_header,
            text="",
            bg=COLORS["card"],
            fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 8)
        )

        self.subtask_count_label.pack(
            side="left",
            padx=(8, 0)
        )

        # ---------------------------------------------------------------
        # Subtask Tree
        # ---------------------------------------------------------------
        subtask_cols = (
            "parent",
            "subtask",
            "status",
            "due"
        )

        subtask_table_frame = tk.Frame(
            self.subtask_card,
            bg=COLORS["card"]
        )

        subtask_table_frame.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=(0, 8)
        )

        self.subtask_tree = ttk.Treeview(
            subtask_table_frame,
            columns=subtask_cols,
            show="headings",
            height=6
        )

        self.subtask_tree.heading(
            "parent",
            text="Task"
        )

        self.subtask_tree.heading(
            "subtask",
            text="Pending Subtask"
        )

        self.subtask_tree.heading(
            "status",
            text="Status"
        )

        self.subtask_tree.heading(
            "due",
            text="Due Date"
        )

        self.subtask_tree.column(
            "parent",
            width=220,
            minwidth=150,
            anchor="w"
        )

        self.subtask_tree.column(
            "subtask",
            width=400,
            minwidth=200,
            anchor="w"
        )

        self.subtask_tree.column(
            "status",
            width=100,
            minwidth=80,
            anchor="w"
        )

        self.subtask_tree.column(
            "due",
            width=110,
            minwidth=90,
            anchor="w"
        )

        self.subtask_tree.tag_configure(
            "pending",
            foreground=COLORS["text"]
        )

        self.subtask_tree.tag_configure(
            "overdue",
            foreground=COLORS["warning"]
        )

        scrollbar = ttk.Scrollbar(
            subtask_table_frame,
            orient="vertical",
            command=self.subtask_tree.yview
        )

        self.subtask_tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.subtask_tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        # Initial refresh
        self.refresh()

    # -------------------------------------------------------------------
    # Preset handling
    # -------------------------------------------------------------------
    def _set_preset(
        self,
        kind,
        apply_refresh=True
    ):
        today = datetime.now().date()

        if kind == 0:
            frm = to = today

        elif kind == "week":
            frm = today - timedelta(
                days=today.weekday()
            )
            to = today

        elif kind == "month":
            frm = today.replace(
                day=1
            )
            to = today

        elif kind == "all":
            frm = None
            to = today

        else:
            frm = today - timedelta(
                days=int(kind) - 1
            )
            to = today

        self.from_entry.delete(
            0,
            tk.END
        )

        self.to_entry.delete(
            0,
            tk.END
        )

        self.from_entry.insert(
            0,
            frm.strftime("%Y-%m-%d")
            if frm
            else "0001-01-01"
        )

        self.to_entry.insert(
            0,
            to.strftime("%Y-%m-%d")
        )

        if apply_refresh:
            self.refresh()

    # -------------------------------------------------------------------
    # Stat card
    # -------------------------------------------------------------------
    def _make_stat_card(
        self,
        parent,
        title,
        value,
        color
    ):
        card = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )

        tk.Label(
            card,
            text=title,
            bg=COLORS["card"],
            fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 8)
        ).pack(
            anchor="w",
            padx=12,
            pady=(8, 0)
        )

        tk.Label(
            card,
            text=value,
            bg=COLORS["card"],
            fg=color,
            font=(FONT_FAMILY, 14, "bold")
        ).pack(
            anchor="w",
            padx=12,
            pady=(2, 8)
        )

        return card

    # -------------------------------------------------------------------
    # Parse subtasks
    # -------------------------------------------------------------------
    def _get_pending_subtasks(self, task):
        """
        Subtasks CSV field examples:

        1|Todo Section;1|Notes Section;0|Sub Tasks

        OR

        Decide outline of project;Using Langchain to connect LLM

        Convention:
            1|text -> pending
            0|text -> completed

        If no 0| / 1| prefix exists, the subtask is treated
        as pending.
        """

        raw = str(
            task.get("Subtasks", "")
        ).strip()

        if not raw:
            return []

        result = []

        # Split individual subtasks
        parts = [
            x.strip()
            for x in raw.split(";")
            if x.strip()
        ]

        for part in parts:

            status = "Pending"
            text = part

            # -----------------------------------------------------------
            # Explicit format:
            # 1|Todo Section
            # 0|Sub Tasks
            # -----------------------------------------------------------
            if "|" in part:
                prefix, remaining = part.split(
                    "|",
                    1
                )

                prefix = prefix.strip()

                if prefix == "1":
                    status = "Pending"
                    text = remaining.strip()

                elif prefix == "0":
                    status = "Completed"
                    text = remaining.strip()

                else:
                    # Unknown prefix -> keep complete text
                    status = "Pending"
                    text = part.strip()

            # Ignore completed subtasks
            if status == "Completed":
                continue

            if text:
                result.append(text)

        return result

    # -------------------------------------------------------------------
    # Refresh
    # -------------------------------------------------------------------
    def refresh(self):

        from_date = (
            self.from_entry.get().strip()
            or "0001-01-01"
        )

        to_date = (
            self.to_entry.get().strip()
            or datetime.now().strftime(
                "%Y-%m-%d"
            )
        )

        today_str = datetime.now().strftime(
            "%Y-%m-%d"
        )

        # ---------------------------------------------------------------
        # Load data
        # ---------------------------------------------------------------
        all_tasks = load_all_tasks()

        time_map = task_time_spent_map()

        # ---------------------------------------------------------------
        # Completed tasks in selected range
        # ---------------------------------------------------------------
        completed_in_range = [
            t
            for t in all_tasks
            if t.get("Status") == "Completed"
            and t.get("Completed Date")
            and from_date <= t["Completed Date"] <= to_date
        ]

        # ---------------------------------------------------------------
        # Created tasks in selected range
        # ---------------------------------------------------------------
        created_in_range = [
            t
            for t in all_tasks
            if t.get("Created Date")
            and from_date <= t["Created Date"] <= to_date
        ]

        # ---------------------------------------------------------------
        # Current pending tasks
        # ---------------------------------------------------------------
        pending_tasks = [
            t
            for t in all_tasks
            if t.get("Status") != "Completed"
        ]

        # ---------------------------------------------------------------
        # Overdue tasks
        # ---------------------------------------------------------------
        overdue_tasks = [
            t
            for t in pending_tasks
            if t.get("Due Date")
            and t["Due Date"] < today_str
        ]

        # ---------------------------------------------------------------
        # Logged time
        # ---------------------------------------------------------------
        log_rows = load_all_rows()

        in_range_logs = [
            r
            for r in log_rows
            if from_date <= r.get("Date", "") <= to_date
        ]

        total_seconds_range = sum(
            row_duration_seconds(r)
            for r in in_range_logs
        )

        # ---------------------------------------------------------------
        # Stats
        # ---------------------------------------------------------------
        for w in self.stats_row.winfo_children():
            w.destroy()

        completion_rate = (
            len(completed_in_range)
            / len(created_in_range)
            * 100
            if created_in_range
            else None
        )

        cards = [
            (
                "Completed",
                str(
                    len(completed_in_range)
                ),
                COLORS["success"]
            ),
            (
                "Created",
                str(
                    len(created_in_range)
                ),
                COLORS["accent"]
            ),
            (
                "Time tracked",
                format_hms(
                    total_seconds_range
                ),
                COLORS["accent"]
            ),
            (
                "Pending",
                f"{len(pending_tasks)} "
                f"({len(overdue_tasks)} overdue)",
                COLORS["warning"]
                if overdue_tasks
                else COLORS["text"]
            ),
            (
                "Completion rate",
                (
                    f"{completion_rate:.0f}%"
                    if completion_rate is not None
                    else "—"
                ),
                COLORS["success"]
            )
        ]

        for i, (
            title,
            value,
            color
        ) in enumerate(cards):

            card = self._make_stat_card(
                self.stats_row,
                title,
                value,
                color
            )

            card.grid(
                row=0,
                column=i,
                padx=4,
                sticky="nsew"
            )

            self.stats_row.columnconfigure(
                i,
                weight=1
            )

        # ===============================================================
        # Completed table
        # ===============================================================
        for row in self.done_tree.get_children():
            self.done_tree.delete(row)

        for t in sorted(
            completed_in_range,
            key=lambda x: x.get(
                "Completed Date",
                ""
            ),
            reverse=True
        ):

            labels = str(
                t.get(
                    "Labels",
                    ""
                )
            ).replace(
                ";",
                ", "
            )

            spent = format_hms(
                time_map.get(
                    t.get(
                        "Title",
                        ""
                    ),
                    0
                )
            )

            self.done_tree.insert(
                "",
                "end",
                values=(
                    t.get(
                        "Title",
                        ""
                    ),
                    labels,
                    t.get(
                        "Completed Date",
                        ""
                    ),
                    spent
                )
            )

        # ===============================================================
        # Pending tasks table
        # ===============================================================
        for row in self.pending_tree.get_children():
            self.pending_tree.delete(row)

        def sort_key(t):
            due = t.get(
                "Due Date",
                ""
            )

            return (
                due == "",
                due
            )

        for t in sorted(
            pending_tasks,
            key=sort_key
        ):

            labels = str(
                t.get(
                    "Labels",
                    ""
                )
            ).replace(
                ";",
                ", "
            )

            due = t.get(
                "Due Date",
                ""
            )

            is_overdue = (
                bool(due)
                and due < today_str
            )

            tags = (
                ("overdue",)
                if is_overdue
                else ()
            )

            due_display = (
                f"{format_due(t)}  (overdue)"
                if is_overdue
                else format_due(t)
            )

            self.pending_tree.insert(
                "",
                "end",
                values=(
                    t.get(
                        "Title",
                        ""
                    ),
                    labels,
                    t.get(
                        "Status",
                        ""
                    ),
                    due_display
                ),
                tags=tags
            )

        # ===============================================================
        # Pending Subtasks
        # ===============================================================
        for row in self.subtask_tree.get_children():
            self.subtask_tree.delete(row)

        pending_subtask_count = 0

        # ---------------------------------------------------------------
        # Only current non-completed tasks
        # ---------------------------------------------------------------
        for task in pending_tasks:

            subtasks = self._get_pending_subtasks(
                task
            )

            for subtask in subtasks:

                pending_subtask_count += 1

                due = str(
                    task.get(
                        "Due Date",
                        ""
                    )
                ).strip()

                is_overdue = (
                    bool(due)
                    and due < today_str
                )

                tags = (
                    ("overdue",)
                    if is_overdue
                    else ("pending",)
                )

                due_display = (
                    f"{due} (overdue)"
                    if is_overdue
                    else due
                )

                self.subtask_tree.insert(
                    "",
                    "end",
                    values=(
                        task.get(
                            "Title",
                            ""
                        ),
                        subtask,
                        "Pending",
                        due_display
                    ),
                    tags=tags
                )

        # ---------------------------------------------------------------
        # Subtask counter
        # ---------------------------------------------------------------
        self.subtask_count_label.config(
            text=(
                f"{pending_subtask_count} pending"
            )
        )

        # ---------------------------------------------------------------
        # Empty state
        # ---------------------------------------------------------------
        if pending_subtask_count == 0:

            self.subtask_tree.insert(
                "",
                "end",
                values=(
                    "",
                    "🎉 No pending subtasks",
                    "",
                    ""
                )
            )

# ---------------------------------------------------------------------------
# Analytics Page
# ---------------------------------------------------------------------------
class AnalyticsPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Content.TFrame")
        self.app = app
        self.range_var = tk.StringVar(value="Last 7 days")
        self._build()

    def _build(self):
        header = tk.Label(self, text="Analytics", bg=COLORS["bg"], fg=COLORS["text"],
                           font=(FONT_FAMILY, 20, "bold"))
        header.pack(anchor="w", padx=28, pady=(24, 4))
        sub = tk.Label(self, text="See where your time actually goes.",
                        bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, 10))
        sub.pack(anchor="w", padx=28, pady=(0, 12))

        control_row = tk.Frame(self, bg=COLORS["bg"])
        control_row.pack(fill="x", padx=28)
        tk.Label(control_row, text="Range:", bg=COLORS["bg"], fg=COLORS["text"],
                  font=(FONT_FAMILY, 9)).pack(side="left")
        range_combo = ttk.Combobox(control_row, textvariable=self.range_var, state="readonly",
                                    values=["Last 7 days", "Last 14 days", "Last 30 days", "All time"],
                                    width=16)
        range_combo.pack(side="left", padx=8)
        range_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        tk.Button(control_row, text="Refresh", command=self.refresh, bg=COLORS["accent"],
                  fg="white", relief="flat", padx=10, pady=3, cursor="hand2").pack(side="left", padx=6)

        # Stat cards row
        self.stats_row = tk.Frame(self, bg=COLORS["bg"])
        self.stats_row.pack(fill="x", padx=28, pady=14)

        # Charts area
        self.charts_frame = tk.Frame(self, bg=COLORS["bg"])
        self.charts_frame.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        self.canvas = None

    def _days_back(self):
        mapping = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30, "All time": None}
        return mapping[self.range_var.get()]

    def _filtered_rows(self):
        rows = load_all_rows()
        days_back = self._days_back()
        if days_back is None:
            return rows
        cutoff = (datetime.now() - timedelta(days=days_back - 1)).strftime("%Y-%m-%d")
        return [r for r in rows if r["Date"] >= cutoff]

    def _make_stat_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"],
                         highlightthickness=1)
        tk.Label(card, text=title, bg=COLORS["card"], fg=COLORS["text_muted"],
                  font=(FONT_FAMILY, 9)).pack(anchor="w", padx=14, pady=(12, 0))
        tk.Label(card, text=value, bg=COLORS["card"], fg=color,
                  font=(FONT_FAMILY, 16, "bold")).pack(anchor="w", padx=14, pady=(2, 12))
        return card

    def refresh(self):
        for w in self.stats_row.winfo_children():
            w.destroy()
        for w in self.charts_frame.winfo_children():
            w.destroy()
        if self.canvas:
            self.canvas = None

        rows = self._filtered_rows()

        if not rows:
            tk.Label(self.charts_frame, text="No sessions logged yet for this range.\n"
                                              "Track something on the Timer page to see analytics here.",
                      bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, 11),
                      justify="center").pack(expand=True)
            return

        # ---- aggregate ----
        total_seconds = sum(row_duration_seconds(r) for r in rows)
        by_task = defaultdict(int)
        by_day = defaultdict(int)
        by_tag = defaultdict(int)
        session_count = len(rows)
        for r in rows:
            secs = row_duration_seconds(r)
            by_task[r["Task"]] += secs
            by_day[r["Date"]] += secs
            tags = [t for t in r.get("Tags", "").split(";") if t]
            if not tags:
                by_tag["Untagged"] += secs
            else:
                for t in tags:
                    by_tag[t] += secs

        avg_session = total_seconds / session_count if session_count else 0
        best_day = max(by_day.items(), key=lambda x: x[1]) if by_day else ("-", 0)
        top_task = max(by_task.items(), key=lambda x: x[1]) if by_task else ("-", 0)

        # ---- stat cards ----
        cards = [
            ("Total tracked", format_hms(total_seconds), COLORS["accent"]),
            ("Sessions logged", str(session_count), COLORS["success"]),
            ("Avg session length", format_hms(avg_session), COLORS["warning"]),
            ("Most-tracked task", f"{top_task[0]}", COLORS["accent"]),
            ("Best day", f"{best_day[0]} ({format_hms(best_day[1])})", COLORS["success"]),
        ]
        for i, (title, value, color) in enumerate(cards):
            card = self._make_stat_card(self.stats_row, title, value, color)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            self.stats_row.columnconfigure(i, weight=1)

        # ---- charts (matplotlib figure with 3 subplots) ----
        fig = Figure(figsize=(11.5, 4.2), dpi=100)
        fig.patch.set_facecolor(COLORS["bg"])

        # 1) Bar chart: time per task
        ax1 = fig.add_subplot(1, 3, 1)
        tasks_sorted = sorted(by_task.items(), key=lambda x: -x[1])[:8]
        labels = [t[0] for t in tasks_sorted]
        values = [t[1] / 3600 for t in tasks_sorted]
        colors1 = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))]
        ax1.barh(labels, values, color=colors1)
        ax1.invert_yaxis()
        ax1.set_title("Hours by Task", fontsize=10, fontweight="bold")
        ax1.set_xlabel("hours", fontsize=8)
        ax1.tick_params(labelsize=8)
        ax1.set_facecolor(COLORS["card"])

        # 2) Line chart: daily trend
        ax2 = fig.add_subplot(1, 3, 2)
        days_sorted = sorted(by_day.items())
        day_labels = [d[0][5:] for d in days_sorted]  # MM-DD
        day_values = [d[1] / 3600 for d in days_sorted]
        ax2.plot(day_labels, day_values, marker="o", color=COLORS["accent"], linewidth=2)
        ax2.fill_between(range(len(day_labels)), day_values, color=COLORS["accent"], alpha=0.12)
        ax2.set_title("Daily Trend (hrs)", fontsize=10, fontweight="bold")
        ax2.tick_params(axis="x", rotation=45, labelsize=7)
        ax2.tick_params(axis="y", labelsize=8)
        ax2.set_facecolor(COLORS["card"])

        # 3) Pie chart: tag split
        ax3 = fig.add_subplot(1, 3, 3)
        tag_sorted = sorted(by_tag.items(), key=lambda x: -x[1])[:6]
        tag_labels = [t[0] for t in tag_sorted]
        tag_values = [t[1] for t in tag_sorted]
        colors3 = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(tag_labels))]
        ax3.pie(tag_values, labels=tag_labels, autopct="%1.0f%%", colors=colors3,
                textprops={"fontsize": 7})
        ax3.set_title("Time by Tag", fontsize=10, fontweight="bold")

        fig.tight_layout(pad=2.0)

        self.canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # ---- simple "scope for improvement" insight line ----
        insight = self._build_insight(by_task, by_day, total_seconds, days_back=self._days_back())
        tk.Label(self.charts_frame, text=insight, bg=COLORS["bg"], fg=COLORS["text_muted"],
                  font=(FONT_FAMILY, 9, "italic"), wraplength=1000, justify="left").pack(
            anchor="w", pady=(8, 0))

    def _build_insight(self, by_task, by_day, total_seconds, days_back):
        if not by_day:
            return ""
        num_days = days_back if days_back else len(by_day)
        num_days = max(num_days, 1)
        avg_per_day = total_seconds / num_days
        least_task = min(by_task.items(), key=lambda x: x[1]) if by_task else None
        zero_days = num_days - len(by_day)
        parts = [f"Averaging {format_hms(avg_per_day)}/day across this range."]
        if zero_days > 0:
            parts.append(f"{zero_days} day(s) in range have no logged sessions at all — potential gap.")
        if least_task and len(by_task) > 1:
            parts.append(f"'{least_task[0]}' gets the least time ({format_hms(least_task[1])}) — worth a look if it matters to you.")
        return "  ".join(parts)


# ---------------------------------------------------------------------------
# Main App shell (sidebar + page switching)
# ---------------------------------------------------------------------------
class App:
    NAV_ITEMS = [
        ("timer", "⏱  Timer"),
        ("tasks", "📝  Tasks"),
        ("calendar", "🗓  Calendar"),
        ("planner", "🔍  Review & Plan"),
        ("history", "📜  History"),
        ("analytics", "📊  Analytics"),
        ("notes", "🗒  Notes"),

    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Time Tracker")
        self.root.geometry("1080x680")
        self.root.minsize(980, 620)
        self.root.configure(bg=COLORS["bg"])

        ensure_csv()
        ensure_tasks_csv()
        self.config = load_config()

        self._setup_styles()

        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)

        self.sidebar = Sidebar(body, self.NAV_ITEMS, self.show_page)
        self.sidebar.pack(side="left", fill="y")

        self.content_container = tk.Frame(body, bg=COLORS["bg"])
        self.content_container.pack(side="left", fill="both", expand=True)

        self.pages = {
            "timer": TimerPage(self.content_container, self),
            "tasks": TasksPage(self.content_container, self),
            "calendar": CalendarPage(self.content_container, self),
            "planner": PlannerPage(self.content_container, self),
            "history": HistoryPage(self.content_container, self),
            "analytics": AnalyticsPage(self.content_container, self),
            "notes": NotesPage(self.content_container, self) ,
        }
        for page in self.pages.values():
            page.place(x=0, y=0, relwidth=1, relheight=1)

        self.show_page("timer")

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Sidebar.TFrame", background=COLORS["sidebar"])
        style.configure("Content.TFrame", background=COLORS["bg"])
        style.configure("Treeview", rowheight=26, font=(FONT_FAMILY, 9),
                         fieldbackground=COLORS["card"], background=COLORS["card"])
        style.configure("Treeview.Heading", font=(FONT_FAMILY, 9, "bold"))
        style.map("Treeview", background=[("selected", COLORS["accent"])])

    def show_page(self, key):
        self.sidebar.set_active(key)
        self.pages[key].tkraise()
        if key == "history":
            self.pages["history"].refresh()
        elif key == "analytics":
            self.pages["analytics"].refresh()
        elif key == "tasks":
            self.pages["tasks"].refresh()
        elif key == "calendar":
            self.pages["calendar"].refresh()
        elif key == "planner":
            self.pages["planner"].refresh()
        elif key == "timer":
            self.pages["timer"].refresh_task_options()
        elif key == "notes":
            self.pages["notes"].refresh()


    def add_known_task(self, task):
        if task and task not in self.config["tasks"]:
            self.config["tasks"].append(task)
            save_config(self.config)
            self.pages["timer"].refresh_task_options()

    def add_known_tag(self, tag):
        if tag and tag not in self.config["tags"]:
            self.config["tags"].append(tag)
            save_config(self.config)

    def add_known_label(self, label):
        if label and label not in self.config["labels"]:
            self.config["labels"].append(label)
            save_config(self.config)

    def refresh_all_data_views(self):
        self.pages["history"].refresh()
        self.pages["analytics"].refresh()
        self.pages["tasks"].refresh()
        self.pages["calendar"].refresh()
        self.pages["planner"].refresh()
        self.pages["timer"].refresh_task_options()
        self.pages["notes"].refresh()



def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()