"""Back up your progress database and export your scores as CSV.

progress.db is never uploaded to GitHub (it holds your personal answers), so this copies it to a
private folder instead: your OneDrive if you have one, so it is also saved in the cloud.
"""

import csv
import io
import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

FOLDER_NAME = "Interview Coach backups"
KEEP = 10
PREFIX = "progress-"


def backup_folder():
    """Where backups go: BACKUP_FOLDER in .env, else OneDrive, else your Documents folder."""
    load_dotenv()
    if os.getenv("BACKUP_FOLDER"):
        return Path(os.getenv("BACKUP_FOLDER"))
    if os.getenv("OneDrive"):  # Windows sets this when OneDrive is installed
        return Path(os.getenv("OneDrive")) / FOLDER_NAME
    return Path.home() / "Documents" / FOLDER_NAME


def backups(folder):
    """Backup files in the folder, newest first."""
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted(folder.glob(f"{PREFIX}*.db"), reverse=True)


def backup_now(db_path, folder, today, keep=KEEP):
    """Copy the database to progress-YYYY-MM-DD.db (one per day) and keep the newest few."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{PREFIX}{today.isoformat()}.db"
    # SQLite's own backup is safe even while the app has the database open
    source = sqlite3.connect(db_path)
    copy = sqlite3.connect(target)
    with copy:
        source.backup(copy)
    source.close()
    copy.close()
    for old in backups(folder)[keep:]:
        old.unlink()
    return target


def daily_backup(db_path, folder, today):
    """Back up once a day. Returns the new file, or None if today's backup already exists."""
    if not Path(db_path).exists():
        return None
    if (Path(folder) / f"{PREFIX}{today.isoformat()}.db").exists():
        return None
    return backup_now(db_path, folder, today)


def _practice_name(job_id, job_names):
    """'abc:technical' -> ('Acme - Analyst', 'technical'); 'aptitude:mock' -> ('All jobs', 'aptitude mock')."""
    base, _, kind = job_id.partition(":")
    if base == "aptitude":
        return "All jobs", " ".join(["aptitude", kind]).strip()
    return job_names.get(base, "Unknown or deleted job"), kind or "daily"


def answers_csv(conn, job_names):
    """Every answer as CSV text: day, job, practice type, topic, question id, correct."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["day", "job", "practice", "topic", "question_id", "correct"])
    rows = conn.execute("SELECT day, job_id, topic, question_id, correct FROM answers ORDER BY id")
    for day, job_id, topic, question_id, correct in rows:
        job, practice = _practice_name(job_id, job_names)
        writer.writerow([day, job, practice, topic, question_id, "yes" if correct else "no"])
    return out.getvalue()


def interviews_csv(conn, job_names):
    """Every mock interview answer as CSV text, with its score and tips."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["day", "job", "question", "your answer", "score", "strength", "tips"])
    rows = conn.execute(
        "SELECT i.day, i.job_id, a.question, a.answer, a.score, a.feedback "
        "FROM interview_answers a JOIN interviews i ON i.id = a.interview_id ORDER BY i.id, a.position"
    )
    for day, job_id, question, answer, score, feedback in rows:
        data = json.loads(feedback)
        writer.writerow([
            day, job_names.get(job_id, "Unknown or deleted job"), question, answer, score,
            data.get("strength", ""), " | ".join(data.get("tips", [])),
        ])
    return out.getvalue()
