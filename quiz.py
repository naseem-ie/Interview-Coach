"""Question bank and daily challenge logic for Interview Coach."""

import json
import random
import re
from pathlib import Path

QUESTIONS_FILE = Path(__file__).parent / "data" / "questions.json"


def load_bank(path=QUESTIONS_FILE):
    """Read the question bank (topics and questions) from the JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _mentions(text, keyword):
    """True if keyword appears in text as a whole word (so 'ci' does not match 'decision')."""
    return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None


def topics_for_job(skill_gaps, topics):
    """Return the topic ids that match a job's skill gaps. Behavioural is always included."""
    text = (skill_gaps or "").lower()
    matched = [
        topic_id
        for topic_id, topic in topics.items()
        if any(_mentions(text, keyword) for keyword in topic["keywords"])
    ]
    if "behavioural" not in matched:
        matched.append("behavioural")
    return matched


def _priority(question, history):
    """Lower number = shown first. Wrong last time, then new, then seen, then mastered."""
    record = history.get(question["id"])
    if record is None:
        return 1
    if not record["last_correct"]:
        return 0
    if record["correct_streak"] >= 3:
        return 3
    return 2


def pick_daily_questions(bank, topic_ids, day, job_id="", count=5, history=None):
    """Pick today's questions for one job. Same day and job always give the same set."""
    history = history or {}
    pool = [q for q in bank["questions"] if q["topic"] in topic_ids]
    rng = random.Random(f"{job_id}-{day.isoformat()}")
    rng.shuffle(pool)
    pool.sort(key=lambda q: _priority(q, history))
    return pool[:count]


CORE_TECHNICAL = ["itil", "linux", "sql"]


def split_topics(topic_ids):
    """Split a job's topics into (technical, behavioural).

    If the job has no technical skill gaps recorded, fall back to core support topics.
    """
    technical = [t for t in topic_ids if t != "behavioural"]
    return technical or list(CORE_TECHNICAL), ["behavioural"]


def topic_sizes(bank):
    """How many questions the bank has for each topic: {topic_id: count}."""
    sizes = {}
    for question in bank["questions"]:
        sizes[question["topic"]] = sizes.get(question["topic"], 0) + 1
    return sizes
