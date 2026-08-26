"""
save_jobs_json.py
Saves all matched jobs to docs/jobs.json for the GitHub Pages dashboard.
"""
import json
import os
from datetime import datetime, timedelta


def _posted_within_days(job: dict, days: int = 7) -> bool:
    """Treat unknown or invalid dates as not fresh enough for Apply Today."""
    raw_date = str(job.get("date_posted", "")).strip().replace("Z", "+00:00")
    if not raw_date:
        return False
    try:
        posted_at = datetime.fromisoformat(raw_date)
        if posted_at.tzinfo:
            posted_at = posted_at.replace(tzinfo=None)
        return posted_at >= datetime.now() - timedelta(days=days)
    except ValueError:
        return False


def build_application_queue(all_jobs: list, limit: int = 10) -> list:
    """Select fresh, high-confidence jobs worth reviewing today."""
    queue = []
    for job in all_jobs:
        if (
            job.get("match_score", 0) < 75
            or job.get("recommendation") != "APPLY"
            or not job.get("url")
            or not _posted_within_days(job)
        ):
            continue

        priority_score = int(job.get("match_score", 0))
        reasons = [f"{job.get('match_score', 0)}% skills match", "Posted within the last 7 days"]
        if job.get("sponsorship_verified") is True:
            priority_score += 5
            reasons.append("Sponsorship explicitly verified")
        if job.get("easy_apply") is True:
            priority_score += 3
            reasons.append("LinkedIn Easy Apply available")

        # Preserve this context on the dashboard's main job record as well as
        # in the queue, so the card can explain why it was selected.
        job["priority_score"] = priority_score
        job["priority_reasons"] = reasons
        queue.append(dict(job))

    return sorted(queue, key=lambda job: job["priority_score"], reverse=True)[:limit]


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

    # A short review queue is safer and more useful than automatic submissions.
    application_queue = build_application_queue(all_jobs)

    output = {
        "generated_at": datetime.now().isoformat(),
        "total_scraped": total_scraped,
        "total_matched": len(all_jobs),
        "jobs": all_jobs,
        "application_queue": application_queue,
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
