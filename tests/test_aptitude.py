"""Tests for aptitude questions. Generated questions are checked across many random seeds."""

import random
import re
from datetime import date

import pytest

from aptitude import (
    GENERATORS, MOCK_FORMATS, build_mock, daily_aptitude, extra_question, generate, score_mock,
)
from quiz import load_bank

BANK = load_bank()
ALL_GENERATORS = [g for gens in GENERATORS.values() for g in gens]


@pytest.mark.parametrize("make", ALL_GENERATORS, ids=lambda g: g.__name__)
def test_every_generator_makes_valid_questions(make):
    for seed in range(300):
        question, options, answer, explanation = make(random.Random(seed))
        assert len(options) == 4
        assert len(set(options)) == 4, (seed, options)
        assert 0 <= answer < 4
        assert question and explanation


def numbers_in(text):
    return [int(n) for n in re.findall(r"-?\d+", text)]


@pytest.mark.parametrize("seed", range(100))
def test_sequence_answers_follow_the_rule(seed):
    rng = random.Random(seed)
    for topic_maker in GENERATORS["logical"]:
        question, options, answer, _ = topic_maker(rng)
        terms = numbers_in(question)
        rules = {
            "arithmetic_sequence": lambda t: t[-1] + (t[1] - t[0]),
            "geometric_sequence": lambda t: t[-1] * (t[1] // t[0]),
            "alternating_sequence": lambda t: t[-1] + (t[-2] - t[-3]),
            "fibonacci_sequence": lambda t: t[-1] + t[-2],
            "squares_sequence": lambda t: t[-1] + (t[-1] - t[-2]) + 2,
        }
        expected = rules[topic_maker.__name__](terms)
        assert options[answer] == str(expected), (topic_maker.__name__, question, options)


def test_daily_set_is_the_same_all_day_and_mixes_topics():
    first = daily_aptitude(BANK, date(2026, 10, 21))
    again = daily_aptitude(BANK, date(2026, 10, 21))
    tomorrow = daily_aptitude(BANK, date(2026, 10, 22))

    assert [q["question"] for q in first] == [q["question"] for q in again]
    assert [q["question"] for q in first] != [q["question"] for q in tomorrow]
    assert [q["topic"] for q in first] == ["numerical"] * 2 + ["logical"] * 2 + ["verbal"] * 2
    assert len({q["id"] for q in first}) == 6


def test_generated_question_has_bank_format():
    q = generate("numerical", random.Random(1), "apt-test")

    assert set(q) == {"id", "topic", "kind", "question", "options", "answer", "explanation"}
    assert q["topic"] == "numerical"


@pytest.mark.parametrize("format_key", list(MOCK_FORMATS))
def test_mock_test_has_the_right_mix_and_unique_ids(format_key):
    questions = build_mock(BANK, format_key, random.Random(5))
    mix = MOCK_FORMATS[format_key]["mix"]

    assert len(questions) == sum(mix.values())
    assert len({q["id"] for q in questions}) == len(questions)
    for topic, count in mix.items():
        assert sum(q["topic"] == topic for q in questions) == count


def test_two_mock_tests_are_different():
    first = build_mock(BANK, "numerical", random.Random(1))
    second = build_mock(BANK, "numerical", random.Random(2))

    assert [q["question"] for q in first] != [q["question"] for q in second]


def test_score_mock_counts_right_answered_and_by_topic():
    questions = [
        {"id": "a", "topic": "numerical", "answer": 0},
        {"id": "b", "topic": "numerical", "answer": 1},
        {"id": "c", "topic": "logical", "answer": 2},
    ]

    result = score_mock(questions, {"a": 0, "b": 3})

    assert result["right"] == 1
    assert result["answered"] == 2
    assert result["total"] == 3
    assert result["by_topic"] == {
        "numerical": {"right": 1, "total": 2},
        "logical": {"right": 0, "total": 1},
    }


def test_extra_questions_are_valid():
    rng = random.Random(3)
    for _ in range(50):
        q = extra_question(BANK, rng)
        assert q["topic"] in ("numerical", "logical", "verbal")
        assert len(set(q["options"])) == 4


# ---------- Tips and tricks ----------

from aptitude import GENERATORS
from aptitude_tips import GUIDE, TIPS, tip_for


def test_every_generated_question_has_a_tip():
    rng = random.Random(1)
    for topic, makers in GENERATORS.items():
        for make in makers:
            assert make.__name__ in TIPS, f"No tip for {make.__name__}"
        for n in range(50):
            question = generate(topic, rng, f"t-{n}")
            assert tip_for(question) is not None


def test_bank_verbal_questions_get_the_verbal_tip():
    bank = load_bank()
    verbal = [q for q in bank["questions"] if q["topic"] == "verbal"]
    assert verbal
    for q in verbal:
        assert tip_for(q) == TIPS["verbal"]


def test_tips_and_guide_are_filled_in():
    for tip in TIPS.values():
        assert tip["title"] and tip["trick"] and tip["example"]
    assert len(GUIDE) >= 4
    for title, body in GUIDE:
        assert title and body.strip()
