"""Save and read your practice progress (answers, XP, streak, readiness) in SQLite."""

import sqlite3
from datetime import timedelta
from pathlib import Path

DB_FILE = Path(__file__).parent / "progress.db"

XP_PER_CORRECT = 10
XP_PER_CHALLENGE = 20
XP_PER_LEVEL = 100
LEVEL_NAMES = [
    "Rookie", "Learner", "Practitioner", "Troubleshooter", "Analyst",
    "Specialist", "Expert", "Senior", "Lead", "Interview-Ready",
]


def connect(path=DB_FILE):
    """Open the database file, creating the tables the first time."""
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY,
            day TEXT NOT NULL,
            job_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            correct INTEGER NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS challenges (
            day TEXT NOT NULL,
            job_id TEXT NOT NULL,
            PRIMARY KEY (day, job_id)
        )"""
    )
    conn.commit()
    return conn


def record_answer(conn, day, job_id, question, correct):
    """Save one answer."""
    conn.execute(
        "INSERT INTO answers (day, job_id, question_id, topic, correct) VALUES (?, ?, ?, ?, ?)",
        (day.isoformat(), job_id, question["id"], question["topic"], int(correct)),
    )
    conn.commit()


def complete_challenge(conn, day, job_id):
    """Mark today's challenge for a job as finished (only counted once)."""
    conn.execute(
        "INSERT OR IGNORE INTO challenges (day, job_id) VALUES (?, ?)",
        (day.isoformat(), job_id),
    )
    conn.commit()


def question_history(conn, before=None):
    """For each question: was the latest answer right, and how many right in a row.

    Pass before=today to ignore today's answers, so today's question set stays fixed.
    """
    history = {}
    query, params = "SELECT question_id, correct FROM answers", ()
    if before is not None:
        query, params = query + " WHERE day < ?", (before.isoformat(),)
    rows = conn.execute(query + " ORDER BY id", params)
    for question_id, correct in rows:
        record = history.setdefault(question_id, {"last_correct": False, "correct_streak": 0})
        record["last_correct"] = bool(correct)
        record["correct_streak"] = record["correct_streak"] + 1 if correct else 0
    return history


def answers_for_day(conn, day, job_id):
    """Today's answers for one job: {question_id: True/False}."""
    rows = conn.execute(
        "SELECT question_id, correct FROM answers WHERE day = ? AND job_id = ? ORDER BY id",
        (day.isoformat(), job_id),
    )
    return {question_id: bool(correct) for question_id, correct in rows}


def total_xp(conn):
    """XP = 10 per correct answer + 20 per finished challenge."""
    correct = conn.execute("SELECT COUNT(*) FROM answers WHERE correct = 1").fetchone()[0]
    challenges = conn.execute("SELECT COUNT(*) FROM challenges").fetchone()[0]
    return correct * XP_PER_CORRECT + challenges * XP_PER_CHALLENGE


def level_for(xp):
    """Return (level number, level name, XP into this level). Level 10 is the top."""
    number = min(xp // XP_PER_LEVEL + 1, len(LEVEL_NAMES))
    return number, LEVEL_NAMES[number - 1], xp - (number - 1) * XP_PER_LEVEL


def streak(conn, today):
    """Days in a row with a finished challenge, counting back from today (or yesterday)."""
    days = {row[0] for row in conn.execute("SELECT DISTINCT day FROM challenges")}
    current = today if today.isoformat() in days else today - timedelta(days=1)
    count = 0
    while current.isoformat() in days:
        count += 1
        current -= timedelta(days=1)
    return count


def readiness(conn, topic_ids, min_answered=3, pass_rate=0.8):
    """Percent of a job's topics mastered: 3+ questions answered, 80%+ right on latest tries."""
    if not topic_ids:
        return 0
    latest = {}
    rows = conn.execute("SELECT question_id, topic, correct FROM answers ORDER BY id")
    for question_id, topic, correct in rows:
        latest[question_id] = (topic, correct)

    mastered = 0
    for topic in topic_ids:
        results = [correct for t, correct in latest.values() if t == topic]
        if len(results) >= min_answered and sum(results) / len(results) >= pass_rate:
            mastered += 1
    return round(100 * mastered / len(topic_ids))


def topic_stats(conn, topic_ids, min_answered=3, pass_rate=0.8):
    """Per topic: questions answered, how many right (latest tries), and a status label."""
    latest = {}
    rows = conn.execute("SELECT question_id, topic, correct FROM answers ORDER BY id")
    for question_id, topic, correct in rows:
        latest[question_id] = (topic, correct)

    stats = {}
    for topic in topic_ids:
        results = [correct for t, correct in latest.values() if t == topic]
        answered, right = len(results), sum(results)
        if answered == 0:
            status = "Not started"
        elif answered >= min_answered and right / answered >= pass_rate:
            status = "Mastered"
        else:
            status = "Learning"
        stats[topic] = {"answered": answered, "correct": right, "status": status}
    return stats
