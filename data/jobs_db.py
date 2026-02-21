"""
jobs_db.py
Simple JSON-based job database for deduplication across days.
"""

import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jobs_db.json")


def load_db() -> dict:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        with open(DB_PATH) as f:
            return json.load(f)
    return {"jobs": {}, "last_updated": ""}


def save_db(db: dict):
    db["last_updated"] = datetime.now().isoformat()
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)


def filter_new_jobs(jobs: list, window_days: int = 30) -> list:
    """Return only jobs not seen in the last window_days days."""
    db = load_db()
    cutoff = datetime.now() - timedelta(days=window_days)
    new_jobs = []

    for job in jobs:
        job_id = job.get("id", "") or job.get("url", "")
        if not job_id:
            new_jobs.append(job)
            continue

        if job_id in db["jobs"]:
            # Check if it's old enough to re-show (stale)
            seen_at = datetime.fromisoformat(db["jobs"][job_id].get("seen_at", "2000-01-01"))
            if seen_at > cutoff:
                continue  # Already seen recently, skip

        new_jobs.append(job)
        db["jobs"][job_id] = {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "seen_at": datetime.now().isoformat(),
            "category": job.get("category", ""),
        }

    save_db(db)
    print(f"   📦 Dedup: {len(jobs)} total → {len(new_jobs)} new jobs")
    return new_jobs


def get_stats() -> dict:
    db = load_db()
    return {
        "total_tracked": len(db["jobs"]),
        "last_updated": db.get("last_updated", "never")
    }
