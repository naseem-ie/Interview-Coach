"""Tests for the AI question writer, using a fake AI so they run instantly without Ollama."""

import json
import random
from types import SimpleNamespace

import httpx
import pytest

from coach import CoachError
from question_writer import AI_TOPIC, parse_questions, question_id, write_questions


class FakeAI:
    """Pretends to be Ollama: returns a fixed reply and remembers what it was sent."""

    def __init__(self, reply=None, error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(message=SimpleNamespace(content=self.reply))


def item(question="What does PowerShell's Get-Help do?", correct="Shows help for a command",
         wrong=("Deletes a file", "Restarts the PC", "Opens Notepad"), explanation="It shows help."):
    return {"question": question, "correct_answer": correct, "wrong_answers": list(wrong), "explanation": explanation}


def reply(*items):
    return json.dumps({"questions": list(items)})


def test_a_good_question_is_turned_into_bank_format():
    [q] = parse_questions(reply(item()), "PowerShell basics", random.Random(1))

    assert q["topic"] == AI_TOPIC
    assert q["skill"] == "PowerShell basics"
    assert len(q["options"]) == 4
    assert q["options"][q["answer"]] == "Shows help for a command"
    assert q["id"] == question_id("PowerShell basics", q["question"])


def test_correct_answer_position_is_shuffled():
    positions = {
        parse_questions(reply(item()), "x", random.Random(seed))[0]["answer"] for seed in range(30)
    }
    assert len(positions) > 1


@pytest.mark.parametrize("bad", [
    item(question=""),
    item(correct=""),
    item(wrong=("A", "B")),
    item(wrong=("Shows help for a command", "A", "B")),
    item(wrong=("A", "a", "B")),
])
def test_badly_formed_questions_are_dropped(bad):
    assert parse_questions(reply(bad), "x") == []


def test_duplicate_questions_are_dropped():
    assert len(parse_questions(reply(item(), item()), "x")) == 1


def test_extra_wrong_answers_are_cut_to_three():
    [q] = parse_questions(reply(item(wrong=("A", "B", "C", "D"))), "x")
    assert len(q["options"]) == 4


def test_invalid_json_raises_a_friendly_error():
    with pytest.raises(CoachError):
        parse_questions("not json", "x")


def test_write_questions_sends_the_skill_and_role_and_limits_the_count():
    ai = FakeAI(reply(*[item(question=f"Question {n}?") for n in range(7)]))

    questions = write_questions("PRINCE2 basics", "Support Analyst", count=5, client=ai)

    assert len(questions) == 5
    sent = ai.calls[0]
    assert "PRINCE2 basics" in sent["messages"][1]["content"]
    assert "Support Analyst" in sent["messages"][1]["content"]
    assert sent["think"] is False


def test_write_questions_explains_when_ollama_is_not_running():
    ai = FakeAI(error=httpx.ConnectError("refused"))
    with pytest.raises(CoachError, match="Could not reach Ollama"):
        write_questions("x", "y", client=ai)
