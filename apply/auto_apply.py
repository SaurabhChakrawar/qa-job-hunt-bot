"""
auto_apply.py
Prepares LinkedIn Easy Apply forms for applicant review.
Tracks all applications in applied_jobs.json.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.json")
PROFILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "resume_profile.json")
APPLIED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "applied_jobs.json")


def load_applied_jobs() -> dict:
    if os.path.exists(APPLIED_PATH):
        with open(APPLIED_PATH) as f:
            return json.load(f)
    return {}


def save_applied_job(job_id: str, job: dict, status: str, method: str = "linkedin_easy_apply"):
    applied = load_applied_jobs()
    applied[job_id] = {
        "title": job.get("title"),
        "company": job.get("company"),
        "url": job.get("url"),
        "applied_at": datetime.now().isoformat(),
        "status": status,
        "match_score": job.get("match_score", 0),
        "method": method,  # "linkedin_easy_apply" | "direct_greenhouse" | "direct_lever"
    }
    os.makedirs(os.path.dirname(APPLIED_PATH), exist_ok=True)
    with open(APPLIED_PATH, "w") as f:
        json.dump(applied, f, indent=2)


async def _submission_confirmed(page) -> bool:
    success_el = await page.query_selector(
        "[aria-label*='submitted' i], .jobs-easy-apply-modal__content h3"
    )
    if not success_el:
        return False
    return any(word in (await success_el.inner_text()).lower() for word in ("submitted", "sent"))


async def _wait_for_review(page, job: dict) -> str:
    """Keep the browser open until the user reviews and submits the form."""
    print(f"\n   👀 REVIEW REQUIRED: {job.get('title')} at {job.get('company')}")
    print("      Check every answer in the visible LinkedIn window and click Submit yourself.")
    response = await asyncio.to_thread(input, "      Press Enter after submitting, or type 'skip' to leave it for later: ")
    if response.strip().lower() == "skip":
        return "ready_for_review"
    await page.wait_for_timeout(1000)
    return "applied" if await _submission_confirmed(page) else "review_unconfirmed"


async def apply_to_linkedin_job(
    page, job: dict, profile: dict, resume_path: str, review_before_submit: bool = True
) -> str:
    """
    Attempt LinkedIn Easy Apply. Returns status string.
    """
    url = job.get("url", "")
    if not url or "linkedin.com" not in url:
        return "skipped_not_linkedin"

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # Look for Easy Apply button
        easy_apply_btn = await page.query_selector("button[aria-label*='Easy Apply'], .jobs-apply-button--top-card")
        if not easy_apply_btn:
            return "skipped_no_easy_apply"

        await easy_apply_btn.click()
        await page.wait_for_timeout(2000)

        # Handle multi-step Easy Apply modal
        max_steps = 8
        for step in range(max_steps):
            # Check if application is complete
            if await _submission_confirmed(page):
                return "applied"

            # Handle phone field
            phone_field = await page.query_selector("input[id*='phone'], input[name*='phone']")
            if phone_field:
                val = await phone_field.input_value()
                if not val:
                    phone = profile.get("personal", {}).get("phone", "")
                    if phone:
                        await phone_field.fill(phone)

            # Handle city/location field
            city_field = await page.query_selector("input[id*='city'], input[name*='location']")
            if city_field:
                val = await city_field.input_value()
                if not val:
                    location = profile.get("personal", {}).get("location", "")
                    if location:
                        await city_field.fill(location.split(",")[0])

            # Handle resume upload if present
            resume_upload = await page.query_selector("input[type='file']")
            if resume_upload and resume_path and os.path.exists(resume_path):
                await resume_upload.set_input_files(resume_path)
                await page.wait_for_timeout(1000)

            # Do not guess answers for radio buttons, dropdowns, or numeric
            # fields. Those include legal, salary, demographic and screening
            # questions that must be reviewed by the applicant.

            # Click Next/Review; never submit without review unless explicitly
            # opted into legacy automatic submission in local configuration.
            next_btn = await page.query_selector(
                "button[aria-label='Continue to next step'], "
                "button[aria-label='Review your application'], "
                "button[aria-label='Submit application'], "
                "button:has-text('Next'), button:has-text('Review'), button:has-text('Submit')"
            )

            if next_btn:
                btn_text = await next_btn.inner_text()
                if "submit" in btn_text.lower() and review_before_submit:
                    return await _wait_for_review(page, job)
                await next_btn.click()
                await page.wait_for_timeout(2000)

                if "submit" in btn_text.lower():
                    return "applied"
            else:
                # Can't find next button - may need manual intervention
                return "skipped_manual_needed"

        return "ready_for_review"

    except PlaywrightTimeout:
        return "failed_timeout"
    except Exception as e:
        return f"failed_{str(e)[:50]}"


async def auto_apply_batch(jobs: list, resume_path: str, max_applications: int = 10) -> list:
    """
    Auto-apply to a list of matched jobs.
    Returns list of application results.
    """
    config_path = CONFIG_PATH
    with open(config_path) as f:
        config = json.load(f)

    with open(PROFILE_PATH) as f:
        profile = json.load(f)

    if not config["linkedin"].get("auto_apply", False):
        print("⚠️ Auto-apply is disabled in config. Set linkedin.auto_apply = true to enable.")
        return []

    review_before_submit = config["linkedin"].get("review_before_submit", True)
    if review_before_submit:
        print("👀 Review-first mode: forms will pause before final submission.")

    applied_jobs = load_applied_jobs()
    results = []
    apply_count = 0

    # Only apply to LinkedIn jobs with Easy Apply
    eligible = [
        j for j in jobs
        if j.get("source") == "linkedin"
        and j.get("recommendation") == "APPLY"
        and j.get("match_score", 0) >= 75
        and j.get("id", "") not in applied_jobs
    ]

    if not eligible:
        print("   No eligible jobs for auto-apply today")
        return []

    action = "Preparing Easy Apply forms" if review_before_submit else "Auto-applying"
    print(f"🚀 {action} for {min(len(eligible), max_applications)} jobs...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=False to handle CAPTCHAs
        context = await browser.new_context()

        # Login first
        page = await context.new_page()
        li_email = config["linkedin"].get("email", "")
        li_pass = config["linkedin"].get("password", "")

        if li_email and li_pass:
            await page.goto("https://www.linkedin.com/login")
            await page.fill("#username", li_email)
            await page.fill("#password", li_pass)
            await page.click('[type="submit"]')
            await page.wait_for_timeout(3000)

        for job in eligible[:max_applications]:
            if apply_count >= max_applications:
                break

            job_id = job.get("id", "")
            print(f"   📝 Applying: {job['title']} at {job['company']}...")

            status = await apply_to_linkedin_job(
                page, job, profile, resume_path, review_before_submit=review_before_submit
            )
            save_applied_job(job_id, job, status)

            result = {
                "job": job,
                "status": status,
                "applied_at": datetime.now().isoformat()
            }
            results.append(result)

            if status == "applied":
                apply_count += 1
                print(f"   ✅ Applied successfully!")
            else:
                print(f"   ⚠️ Status: {status}")

            await asyncio.sleep(5)  # Delay between applications

        await browser.close()

    print(f"\n📊 Auto-apply complete: {apply_count} successful applications")
    return results


def run_auto_apply(jobs: list, resume_path: str) -> list:
    """Synchronous wrapper for auto-apply."""
    config_path = CONFIG_PATH
    with open(config_path) as f:
        config = json.load(f)
    max_apply = config["linkedin"].get("max_apply_per_day", 10)
    return asyncio.run(auto_apply_batch(jobs, resume_path, max_apply))
