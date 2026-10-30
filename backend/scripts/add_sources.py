"""
Adds new company sources to the respective catalogs.

Iterates over the configured NEW_SOURCES dictionary, generates source
metadata for each company, checks for existing entries to prevent
duplicates, and appends new sources to the corresponding JSON catalog.

Only writes changes to a catalog if new sources were added.

NOTE: Run from backend/ folder.
"""

import json
import re
from pathlib import Path

# ==============================
# CONFIGURATION
# ==============================

NEW_SOURCES = {
    "ashby": ["abc", "abc-def"],
    "greenhouse": ["abc", "abc-def"]
}

# ==============================
# GENERATION RULES
# ==============================

def generate_source(company):
    def generate_name(company):
        return company.lower().strip()

    def generate_company(company):
        company = company.lower().strip()
        company = company.replace("-", " ")
        return company.title()

    def generate_board_name(company):
        return company.lower().strip()

    def generate_homepage(company):
        return f"https://{company.lower().strip()}.com/careers"

    return {
        "name": generate_name(company),
        "company": generate_company(company),
        "board_name": generate_board_name(company),
        "homepage": generate_homepage(company)
    }

# ==============================
# MAIN
# ==============================

def main():
    for catalog, new_sources in NEW_SOURCES.items():

        json_file = f"jobsentry/sources/catalogs/{catalog}-sources.json"
        path = Path(json_file)

        if not path.exists():
            print(f"File not found: {json_file}")
            continue

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if "sources" not in data:
            data["sources"] = []

        existing_names = {
            source["name"].lower()
            for source in data["sources"]
            if "name" in source
        }

        added = []

        for company in new_sources:
            source = generate_source(company)

            if source["name"].lower() in existing_names:
                print(f"Skipping duplicate in {catalog}: {company}")
                continue

            data["sources"].append(source)
            existing_names.add(source["name"].lower())
            added.append(company)

        if added:
            with path.open("w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
                file.write("\n")

        print(f"\n{catalog.upper()} - Added {len(added)} sources:")

        for company in added:
            print(f"  + {company}")

if __name__ == "__main__":
    main()
