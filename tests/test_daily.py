"""Tests for picking the daily challenge questions."""

from datetime import date

from quiz import load_bank, pick_daily_questions

BANK = load_bank()
TOPICS = ["linux", "sql", "behavioural"]


def ids(questions):
    return [q["id"] for q in questions]


def test_picks_five_questions_from_matched_topics_only():
    picked = pick_daily_questions(BANK, TOPICS, date(2026, 10, 20), job_id="job-1")

    assert len(picked) == 5
    assert all(q["topic"] in TOPICS for q in picked)


def test_same_day_gives_same_questions():
    first = pick_daily_questions(BANK, TOPICS, date(2026, 10, 20), job_id="job-1")
    second = pick_daily_questions(BANK, TOPICS, date(2026, 10, 20), job_id="job-1")

    assert ids(first) == ids(second)


def test_next_day_gives_different_questions():
    today = pick_daily_questions(BANK, TOPICS, date(2026, 10, 20), job_id="job-1")
    tomorrow = pick_daily_questions(BANK, TOPICS, date(2026, 10, 21), job_id="job-1")

    assert ids(today) != ids(tomorrow)


def test_wrong_answers_come_back_first():
    history = {"sql-04": {"last_correct": False, "correct_streak": 0}}

    picked = pick_daily_questions(BANK, TOPICS, date(2026, 10, 20), history=history)

    assert picked[0]["id"] == "sql-04"


def test_mastered_questions_wait_while_others_remain():
    history = {"linux-01": {"last_correct": True, "correct_streak": 3}}

    picked = pick_daily_questions(BANK, TOPICS, date(2026, 10, 20), history=history)

    assert "linux-01" not in ids(picked)


def test_small_topic_returns_what_it_has():
    picked = pick_daily_questions(BANK, ["docker"], date(2026, 10, 20), count=10)

    assert len(picked) == 5