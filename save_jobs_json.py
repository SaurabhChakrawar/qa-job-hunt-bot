"""
save_jobs_json.py
Saves all matched jobs to docs/jobs.json for the GitHub Pages dashboard.
"""
import json
import os
from datetime import datetime


def save_jobs_for_dashboard(matched_jobs: dict, skill_gap: dict, total_scraped: int):
    """Save jobs to docs/jobs.json for GitHub Pages dashboard."""
    # Ensure docs directory exists
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    output_path = os.path.join(docs_dir, "jobs.json")

    all_jobs = []
    for category, jobs in matched_jobs.items():
        for job in jobs:
            job_copy = dict(job)
            job_copy["category"] = category
            all_jobs.append(job_copy)

    # Sort by match score descending
    all_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    output = {
        "generated_at": datetime.now().isoformat(),
        "total_scraped": total_scraped,
        "total_matched": len(all_jobs),
        "jobs": all_jobs,
        "skill_gap": skill_gap or {},
        "stats": {
            "excellent": len([j for j in all_jobs if j.get("match_score", 0) >= 80]),
            "good": len([j for j in all_jobs if 60 <= j.get("match_score", 0) < 80]),
            "india_remote": len([j for j in all_jobs if j.get("category") == "india_remote"]),
            "sponsorship": len([j for j in all_jobs if j.get("category") == "sponsorship_worldwide"]),
            "remote_worldwide": len([j for j in all_jobs if j.get("category") == "remote_worldwide"]),
        }
    }

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str, ensure_ascii=False)
        size_kb = os.path.getsize(output_path) / 1024
        print(f"   💾 Saved docs/jobs.json — {len(all_jobs)} jobs ({size_kb:.1f} KB)")
        print(f"   📁 Full path: {output_path}")
    except Exception as e:
        print(f"   ❌ Failed to save jobs.json: {e}")
        raise
