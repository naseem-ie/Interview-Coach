"""Question bank and daily challenge logic for Interview Coach."""

import json
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