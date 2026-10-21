"""Tests for notion_data, using fake sample data (no Notion needed)."""

import pytest

from notion_data import blocks_to_markdown, page_to_job, update_status


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


def text_block(kind, text):
    return {"type": kind, kind: {"rich_text": [{"plain_text": text}]}}


def test_blocks_to_markdown_keeps_headings_and_bullets():
    blocks = [
        text_block("heading_2", "About the role"),
        text_block("paragraph", "Support enterprise customers."),
        text_block("bulleted_list_item", "SQL"),
        text_block("paragraph", ""),
        {"type": "divider", "divider": {}},
    ]

    result = blocks_to_markdown(blocks)

    assert result == "### About the role\n\nSupport enterprise customers.\n\n- SQL"


class FakeNotion:
    """Records the update call instead of talking to Notion."""

    def __init__(self):
        self.calls = []
        self.pages = self

    def update(self, **kwargs):
        self.calls.append(kwargs)


def test_update_status_sends_the_new_status():
    fake = FakeNotion()

    update_status("page-1", "Interview", notion=fake)

    assert fake.calls == [
        {"page_id": "page-1", "properties": {"Status": {"select": {"name": "Interview"}}}}
    ]


def test_update_status_rejects_unknown_status():
    with pytest.raises(ValueError):
        update_status("page-1", "Hired yesterday", notion=FakeNotion())
