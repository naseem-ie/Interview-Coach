"""Tests for building mock interviews and summarising the scores."""

import random

from interview import BEHAVIOURAL, QUESTIONS_PER_INTERVIEW, build_interview, summarise


def job(skill_gaps="PowerShell basics; PRINCE2 or Agile basics; SQL", role="Support Analyst"):
    return {"skill_gaps": skill_gaps, "role": role}


def test_interview_has_five_different_questions():
    questions = build_interview(job(), random.Random(1))

    assert len(questions) == QUESTIONS_PER_INTERVIEW
    assert len(set(questions)) == QUESTIONS_PER_INTERVIEW


def test_two_questions_come_from_the_jobs_skill_gaps_and_it_starts_behavioural():
    questions = build_interview(job(), random.Random(2))

    about_gaps = [q for q in questions if any(s in q for s in ["PowerShell", "PRINCE2", "SQL"])]
    assert len(about_gaps) == 2
    assert questions[0] in BEHAVIOURAL


def test_jobs_without_skill_gaps_get_questions_about_the_role():
    questions = build_interview(job(skill_gaps=None), random.Random(3))

    assert sum("Support Analyst" in q for q in questions) == 2


def test_different_interviews_ask_different_questions():
    sets = {tuple(build_interview(job(), random.Random(seed))) for seed in range(10)}
    assert len(sets) > 1


def test_summary_ignores_skipped_questions():
    results = [
        {"question": "A", "score": 4},
        {"question": "B", "score": None},
        {"question": "C", "score": 8},
    ]
    summary = summarise(results)

    assert summary["answered"] == 2
    assert summary["average"] == 6.0
    assert summary["best"]["question"] == "C"
    assert summary["weakest"]["question"] == "A"


def test_summary_has_no_strongest_or_weakest_when_scores_are_equal():
    summary = summarise([{"question": "A", "score": 6}, {"question": "B", "score": 6}])

    assert summary["average"] == 6.0
    assert summary["best"] is None and summary["weakest"] is None


def test_summary_of_nothing_answered():
    assert summarise([{"question": "A", "score": None}])["answered"] == 0
