"""Tests for aptitude questions. Generated questions are checked across many random seeds."""

import random
import re
from datetime import date

import pytest

from aptitude import GENERATORS, daily_aptitude, generate
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

    assert set(q) == {"id", "topic", "question", "options", "answer", "explanation"}
    assert q["topic"] == "numerical"
