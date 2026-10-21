"""Tests for saving progress. Each test gets a brand-new temporary database."""

from datetime import date, timedelta

import pytest

from progress import (
    answers_for_day, complete_challenge, connect, job_summary, level_for, mock_tests, question_history,
    readiness, recent_accuracy, record_answer, record_mock_test, streak, topic_stats, total_xp,
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


def test_readiness_is_share_of_topic_questions_right(conn):
    sizes = {"linux": 6, "sql": 6, "docker": 5}
    for n in range(1, 4):
        record_answer(conn, TODAY, "job-1", q(f"linux-0{n}", "linux"), True)
    record_answer(conn, TODAY, "job-1", q("sql-01", "sql"), False)

    # 3 right out of 17 questions in these topics
    assert readiness(conn, ["linux", "sql", "docker"], sizes) == round(100 * 3 / 17)


def test_readiness_uses_latest_answer(conn):
    sizes = {"sql": 2}
    record_answer(conn, TODAY, "job-1", q("sql-01", "sql"), False)
    record_answer(conn, TODAY, "job-1", q("sql-01", "sql"), True)

    assert readiness(conn, ["sql"], sizes) == 50


def test_history_can_ignore_todays_answers(conn):
    record_answer(conn, TODAY - timedelta(days=1), "job-1", q("sql-01"), True)
    record_answer(conn, TODAY, "job-1", q("sql-02"), False)

    history = question_history(conn, before=TODAY)

    assert "sql-01" in history
    assert "sql-02" not in history


def test_answers_for_day_only_returns_that_day_and_job(conn):
    record_answer(conn, TODAY, "job-1", q("linux-01"), True)
    record_answer(conn, TODAY, "job-2", q("linux-02"), True)
    record_answer(conn, TODAY - timedelta(days=1), "job-1", q("linux-03"), False)

    assert answers_for_day(conn, TODAY, "job-1") == {"linux-01": True}


def test_topic_stats_labels_each_topic(conn):
    sizes = {"linux": 3, "sql": 6, "docker": 5}
    for n in range(1, 4):
        record_answer(conn, TODAY, "job-1", q(f"linux-0{n}", "linux"), True)
    record_answer(conn, TODAY, "job-1", q("sql-01", "sql"), False)

    stats = topic_stats(conn, ["linux", "sql", "docker"], sizes)

    assert stats["linux"]["status"] == "Mastered"
    assert stats["linux"]["percent"] == 100
    assert stats["sql"] == {"total": 6, "answered": 1, "correct": 0, "percent": 0, "status": "Learning"}
    assert stats["docker"]["status"] == "Not started"


def test_job_summary_counts_only_that_job(conn):
    record_answer(conn, TODAY, "job-1:technical", q("linux-01"), True)
    record_answer(conn, TODAY, "job-1:behavioural", q("beh-01", "behavioural"), False)
    record_answer(conn, TODAY, "job-2:technical", q("linux-02"), True)
    complete_challenge(conn, TODAY, "job-1:technical")

    summary = job_summary(conn, "job-1")

    assert summary == {"answered": 2, "correct": 1, "accuracy": 50, "challenges": 1, "xp": 30}


def test_recent_accuracy_uses_only_the_latest_answers(conn):
    record_answer(conn, TODAY, "aptitude", q("apt-1", "numerical"), False)
    for n in range(3):
        record_answer(conn, TODAY, "aptitude", q(f"apt-{n + 2}", "logical"), True)
    record_answer(conn, TODAY, "job-1:technical", q("linux-01"), False)

    assert recent_accuracy(conn, "aptitude", last=3) == 100
    assert recent_accuracy(conn, "aptitude") == 75
    assert recent_accuracy(conn, "nothing-yet") == 0


def test_mock_test_results_are_saved_newest_first(conn):
    record_mock_test(conn, TODAY, "speed", 12, 20, 25, 480)
    record_mock_test(conn, TODAY, "speed", 15, 22, 25, 470)
    record_mock_test(conn, TODAY, "numerical", 9, 12, 12, 600)

    results = mock_tests(conn, "speed")

    assert [r["right"] for r in results] == [15, 12]
    assert results[0] == {"day": "2026-10-20", "right": 15, "answered": 22, "total": 25, "seconds": 470}


def test_recent_accuracy_includes_extra_practice_and_mock_answers(conn):
    record_answer(conn, TODAY, "aptitude", q("apt-1", "numerical"), True)
    record_answer(conn, TODAY, "aptitude:extra", q("extra-1", "logical"), False)
    record_answer(conn, TODAY, "aptitude:mock", q("mock-1", "logical"), True)
    record_answer(conn, TODAY, "aptitudeX", q("other", "logical"), False)

    assert recent_accuracy(conn, "aptitude") == 67


# ---------- AI questions ----------

from progress import ai_questions, report_ai_question, save_ai_questions


def ai_q(question_id, skill="PowerShell basics"):
    return {"id": question_id, "topic": "ai", "skill": skill, "question": "Q?",
            "options": ["a", "b", "c", "d"], "answer": 0, "explanation": "E."}


def test_ai_questions_are_saved_once_and_shared_by_skill(conn):
    assert save_ai_questions(conn, TODAY, "job-1", "PowerShell basics", [ai_q("ai-1"), ai_q("ai-2")]) == 2
    assert save_ai_questions(conn, TODAY, "job-1", "PowerShell basics", [ai_q("ai-1")]) == 0

    # Another job with the same skill gap (any capitals) sees them too
    assert [q["id"] for q in ai_questions(conn, ["powershell BASICS"], "job-2")] == ["ai-1", "ai-2"]
    assert ai_questions(conn, ["Agile"], "job-2") == []


def test_extra_topics_belong_to_the_job_that_added_them(conn):
    save_ai_questions(conn, TODAY, "job-1", "SAP Ariba", [ai_q("ai-9", "SAP Ariba")])

    assert len(ai_questions(conn, [], "job-1")) == 1
    assert ai_questions(conn, [], "job-2") == []


def test_reported_ai_questions_are_hidden(conn):
    save_ai_questions(conn, TODAY, "job-1", "PowerShell basics", [ai_q("ai-1"), ai_q("ai-2")])
    report_ai_question(conn, "ai-1")

    assert [q["id"] for q in ai_questions(conn, ["PowerShell basics"], "job-1")] == ["ai-2"]


def test_ai_practice_counts_towards_the_job(conn):
    record_answer(conn, TODAY, "job-1:ai", ai_q("ai-1"), True)
    assert job_summary(conn, "job-1")["correct"] == 1


def test_ai_skill_stats_group_by_skill_and_use_the_latest_answer(conn):
    pool = [ai_q("ai-1"), ai_q("ai-2"), ai_q("ai-3", "Agile")]
    record_answer(conn, TODAY, "job-1:ai", ai_q("ai-1"), False)
    record_answer(conn, TODAY, "job-1:ai", ai_q("ai-1"), True)

    from progress import ai_skill_stats
    stats = ai_skill_stats(conn, pool)

    assert stats["PowerShell basics"]["total"] == 2
    assert stats["PowerShell basics"]["correct"] == 1
    assert stats["PowerShell basics"]["status"] == "Learning"
    assert stats["Agile"]["status"] == "Not started"


def test_technical_readiness_combines_bank_topics_and_ai_skills():
    from progress import combined_readiness

    bank = {"web": {"total": 8, "correct": 0}}
    ai = {"Agile": {"total": 5, "correct": 4}, "ERP": {"total": 7, "correct": 6}}

    assert combined_readiness(bank, ai) == 50  # 10 right of 20
    assert combined_readiness({}, {}) == 0


# ---------- Mock interviews ----------

from progress import interviews, save_interview


def test_interviews_are_saved_with_answers_and_skips_left_out(conn):
    feedback = {"checklist": {}, "strength": "Clear.", "tips": ["Add a number."]}
    results = [
        {"question": "Q1", "answer": "My answer", "score": 6, "feedback": feedback},
        {"question": "Q2", "answer": "", "score": None, "feedback": None},
    ]
    save_interview(conn, TODAY, "job-1", results, 6.0)
    save_interview(conn, TODAY, "job-1", results[:1], 8.0)

    past = interviews(conn, "job-1")
    assert [p["average"] for p in past] == [8.0, 6.0]  # newest first
    assert past[1]["answered"] == 1
    assert past[1]["answers"][0]["feedback"]["tips"] == ["Add a number."]
    assert interviews(conn, "job-2") == []
