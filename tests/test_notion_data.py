"""Tests for notion_data.page_to_job, using fake sample data (no Notion needed)."""

from notion_data import page_to_job


def test_reads_filled_in_row():
    fake_page = {
        "id": "page-123",
        "properties": {
            "Company": {"title": [{"plain_text": "Acme"}, {"plain_text": " Ltd"}]},
            "Role": {"rich_text": [{"plain_text": "Support Engineer"}]},
            "Status": {"select": {"name": "Applied"}},
            "Applied date": {"date": {"start": "2026-10-01"}},
            "Match score": {"number": 7},
            "Skill gaps": {"rich_text": [{"plain_text": "SQL; Linux"}]},
            "Job link": {"url": "https://example.com/job"},
        },
    }

    job = page_to_job(fake_page)

    assert job["company"] == "Acme Ltd"
    assert job["role"] == "Support Engineer"
    assert job["status"] == "Applied"
    assert job["applied_date"] == "2026-10-01"
    assert job["match_score"] == 7
    assert job["skill_gaps"] == "SQL; Linux"
    assert job["job_link"] == "https://example.com/job"


def test_empty_row_gives_safe_defaults():
    fake_page = {
        "id": "page-456",
        "properties": {
            "Status": {"select": None},
            "Applied date": {"date": None},
        },
    }

    job = page_to_job(fake_page)

    assert job["company"] == ""
    assert job["status"] == ""
    assert job["applied_date"] == ""
    assert job["match_score"] is None
    assert job["job_link"] == ""