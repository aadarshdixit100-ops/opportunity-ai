"""
scripts/ingest_github.py — OPTIONAL discovery script.

Fetches public GitHub repositories that look like student programmes and writes
them to data/ingested_cache.json with verification_status "fetched".

The Streamlit app NEVER calls the network. It only reads the cache file, and
handles a missing or corrupt cache silently. Run this once before a demo if you
want the "fetched" rows to appear.

    python3 scripts/ingest_github.py --source github --query "student hackathon"
    python3 scripts/ingest_github.py --source github --query "scholarship students" --limit 10

Only endpoints I am confident exist are used:
    GET https://api.github.com/search/repositories
GitHub rate-limits unauthenticated requests to ~10/min, so set GITHUB_TOKEN if
you can. This script is fail-safe: any error leaves the existing cache untouched.

Honesty: a repository is NOT an opportunity with a deadline. Records written here
carry verification_status "fetched" (not human-checked), a null deadline, and the
exact URL that was fetched in source_url.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    print("requests is required: pip install requests", file=sys.stderr)
    raise SystemExit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, "data", "ingested_cache.json")
GITHUB_SEARCH = "https://api.github.com/search/repositories"
TIMEOUT = 10


def _headers() -> Dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "OpportunityAI-ingest"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_github(query: str, limit: int) -> List[Dict[str, Any]]:
    """Return mapped records. Raises on network/HTTP failure (caller handles)."""
    resp = requests.get(GITHUB_SEARCH, headers=_headers(), timeout=TIMEOUT,
                        params={"q": query, "per_page": min(limit, 50), "sort": "stars"})
    if resp.status_code == 403:
        raise RuntimeError("GitHub rate limit hit (403). Set GITHUB_TOKEN and retry.")
    resp.raise_for_status()
    items = resp.json().get("items", [])[:limit]
    stamp = dt.date.today().isoformat()
    out = []
    for i, repo in enumerate(items, start=1):
        out.append({
            "id": f"GH{repo.get('id', i)}",
            "title": repo.get("full_name") or repo.get("name") or "Untitled repository",
            "organization": (repo.get("owner") or {}).get("login") or "unknown",
            "category": "Open Source Program",
            "description": (repo.get("description") or "No description provided.")[:400],
            "required_skills": [], "preferred_skills": [], "interests": ["Open Source"], "tags": ["fetched"],
            "min_cgpa": None, "eligible_years": None, "eligible_degrees": None, "eligible_branches": None,
            "work_mode": "Remote", "location": "Remote", "stipend_or_award": None,
            "deadline": None, "deadline_kind": "unknown", "opens_on": None,
            "demo_deadline_offset_days": None,
            "apply_url": None,
            "source_url": repo.get("html_url"),      # the exact URL fetched
            "last_verified": stamp,
            "verification_status": "fetched",        # NOT human-checked
            "women_only": None, "experience_level": "Beginner",
            "eligibility": ["Auto-ingested from GitHub — not human-checked."],
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="OpportunityAI discovery ingestion")
    ap.add_argument("--source", default="github", choices=["github"])
    ap.add_argument("--query", default="student hackathon")
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args()

    try:
        records = fetch_github(args.query, args.limit)
    except Exception as exc:                     # noqa: BLE001 - fail safe by design
        print(f"Ingestion failed ({exc.__class__.__name__}: {exc}). Cache left unchanged.")
        return 1

    payload = {
        "_meta": {
            "source": "github",
            "query": args.query,
            "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
            "count": len(records),
            "notice": ("Auto-ingested, NOT human-checked. Deadlines are null. "
                       "Treat every field as unverified."),
        },
        "opportunities": records,
    }
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CACHE_PATH)                  # atomic: never a half-written cache
    print(f"Wrote {len(records)} fetched records to {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
