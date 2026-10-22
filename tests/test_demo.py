"""Tests for demo mode and the made-up sample jobs."""

from demo import demo_mode, load_sample_jobs, sample_description
from quiz import load_bank, uncovered_gaps

EXPECTED_KEYS = {
    "id", "company", "role", "status", "source", "applied_date", "follow_up_due", "next_action", "prep_status",
    "skill_gaps", "match_score", "recruiter", "salary", "job_link", "prep_page", "notes", "description",
}


def test_sample_jobs_look_like_notion_jobs():
    jobs = load_sample_jobs()

    assert len(jobs) >= 3
    for job in jobs:
        assert set(job) == EXPECTED_KEYS
        assert job["id"].startswith("demo-")
        assert sample_description(job["id"])


def test_sample_jobs_show_off_the_features():
    jobs = load_sample_jobs()
    topics = load_bank()["topics"]

    assert any(uncovered_gaps(j["skill_gaps"], topics) for j in jobs)  # AI practice has work to do
    assert any(not j["skill_gaps"] for j in jobs)  # the core-topics fallback is shown too


def test_demo_mode_switch(monkeypatch):
    monkeypatch.setattr("demo.load_dotenv", lambda: None)  # ignore your real .env
    monkeypatch.setenv("NOTION_API_KEY", "secret")
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert demo_mode() is False

    monkeypatch.setenv("DEMO_MODE", "1")
    assert demo_mode() is True

    monkeypatch.delenv("DEMO_MODE")
    monkeypatch.delenv("NOTION_API_KEY")
    assert demo_mode() is True  # no Notion key: fall back to the sample jobs
