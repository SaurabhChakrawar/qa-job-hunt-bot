"""
save_jobs_json.py
Saves all matched jobs to docs/jobs.json for the GitHub Pages dashboard.
Called automatically at end of main pipeline.
"""
import json
import os
from datetime import datetime


def save_jobs_for_dashboard(matched_jobs: dict, skill_gap: dict, total_scraped: int):
    """Save jobs to docs/jobs.json for GitHub Pages dashboard."""
    os.makedirs("docs", exist_ok=True)

    all_jobs = []
    for category, jobs in matched_jobs.items():
        for job in jobs:
            job["category"] = category
            all_jobs.append(job)

    # Sort by match score
    all_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    output = {
        "generated_at": datetime.now().isoformat(),
        "total_scraped": total_scraped,
        "total_matched": len(all_jobs),
        "jobs": all_jobs,
        "skill_gap": skill_gap,
        "stats": {
            "excellent": len([j for j in all_jobs if j.get("match_score", 0) >= 80]),
            "good": len([j for j in all_jobs if 60 <= j.get("match_score", 0) < 80]),
            "india_remote": len([j for j in all_jobs if j.get("category") == "india_remote"]),
            "sponsorship": len([j for j in all_jobs if j.get("category") == "sponsorship_worldwide"]),
            "remote_worldwide": len([j for j in all_jobs if j.get("category") == "remote_worldwide"]),
        }
    }

    with open("docs/jobs.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"   💾 Dashboard data saved: docs/jobs.json ({len(all_jobs)} jobs)")
