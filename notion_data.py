"""Read job applications from the Notion Applications database, and update a job's status."""

import os

from dotenv import load_dotenv
from notion_client import Client
from notion_client.helpers import collect_paginated_api

STATUSES = [
    "To apply", "Recruiter contact", "Applied", "Screening call", "Interview",
    "Interviewed - awaiting", "Offer", "Rejected", "Withdrawn", "No reply - inactive",
]


def _text(prop):
    """Title or text property -> plain string."""
    parts = prop.get("title") or prop.get("rich_text") or []
    return "".join(part["plain_text"] for part in parts)


def _select(prop):
    """Select property -> option name, or empty string."""
    option = prop.get("select")
    return option["name"] if option else ""


def _date(prop):
    """Date property -> 'YYYY-MM-DD', or empty string."""
    value = prop.get("date")
    return value["start"] if value else ""


def page_to_job(page):
    """Turn one Notion row into a simple dictionary."""
    p = page["properties"]
    return {
        "id": page["id"],
        "company": _text(p.get("Company", {})),
        "role": _text(p.get("Role", {})),
        "status": _select(p.get("Status", {})),
        "source": _select(p.get("Source", {})),
        "applied_date": _date(p.get("Applied date", {})),
        "follow_up_due": _date(p.get("Follow-up due", {})),
        "next_action": _text(p.get("Next action", {})),
        "prep_status": _select(p.get("Prep status", {})),
        "skill_gaps": _text(p.get("Skill gaps", {})),
        "match_score": p.get("Match score", {}).get("number"),
        "recruiter": _text(p.get("Recruiter", {})),
        "salary": _text(p.get("Salary", {})),
        "job_link": p.get("Job link", {}).get("url") or "",
        "prep_page": p.get("Prep page", {}).get("url") or "",
        "notes": _text(p.get("Notes", {})),
    }


def _settings():
    """Read the token and database id from .env."""
    load_dotenv()
    token = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not token or not database_id:
        raise RuntimeError("Missing NOTION_API_KEY or NOTION_DATABASE_ID in .env")
    return token, database_id


def load_jobs():
    """Fetch every job from Notion, sorted by company name."""
    token, database_id = _settings()
    notion = Client(auth=token)
    database = notion.databases.retrieve(database_id=database_id)
    data_source_id = database["data_sources"][0]["id"]
    pages = collect_paginated_api(notion.data_sources.query, data_source_id=data_source_id)

    jobs = [page_to_job(page) for page in pages]
    return sorted(jobs, key=lambda job: job["company"].lower())


PREFIXES = {
    "heading_1": "### ", "heading_2": "### ", "heading_3": "#### ",
    "bulleted_list_item": "- ", "numbered_list_item": "1. ", "to_do": "- ", "quote": "> ",
}


def blocks_to_markdown(blocks):
    """Turn a Notion page's text blocks into simple Markdown (other block types are skipped)."""
    lines = []
    for block in blocks:
        kind = block.get("type", "")
        rich_text = block.get(kind, {}).get("rich_text")
        if rich_text is None:
            continue
        text = "".join(part["plain_text"] for part in rich_text).strip()
        if text:
            lines.append(PREFIXES.get(kind, "") + text)
    return "\n\n".join(lines)


def load_job_description(page_id):
    """Read the text written inside a job's Notion page (the job advert)."""
    token, _ = _settings()
    notion = Client(auth=token)
    blocks = collect_paginated_api(notion.blocks.children.list, block_id=page_id)
    return blocks_to_markdown(blocks)


def update_status(page_id, status, notion=None):
    """Change a job's Status in Notion. Needs 'Update content' on the Notion connection."""
    if status not in STATUSES:
        raise ValueError(f"Unknown status: {status}")
    if notion is None:
        token, _ = _settings()
        notion = Client(auth=token)
    notion.pages.update(page_id=page_id, properties={"Status": {"select": {"name": status}}})
