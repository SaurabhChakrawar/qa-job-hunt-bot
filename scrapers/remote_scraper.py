"""
remote_scraper.py - FIXED VERSION
Uses Remotive free API properly with full job descriptions.
"""

import requests
import json
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup
import time
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# QA-specific search terms
QA_SEARCHES = [
    "selenium", "playwright", "cypress", "appium",
    "test automation", "qa automation", "sdet",
    "quality assurance", "software tester", "testng"
]


def clean_html(html_text: str) -> str:
    """Strip HTML tags from job description."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "lxml")
    return soup.get_text(separator=" ", strip=True)[:3000]


def scrape_remotive() -> list:
    """Scrape Remotive.io using their free API - returns full descriptions."""
    jobs = []
    seen_ids = set()

    # Remotive free API - no key needed
    categories = ["qa", "testing", "software-dev"]
    
    for category in categories:
        try:
            url = f"https://remotive.com/api/remote-jobs?category={category}&limit=50"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            
            data = resp.json()
            for job in data.get("jobs", []):
                job_id = str(job.get("id", ""))
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = job.get("title", "").lower()
                # Filter only QA related jobs
                if not any(kw in title for kw in [
                    "qa", "quality", "test", "sdet", "automation",
                    "selenium", "playwright", "cypress"
                ]):
                    continue

                description = clean_html(job.get("description", ""))
                
                jobs.append({
                    "id": f"remotive_{job_id}",
                    "title": job.get("title", ""),
                    "company": job.get("company_name", ""),
                    "location": job.get("candidate_required_location", "Worldwide"),
                    "url": job.get("url", ""),
                    "description": description,
                    "source": "remotive",
                    "category": "remote_worldwide",
                    "type": "Remote Worldwide",
                    "date_posted": job.get("publication_date", str(datetime.now().date())),
                    "scraped_at": datetime.now().isoformat(),
                    "salary": job.get("salary", ""),
                    "tags": job.get("tags", []),
                })
            
            time.sleep(1)
        except Exception as e:
            print(f"   ⚠️ Remotive {category} error: {e}")

    print(f"   ✅ Remotive: {len(jobs)} QA jobs with descriptions")
    return jobs


def scrape_himalayas() -> list:
    """Scrape Himalayas.app - great remote job board with full descriptions."""
    jobs = []
    searches = [
        "QA automation engineer",
        "SDET",
        "test automation engineer",
        "software test engineer",
        "selenium engineer"
    ]

    for query in searches:
        try:
            url = f"https://himalayas.app/api/jobs?q={query.replace(' ', '+')}&limit=20"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            data = resp.json()
            for job in data.get("jobs", []):
                slug = job.get("slug", "")
                description = clean_html(job.get("description", ""))
                
                # Get location restrictions
                locations = job.get("locationRestrictions", [])
                location = locations[0] if locations else "Worldwide"

                jobs.append({
                    "id": f"himalayas_{slug}",
                    "title": job.get("title", ""),
                    "company": job.get("company", {}).get("name", ""),
                    "location": location,
                    "url": f"https://himalayas.app/jobs/{slug}",
                    "description": description,
                    "source": "himalayas",
                    "category": "remote_worldwide",
                    "type": "Remote Worldwide",
                    "date_posted": job.get("publishedAt", str(datetime.now().date())),
                    "scraped_at": datetime.now().isoformat(),
                    "salary": str(job.get("salaryRange", "")),
                })
            time.sleep(1)
        except Exception as e:
            print(f"   ⚠️ Himalayas error for '{query}': {e}")

    # Deduplicate
    seen = set()
    unique = []
    for job in jobs:
        if job["id"] not in seen and job["title"]:
            seen.add(job["id"])
            unique.append(job)

    print(f"   ✅ Himalayas: {len(unique)} jobs")
    return unique


def scrape_arbeitnow() -> list:
    """Scrape Arbeitnow - great for Europe + visa sponsorship jobs."""
    jobs = []
    try:
        # Free API, no key needed
        url = "https://www.arbeitnow.com/api/job-board-api"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        data = resp.json()
        for job in data.get("data", []):
            title = job.get("title", "").lower()
            # Filter QA related
            if not any(kw in title for kw in [
                "qa", "quality", "test", "sdet", "automation"
            ]):
                continue

            description = clean_html(job.get("description", ""))
            visa = job.get("visa_sponsorship", False)

            jobs.append({
                "id": f"arbeitnow_{job.get('slug', '')}",
                "title": job.get("title", ""),
                "company": job.get("company_name", ""),
                "location": job.get("location", "Europe"),
                "url": job.get("url", ""),
                "description": description,
                "source": "arbeitnow",
                "category": "sponsorship_worldwide" if visa else "remote_worldwide",
                "type": "Outside India (Sponsorship)" if visa else "Remote Worldwide",
                "sponsorship": visa,
                "date_posted": job.get("created_at", str(datetime.now().date())),
                "scraped_at": datetime.now().isoformat(),
            })

    except Exception as e:
        print(f"   ⚠️ Arbeitnow error: {e}")

    print(f"   ✅ Arbeitnow: {len(jobs)} QA jobs (includes visa sponsorship)")
    return jobs


def scrape_jobicy() -> list:
    """Scrape Jobicy - remote jobs API, free, no key needed."""
    jobs = []
    searches = ["qa-engineer", "test-automation", "sdet", "quality-assurance"]
    
    for tag in searches:
        try:
            url = f"https://jobicy.com/api/v2/remote-jobs?tag={tag}&count=20"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            data = resp.json()
            for job in data.get("jobs", []):
                description = clean_html(job.get("jobDescription", ""))
                jobs.append({
                    "id": f"jobicy_{job.get('id', '')}",
                    "title": job.get("jobTitle", ""),
                    "company": job.get("companyName", ""),
                    "location": job.get("jobGeo", "Worldwide"),
                    "url": job.get("url", ""),
                    "description": description,
                    "source": "jobicy",
                    "category": "remote_worldwide",
                    "type": "Remote Worldwide",
                    "date_posted": job.get("pubDate", str(datetime.now().date())),
                    "scraped_at": datetime.now().isoformat(),
                    "salary": job.get("annualSalaryMin", ""),
                })
            time.sleep(1)
        except Exception as e:
            print(f"   ⚠️ Jobicy error: {e}")

    # Deduplicate
    seen = set()
    unique = [j for j in jobs if j["id"] not in seen and not seen.add(j["id"]) and j["title"]]
    print(f"   ✅ Jobicy: {len(unique)} remote QA jobs")
    return unique


def scrape_naukri_remote() -> list:
    """Scrape Naukri for India remote QA jobs."""
    jobs = []
    searches = [
        ("qa-automation-engineer-jobs", "QA Automation Engineer"),
        ("test-automation-engineer-jobs", "Test Automation Engineer"),
        ("sdet-jobs", "SDET"),
    ]

    for path, label in searches:
        try:
            url = f"https://www.naukri.com/{path}?jobType=work+from+home"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            
            # Try multiple selectors
            cards = (soup.select("article.jobTuple") or 
                    soup.select("[class*='jobTuple']") or
                    soup.select(".job-container"))

            for card in cards[:20]:
                title_el = card.select_one("a.title, [class*='jobTitle'] a")
                company_el = card.select_one("[class*='companyName'], .companyInfo a")
                
                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                job_url = title_el.get("href", "") if title_el else ""

                if title and job_url:
                    jobs.append({
                        "id": f"naukri_{hash(job_url) % 100000}",
                        "title": title,
                        "company": company,
                        "location": "India (Remote)",
                        "url": job_url,
                        "description": f"QA Automation role at {company}. Position: {title}. Remote work from India.",
                        "source": "naukri",
                        "category": "india_remote",
                        "type": "India Remote",
                        "date_posted": str(datetime.now().date()),
                        "scraped_at": datetime.now().isoformat(),
                    })
            time.sleep(2)
        except Exception as e:
            print(f"   ⚠️ Naukri error: {e}")

    seen = set()
    unique = [j for j in jobs if j["id"] not in seen and not seen.add(j["id"]) and j["title"]]
    print(f"   ✅ Naukri: {len(unique)} India remote jobs")
    return unique


def deduplicate(jobs: list) -> list:
    seen = set()
    unique = []
    for job in jobs:
        key = job.get("url", "") or job.get("id", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def scrape_all_remote_boards() -> dict:
    """Scrape all job boards. Returns categorized jobs with descriptions."""
    print("\n🌐 Scraping job boards...")

    results = {
        "remote_worldwide": [],
        "india_remote": [],
        "sponsorship_worldwide": [],
    }

    print("  📍 Remotive.io (free API)...")
    results["remote_worldwide"].extend(scrape_remotive())

    print("  📍 Himalayas.app...")
    results["remote_worldwide"].extend(scrape_himalayas())

    print("  📍 Arbeitnow (Europe + Visa Sponsorship)...")
    arbeitnow_jobs = scrape_arbeitnow()
    for job in arbeitnow_jobs:
        cat = job.get("category", "remote_worldwide")
        results[cat].append(job)

    print("  📍 Jobicy (Remote)...")
    results["remote_worldwide"].extend(scrape_jobicy())

    print("  📍 Naukri (India Remote)...")
    results["india_remote"].extend(scrape_naukri_remote())

    # Deduplicate each category
    for cat in results:
        results[cat] = deduplicate(results[cat])
        print(f"  📊 {cat}: {len(results[cat])} unique jobs")

    total = sum(len(j) for j in results.values())
    print(f"\n  🎯 Total: {total} jobs scraped across all boards")
    return results
