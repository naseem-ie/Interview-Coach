"""Tests for saving progress. Each test gets a brand-new temporary database."""

from datetime import date, timedelta

import pytest

from progress import (
    complete_challenge, connect, level_for, question_history, readiness,
    record_answer, streak, total_xp,
)

TODAY = date(2026, 10, 20)


@pytest.fixture
def conn(tmp_path):
    """A fresh database in a temporary folder, deleted after the test."""
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


def q(question_id, topic="linux"):
    return {"id": question_id, "topic": topic}


def test_xp_counts_correct_answers_and_finished_challenges(conn):
    record_answer(conn, TODAY, "job-1", q("linux-01"), True)
    record_answer(conn, TODAY, "job-1", q("linux-02"), False)
    record_answer(conn, TODAY, "job-1", q("linux-03"), True)
    complete_challenge(conn, TODAY, "job-1")
    complete_challenge(conn, TODAY, "job-1")  # finishing twice only counts once

    assert total_xp(conn) == 2 * 10 + 20


def test_levels():
    assert level_for(0) == (1, "Rookie", 0)
    assert level_for(150) == (2, "Learner", 50)
    assert level_for(5000)[1] == "Interview-Ready"


def test_history_tracks_latest_answer_and_run_of_correct(conn):
    record_answer(conn, TODAY, "job-1", q("sql-01"), True)
    record_answer(conn, TODAY, "job-1", q("sql-01"), True)
    record_answer(conn, TODAY, "job-1", q("sql-02"), True)
    record_answer(conn, TODAY, "job-1", q("sql-02"), False)

    history = question_history(conn)

    assert history["sql-01"] == {"last_correct": True, "correct_streak": 2}
    assert history["sql-02"] == {"last_correct": False, "correct_streak": 0}


def test_streak_counts_consecutive_days(conn):
    for days_ago in [0, 1, 2, 4]:
        complete_challenge(conn, TODAY - timedelta(days=days_ago), "job-1")

    assert streak(conn, TODAY) == 3


def test_streak_survives_until_end_of_today(conn):
    complete_challenge(conn, TODAY - timedelta(days=1), "job-1")

    assert streak(conn, TODAY) == 1


def test_streak_resets_after_a_missed_day(conn):
    complete_challenge(conn, TODAY - timedelta(days=2), "job-1")

    assert streak(conn, TODAY) == 0


def test_readiness_counts_mastered_topics(conn):
    for n in range(1, 4):
        record_answer(conn, TODAY, "job-1", q(f"linux-0{n}", "linux"), True)
    record_answer(conn, TODAY, "job-1", q("sql-01", "sql"), True)

    # linux mastered (3 of 3 right); sql not yet (only 1 answered); docker untouched
    assert readiness(conn, ["linux", "sql", "docker"]) == 33