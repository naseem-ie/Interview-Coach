"""Demo mode: run the app with made-up sample jobs instead of your Notion database.

Used for screenshots and for anyone who clones the repo without a Notion account.
Turn it on with DEMO_MODE=1. It also switches on by itself when no Notion key is set.
Demo progress is saved in demo.db, so it never mixes with your real progress.db.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

SAMPLE_FILE = Path(__file__).parent / "data" / "sample_jobs.json"
DEMO_DB = Path(__file__).parent / "demo.db"


def demo_mode():
    """True if DEMO_MODE is set, or if there is no Notion key to load real jobs with."""
    load_dotenv()
    if os.getenv("DEMO_MODE", "").strip().lower() in ("1", "true", "yes"):
        return True
    return not os.getenv("NOTION_API_KEY")


def load_sample_jobs(path=SAMPLE_FILE):
    """The sample jobs, sorted by company, in the same format as Notion jobs."""
    with open(path, encoding="utf-8") as f:
        jobs = json.load(f)["jobs"]
    return sorted(jobs, key=lambda job: job["company"].lower())


def sample_description(job_id, path=SAMPLE_FILE):
    """The job advert for a sample job."""
    return next((j["description"] for j in load_sample_jobs(path) if j["id"] == job_id), "")
