"""Print all job applications from Notion (quick check from the terminal)."""

from notion_data import load_jobs

jobs = load_jobs()
print(f"Found {len(jobs)} jobs\n")
for job in jobs:
    print(f"{job['company']} | {job['role']} | {job['status']}")