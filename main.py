"""
main.py
Main orchestrator — works both locally and on GitHub Actions.
Reads config from config/config.json (created by GitHub Actions workflow).
"""

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "config.json")
PROFILE_PATH = os.path.join(os.path.dirname(__file__), "config", "resume_profile.json")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_profile():
    if not os.path.exists(PROFILE_PATH):
        print("❌ Resume profile not found.")
        print("   Locally: python main.py --parse-resume /path/to/resume.pdf")
        print("   GitHub:  Set RESUME_PROFILE_JSON secret (see setup guide)")
        sys.exit(1)
    with open(PROFILE_PATH) as f:
        return json.load(f)


def check_api_key(config):
    key = config["api_keys"].get("gemini_api_key", "")
    if not key or key == "YOUR_GEMINI_API_KEY_HERE":
        print("❌ Gemini API key not set!")
        print("   Locally: edit config/config.json")
        print("   GitHub:  add GEMINI_API_KEY secret in repo settings")
        sys.exit(1)


def run_full_pipeline(resume_path: str = None):
    config = load_config()
    check_api_key(config)
    profile = load_profile()

    is_github = os.environ.get("GITHUB_ACTIONS") == "true"
    env_label = "☁️  GitHub Actions" if is_github else "💻 Local Mac"

    print(f"\n{'='*60}")
    print(f"🚀 QA JOB HUNT BOT - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"🤖 Gemini AI (FREE) | Running on: {env_label}")
    print(f"{'='*60}")
    print(f"👤 {profile['personal'].get('name', 'QA Engineer')}")
    print(f"🎯 {', '.join(config['job_preferences']['role_titles'][:3])}...")
    print(f"{'='*60}\n")

    # ── STEP 1: SCRAPE ──────────────────────────────────────────
    print("📡 STEP 1: Scraping job boards...")
    all_raw_jobs = {"sponsorship_worldwide": [], "india_remote": [], "remote_worldwide": []}

    try:
        from scrapers.remote_scraper import scrape_all_remote_boards
        for cat, jobs in scrape_all_remote_boards().items():
            all_raw_jobs[cat].extend(jobs)
    except Exception as e:
        print(f"⚠️ Remote scraper error: {e}")

    try:
        from scrapers.linkedin_scraper import scrape_all_categories
        for cat, jobs in scrape_all_categories(max_jobs=config["search_settings"]["max_jobs_per_source"]).items():
            all_raw_jobs[cat].extend(jobs)
    except Exception as e:
        print(f"⚠️ LinkedIn scraper error: {e}")

    total_scraped = sum(len(j) for j in all_raw_jobs.values())
    print(f"\n📊 Total raw jobs scraped: {total_scraped}")

    # ── STEP 2: DEDUPLICATE ─────────────────────────────────────
    print("\n🔄 STEP 2: Deduplicating...")
    from data.jobs_db import filter_new_jobs
    deduped_jobs = {}
    for cat, jobs in all_raw_jobs.items():
        deduped_jobs[cat] = filter_new_jobs(jobs, window_days=config["search_settings"]["dedup_window_days"])
    total_new = sum(len(j) for j in deduped_jobs.values())
    print(f"📦 New jobs after dedup: {total_new}")

    # ── STEP 3: AI MATCHING ─────────────────────────────────────
    print("\n🤖 STEP 3: AI Matching with Gemini (Free)...")
    from matcher.job_matcher import batch_match_jobs, generate_skill_gap_analysis
    min_score = config["job_preferences"]["min_match_score"]
    matched_jobs = {}
    all_scored_jobs = []

    for cat, jobs in deduped_jobs.items():
        if not jobs:
            matched_jobs[cat] = []
            continue
        print(f"\n  📂 {cat} ({len(jobs)} jobs)")
        matched = batch_match_jobs(jobs, min_score=min_score)
        matched_jobs[cat] = matched
        all_scored_jobs.extend(matched)

    total_matched = sum(len(j) for j in matched_jobs.values())
    print(f"\n✅ Matched: {total_matched} jobs (score >= {min_score}%)")

    # ── STEP 4: SKIP AUTO-APPLY ON GITHUB ───────────────────────
    applied_results = []
    if is_github:
        print("\n⏭️  STEP 4: Auto-apply skipped (not supported on GitHub Actions)")
    elif config["linkedin"].get("auto_apply", False):
        print("\n📝 STEP 4: Auto-applying...")
        from apply.auto_apply import run_auto_apply
        all_flat = [j for jobs in matched_jobs.values() for j in jobs]
        applied_results = run_auto_apply(all_flat, resume_path or "")
    else:
        print("\n⏭️  STEP 4: Auto-apply disabled")

    # ── STEP 5: SKILL GAP ANALYSIS ──────────────────────────────
    print("\n🧠 STEP 5: Skill gap analysis with Gemini...")
    api_key = config["api_keys"]["gemini_api_key"]
    skill_gap = generate_skill_gap_analysis(all_scored_jobs, profile, api_key)

    # ── STEP 6: GENERATE REPORT ─────────────────────────────────
    print("\n📊 STEP 6: Generating HTML report...")
    from reporter.report_generator import generate_report

    applied_urls = {r["job"].get("url") for r in applied_results if r.get("status") == "applied"}
    for cat_jobs in matched_jobs.values():
        for job in cat_jobs:
            if job.get("url") in applied_urls:
                job["auto_applied"] = True

    html_report = generate_report(
        matched_jobs=matched_jobs,
        applied_results=applied_results,
        skill_gap=skill_gap,
        total_scraped=total_scraped
    )

    os.makedirs("logs", exist_ok=True)
    report_path = f"logs/report_{datetime.now().strftime('%Y%m%d')}.html"
    with open(report_path, "w") as f:
        f.write(html_report)
    print(f"   💾 Saved: {report_path}")

    # ── STEP 7: SEND EMAIL ───────────────────────────────────────
    print("\n📧 STEP 7: Sending email...")
    from reporter.email_sender import send_report_email
    send_report_email(html_report, job_count=total_scraped, match_count=total_matched)

    print(f"\n{'='*60}")
    print(f"✅ DONE!")
    print(f"   📡 Scraped:  {total_scraped} jobs")
    print(f"   🎯 Matched:  {total_matched} jobs")
    print(f"   📧 Sent to:  {config['email']['recipient_email']}")
    print(f"   💰 Cost:     $0.00")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="QA Job Hunt Bot")
    parser.add_argument("--parse-resume", metavar="PATH", help="Parse resume PDF")
    parser.add_argument("--test-email", action="store_true", help="Send test email")
    parser.add_argument("--resume-path", default="", help="Resume path for auto-apply")
    args = parser.parse_args()

    if args.parse_resume:
        from matcher.resume_parser import main as parse_main
        sys.argv = ["resume_parser.py", "--resume", args.parse_resume]
        parse_main()
        return

    if args.test_email:
        from reporter.email_sender import send_report_email
        html = "<div style='font-family:Arial;padding:30px;text-align:center'><h1>✅ Job Bot Working!</h1><p>Daily reports will arrive at 9:00 AM IST 🎉</p></div>"
        send_report_email(html, 0, 0)
        return

    run_full_pipeline(args.resume_path)


if __name__ == "__main__":
    main()
