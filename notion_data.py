"""Read job applications from the Notion Applications database."""

import os

from dotenv import load_dotenv
from notion_client import Client
from notion_client.helpers import collect_paginated_api


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


def load_jobs():
    """Fetch every job from Notion, sorted by company name."""
    load_dotenv()
    token = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not token or not database_id:
        raise RuntimeError("Missing NOTION_API_KEY or NOTION_DATABASE_ID in .env")

    notion = Client(auth=token)
    database = notion.databases.retrieve(database_id=database_id)
    data_source_id = database["data_sources"][0]["id"]
    pages = collect_paginated_api(notion.data_sources.query, data_source_id=data_source_id)

    jobs = [page_to_job(page) for page in pages]
    return sorted(jobs, key=lambda job: job["company"].lower())