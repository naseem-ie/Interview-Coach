"""Fetch job applications from the Notion Applications database and print them."""

import os

from dotenv import load_dotenv
from notion_client import Client
from notion_client.helpers import collect_paginated_api

# 1. Load the secrets from .env
load_dotenv()
token = os.getenv("NOTION_API_KEY")
database_id = os.getenv("NOTION_DATABASE_ID")

if not token or not database_id:
    raise SystemExit("Missing NOTION_API_KEY or NOTION_DATABASE_ID in .env")

# 2. Connect to Notion
notion = Client(auth=token)

# 3. Find the data source inside the database (where the rows live)
database = notion.databases.retrieve(database_id=database_id)
data_source_id = database["data_sources"][0]["id"]

# 4. Get every row (one row = one job)
pages = collect_paginated_api(notion.data_sources.query, data_source_id=data_source_id)


def text_of(prop):
    """Turn a Notion title or text property into a plain string."""
    parts = prop.get("title") or prop.get("rich_text") or []
    return "".join(part["plain_text"] for part in parts)


# 5. Print one line per job
print(f"Found {len(pages)} jobs\n")
for page in pages:
    props = page["properties"]
    company = text_of(props["Company"])
    role = text_of(props["Role"])
    status = props["Status"]["select"]["name"] if props["Status"]["select"] else "No status"
    print(f"{company} | {role} | {status}")