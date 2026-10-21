"""Tests for the AI coach, using a fake AI so they run instantly without Ollama."""

import json
from types import SimpleNamespace

import pytest

from coach import CHECKLIST, CoachError, build_messages, parse_feedback, score_answer


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


def reply(met, tips=("Add a number.", "Say what you did.")):
    checklist = {item: item in met for item in CHECKLIST}
    return json.dumps({"checklist": checklist, "strength": "Clear story.", "tips": list(tips)})


def test_score_is_two_points_per_checklist_item():
    feedback = parse_feedback(reply({"situation", "action", "relevance"}))

    assert feedback["score"] == 6
    assert feedback["checklist"]["result"] is False
    assert feedback["strength"] == "Clear story."


def test_missing_items_count_as_not_met_and_tips_are_capped_at_two():
    text = json.dumps({"checklist": {"situation": True}, "strength": "", "tips": ["a", "b", "c"]})

    feedback = parse_feedback(text)

    assert feedback["score"] == 2
    assert feedback["tips"] == ["a", "b"]


def test_invalid_reply_raises_coach_error():
    with pytest.raises(CoachError):
        parse_feedback("Sorry, I cannot help with that")


def test_empty_answer_is_rejected_before_calling_the_ai():
    fake = FakeAI(reply=reply(set()))

    with pytest.raises(ValueError):
        score_answer("Tell me about yourself.", "   ", "Support Engineer", client=fake)
    assert fake.calls == []


def test_score_answer_sends_question_role_and_turns_thinking_off():
    fake = FakeAI(reply=reply(set(CHECKLIST)))

    feedback = score_answer("Tell me about an outage.", "I fixed it.", "SRE", client=fake)

    assert feedback["score"] == 10
    call = fake.calls[0]
    assert call["think"] is False
    assert "SRE" in call["messages"][0]["content"]
    assert "I fixed it." in call["messages"][1]["content"]


def test_ollama_not_running_gives_a_clear_message():
    fake = FakeAI(error=ConnectionError("Failed to connect"))

    with pytest.raises(CoachError, match="Could not reach Ollama"):
        score_answer("Q", "A", "Role", client=fake)


def test_prompt_lists_every_checklist_item():
    messages = build_messages("Q", "A", "Role")

    for item in CHECKLIST:
        assert item in messages[1]["content"]
