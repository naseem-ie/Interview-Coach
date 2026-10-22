"""Save and read your practice progress (answers, XP, streak, readiness) in SQLite."""

import json
import os
import sqlite3
from datetime import timedelta
from pathlib import Path

# DATA_DIR lets Docker keep the database in a mounted folder; normally it sits next to the code
DATA_DIR = Path(os.getenv("DATA_DIR") or Path(__file__).parent)
DB_FILE = DATA_DIR / "progress.db"

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
    conn.execute(
        """CREATE TABLE IF NOT EXISTS mock_tests (
            id INTEGER PRIMARY KEY,
            day TEXT NOT NULL,
            format TEXT NOT NULL,
            right INTEGER NOT NULL,
            answered INTEGER NOT NULL,
            total INTEGER NOT NULL,
            seconds INTEGER NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ai_questions (
            id TEXT PRIMARY KEY,
            skill TEXT NOT NULL,
            job_id TEXT NOT NULL,
            day TEXT NOT NULL,
            data TEXT NOT NULL,
            reported INTEGER NOT NULL DEFAULT 0
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY,
            day TEXT NOT NULL,
            job_id TEXT NOT NULL,
            average REAL NOT NULL,
            answered INTEGER NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS interview_answers (
            interview_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            score INTEGER NOT NULL,
            feedback TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


def save_interview(conn, day, job_id, results, average):
    """Save a finished mock interview and every answer with its feedback. Returns its id."""
    answered = [r for r in results if r.get("score") is not None]
    cursor = conn.execute(
        "INSERT INTO interviews (day, job_id, average, answered) VALUES (?, ?, ?, ?)",
        (day.isoformat(), job_id, average, len(answered)),
    )
    interview_id = cursor.lastrowid
    conn.executemany(
        "INSERT INTO interview_answers (interview_id, position, question, answer, score, feedback) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (interview_id, n, r["question"], r["answer"], r["score"], json.dumps(r["feedback"]))
            for n, r in enumerate(answered)
        ],
    )
    conn.commit()
    return interview_id


def interviews(conn, job_id):
    """Past mock interviews for a job, newest first, each with its answers."""
    rows = conn.execute(
        "SELECT id, day, average, answered FROM interviews WHERE job_id = ? ORDER BY id DESC",
        (job_id,),
    ).fetchall()
    result = []
    for interview_id, day, average, answered in rows:
        answers = conn.execute(
            "SELECT question, answer, score, feedback FROM interview_answers "
            "WHERE interview_id = ? ORDER BY position",
            (interview_id,),
        )
        result.append({
            "day": day, "average": average, "answered": answered,
            "answers": [
                {"question": q, "answer": a, "score": sc, "feedback": json.loads(f)}
                for q, a, sc, f in answers
            ],
        })
    return result


def save_ai_questions(conn, day, job_id, skill, questions):
    """Save AI-written questions for a skill. Returns how many were new."""
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO ai_questions (id, skill, job_id, day, data) VALUES (?, ?, ?, ?, ?)",
        [(q["id"], skill, job_id, day.isoformat(), json.dumps(q)) for q in questions],
    )
    conn.commit()
    return conn.total_changes - before


def ai_questions(conn, skills, job_id):
    """Saved AI questions for these skills (any job) or added for this job. Reported ones are left out."""
    lowered = [s.lower() for s in skills]
    marks = ",".join("?" * len(lowered)) or "''"
    rows = conn.execute(
        f"SELECT data FROM ai_questions WHERE reported = 0 AND (LOWER(skill) IN ({marks}) OR job_id = ?) "
        "ORDER BY day, id",
        (*lowered, job_id),
    )
    return [json.loads(row[0]) for row in rows]


def report_ai_question(conn, question_id):
    """Hide an AI question you think is wrong. It is kept in the file but never shown again."""
    conn.execute("UPDATE ai_questions SET reported = 1 WHERE id = ?", (question_id,))
    conn.commit()


def record_mock_test(conn, day, format_key, right, answered, total, seconds):
    """Save the result of a timed mock test."""
    conn.execute(
        "INSERT INTO mock_tests (day, format, right, answered, total, seconds) VALUES (?, ?, ?, ?, ?, ?)",
        (day.isoformat(), format_key, right, answered, total, seconds),
    )
    conn.commit()


def mock_tests(conn, format_key):
    """Past results for one mock test format, newest first."""
    rows = conn.execute(
        "SELECT day, right, answered, total, seconds FROM mock_tests WHERE format = ? ORDER BY id DESC",
        (format_key,),
    )
    keys = ["day", "right", "answered", "total", "seconds"]
    return [dict(zip(keys, row)) for row in rows]


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


def _latest_answers(conn):
    """Latest answer for each question: {question_id: (topic, correct)}."""
    latest = {}
    rows = conn.execute("SELECT question_id, topic, correct FROM answers ORDER BY id")
    for question_id, topic, correct in rows:
        latest[question_id] = (topic, correct)
    return latest


def topic_stats(conn, topic_ids, topic_sizes, pass_rate=0.8):
    """Per topic: questions in the bank, answered, right on latest try, percent and status.

    topic_sizes is {topic_id: number of questions in the bank}.
    """
    latest = _latest_answers(conn)
    stats = {}
    for topic in topic_ids:
        results = [correct for t, correct in latest.values() if t == topic]
        stats[topic] = _stat(topic_sizes.get(topic, 0), len(results), sum(results), pass_rate)
    return stats


def _stat(total, answered, right, pass_rate):
    """Percent and status (Not started / Learning / Mastered) for a group of questions."""
    percent = round(100 * right / total) if total else 0
    if answered == 0:
        status = "Not started"
    elif total and right / total >= pass_rate:
        status = "Mastered"
    else:
        status = "Learning"
    return {"total": total, "answered": answered, "correct": right, "percent": percent, "status": status}


def ai_skill_stats(conn, questions, pass_rate=0.8):
    """Like topic_stats, but for AI questions grouped by skill: {skill: stats}."""
    latest = _latest_answers(conn)
    groups = {}
    for q in questions:
        group = groups.setdefault(q["skill"], [0, 0, 0])  # total, answered, right
        group[0] += 1
        if q["id"] in latest:
            group[1] += 1
            group[2] += latest[q["id"]][1]
    return {skill: _stat(*group, pass_rate) for skill, group in groups.items()}


def combined_readiness(*stat_groups):
    """Percent right on the latest try across several stats dicts (bank topics and AI skills)."""
    stats = [s for group in stat_groups for s in group.values()]
    total = sum(s["total"] for s in stats)
    right = sum(s["correct"] for s in stats)
    return round(100 * right / total) if total else 0


def readiness(conn, topic_ids, topic_sizes):
    """Percent of all questions in these topics that you got right on your latest try."""
    stats = topic_stats(conn, topic_ids, topic_sizes)
    total = sum(s["total"] for s in stats.values())
    right = sum(s["correct"] for s in stats.values())
    return round(100 * right / total) if total else 0


def _job_filter(job_id):
    """SQL condition matching a job's challenges (e.g. 'abc', 'abc:technical')."""
    return "(job_id = ? OR job_id LIKE ?)", (job_id, f"{job_id}:%")


def job_summary(conn, job_id):
    """Practice for one job: answers given, how many right, challenges finished, XP earned."""
    condition, params = _job_filter(job_id)
    answered, right = conn.execute(
        f"SELECT COUNT(*), COALESCE(SUM(correct), 0) FROM answers WHERE {condition}", params
    ).fetchone()
    challenges = conn.execute(
        f"SELECT COUNT(*) FROM challenges WHERE {condition}", params
    ).fetchone()[0]
    return {
        "answered": answered,
        "correct": right,
        "accuracy": round(100 * right / answered) if answered else 0,
        "challenges": challenges,
        "xp": right * XP_PER_CORRECT + challenges * XP_PER_CHALLENGE,
    }


def recent_accuracy(conn, job_id, last=30):
    """Percent right over the most recent answers for a challenge and its parts (e.g. 'aptitude')."""
    condition, params = _job_filter(job_id)
    rows = conn.execute(
        f"SELECT correct FROM answers WHERE {condition} ORDER BY id DESC LIMIT ?", params + (last,)
    ).fetchall()
    return round(100 * sum(r[0] for r in rows) / len(rows)) if rows else 0
