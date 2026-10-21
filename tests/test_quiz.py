"""Tests for the question bank and topic matching."""

from quiz import load_bank, split_topics, topic_sizes, topics_for_job


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


def test_split_topics_separates_behavioural():
    technical, behavioural = split_topics(["python", "linux", "behavioural"])

    assert technical == ["python", "linux"]
    assert behavioural == ["behavioural"]


def test_split_topics_uses_core_topics_when_no_skill_gaps():
    technical, _ = split_topics(["behavioural"])

    assert technical == ["itil", "linux", "sql"]


def test_topic_sizes_counts_questions_per_topic():
    bank = {"questions": [{"topic": "sql"}, {"topic": "sql"}, {"topic": "linux"}]}

    assert topic_sizes(bank) == {"sql": 2, "linux": 1}


def test_skill_gap_items_split_on_semicolons_and_new_lines():
    from quiz import skill_gap_items

    assert skill_gap_items("SQL; PowerShell basics\nAgile ;  ") == ["SQL", "PowerShell basics", "Agile"]
    assert skill_gap_items(None) == []


def test_uncovered_gaps_are_the_ones_no_topic_matches():
    from quiz import load_bank, uncovered_gaps

    topics = load_bank()["topics"]
    gaps = "SQL Server querying; PowerShell basics; PRINCE2 or Agile concepts; Zendesk"

    assert uncovered_gaps(gaps, topics) == ["PowerShell basics", "PRINCE2 or Agile concepts"]
