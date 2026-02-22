"""
main.py - Updated with Dashboard support
Saves jobs.json for GitHub Pages dashboard after each run.
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
        sys.exit(1)
    with open(PROFILE_PATH) as f:
        return json.load(f)


def check_api_key(config):
    key = config["api_keys"].get("gemini_api_key", "")
    if not key or key == "YOUR_GEMINI_API_KEY_HERE":
        print("❌ Gemini API key not set!")
        sys.exit(1)


def run_full_pipeline(resume_path: str = None):
    config = load_config()
    check_api_key(config)
    profile = load_profile()

    is_github = os.environ.get("GITHUB_ACTIONS") == "true"
    github_repo = os.environ.get("GITHUB_REPOSITORY", "")
    github_username = github_repo.split("/")[0] if "/" in github_repo else ""
    github_reponame = github_repo.split("/")[1] if "/" in github_repo else ""

    # Dashboard URL on GitHub Pages
    dashboard_url = f"https://{github_username}.github.io/{github_reponame}/" if github_username else ""

    print(f"\n{'='*60}")
    print(f"🚀 QA JOB HUNT BOT - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"🤖 Gemini AI (FREE) | {'☁️ GitHub Actions' if is_github else '💻 Local'}")
    print(f"{'='*60}")
    print(f"👤 {profile['personal'].get('name', 'QA Engineer')}")
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
    print("\n🤖 STEP 3: AI Matching with Gemini...")
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
    print(f"\n✅ Matched: {total_matched} jobs")

    # ── STEP 4: SKIP AUTO-APPLY ON GITHUB ───────────────────────
    applied_results = []
    if not is_github and config["linkedin"].get("auto_apply", False):
        from apply.auto_apply import run_auto_apply
        all_flat = [j for jobs in matched_jobs.values() for j in jobs]
        applied_results = run_auto_apply(all_flat, resume_path or "")

    # ── STEP 5: SKILL GAP ANALYSIS ──────────────────────────────
    print("\n🧠 STEP 5: Skill gap analysis...")
    api_key = config["api_keys"]["gemini_api_key"]
    skill_gap = generate_skill_gap_analysis(all_scored_jobs, profile, api_key)

    # ── STEP 6: SAVE DASHBOARD DATA ─────────────────────────────
    print("\n💾 STEP 6: Saving dashboard data...")
    try:
        from save_jobs_json import save_jobs_for_dashboard
        save_jobs_for_dashboard(matched_jobs, skill_gap, total_scraped)
        if dashboard_url:
            print(f"   🌐 Dashboard: {dashboard_url}")
    except Exception as e:
        print(f"   ⚠️ Dashboard save error: {e}")

    # ── STEP 7: GENERATE REPORT ─────────────────────────────────
    print("\n📊 STEP 7: Generating HTML report...")
    from reporter.report_generator import generate_report

    html_report = generate_report(
        matched_jobs=matched_jobs,
        applied_results=applied_results,
        skill_gap=skill_gap,
        total_scraped=total_scraped,
        dashboard_url=dashboard_url
    )

    os.makedirs("logs", exist_ok=True)
    report_path = f"logs/report_{datetime.now().strftime('%Y%m%d')}.html"
    with open(report_path, "w") as f:
        f.write(html_report)

    # ── STEP 8: SEND EMAIL ───────────────────────────────────────
    print("\n📧 STEP 8: Sending email...")
    from reporter.email_sender import send_report_email
    send_report_email(html_report, job_count=total_scraped, match_count=total_matched)

    print(f"\n{'='*60}")
    print(f"✅ DONE! Scraped: {total_scraped} | Matched: {total_matched}")
    print(f"   Dashboard: {dashboard_url or 'Enable GitHub Pages to view'}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parse-resume", metavar="PATH")
    parser.add_argument("--test-email", action="store_true")
    parser.add_argument("--resume-path", default="")
    args = parser.parse_args()

    if args.parse_resume:
        from matcher.resume_parser import main as parse_main
        sys.argv = ["resume_parser.py", "--resume", args.parse_resume]
        parse_main()
        return

    if args.test_email:
        from reporter.email_sender import send_report_email
        html = "<div style='font-family:Arial;padding:30px;text-align:center'><h1>✅ Job Bot Working!</h1></div>"
        send_report_email(html, 0, 0)
        return

    run_full_pipeline(args.resume_path)


if __name__ == "__main__":
    main()
