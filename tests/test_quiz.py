"""Tests for the question bank and topic matching."""

from quiz import load_bank, topics_for_job


def test_question_bank_is_valid():
    bank = load_bank()
    seen_ids = set()
    for q in bank["questions"]:
        assert q["topic"] in bank["topics"], q["id"]
        assert len(q["options"]) == 4, q["id"]
        assert 0 <= q["answer"] < 4, q["id"]
        assert q["id"] not in seen_ids, q["id"]
        seen_ids.add(q["id"])


def test_skill_gaps_map_to_topics():
    topics = load_bank()["topics"]
    gaps = "Python scripting; Linux and Bash; Dynatrace or another APM; CI/CD (Jenkins)"

    result = topics_for_job(gaps, topics)

    assert "python" in result
    assert "linux" in result
    assert "monitoring" in result
    assert "cicd" in result
    assert "sql" not in result


def test_short_keywords_do_not_match_inside_words():
    topics = load_bank()["topics"]

    result = topics_for_job("Decision making with stakeholders", topics)

    assert result == ["behavioural"]


def test_empty_skill_gaps_still_give_behavioural():
    topics = load_bank()["topics"]

    assert topics_for_job("", topics) == ["behavioural"]