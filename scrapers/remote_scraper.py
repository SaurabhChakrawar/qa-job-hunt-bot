"""
remote_scraper.py
Scrapes remote-specific job boards for QA/Test Automation roles:
- Remotive.io
- We Work Remotely (WWR)
- Remote.co
- Himalayas.app
- Wellfound (AngelList)
"""

import requests
import json
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup
import time
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

QA_KEYWORDS = ["qa automation", "test automation", "sdet", "quality assurance", "selenium", "playwright", "cypress", "software tester"]


def scrape_remotive() -> list:
    """Scrape Remotive.io for QA jobs via their API."""
    jobs = []
    searches = ["qa", "test", "sdet", "quality assurance"]

    for query in searches:
        try:
            url = f"https://remotive.com/api/remote-jobs?category=qa&search={query}&limit=20"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for job in data.get("jobs", []):
                    jobs.append({
                        "id": f"remotive_{job.get('id', '')}",
                        "title": job.get("title", ""),
                        "company": job.get("company_name", ""),
                        "location": job.get("candidate_required_location", "Worldwide"),
                        "url": job.get("url", ""),
                        "description": job.get("description", "")[:2000],
                        "source": "remotive",
                        "category": "remote_worldwide",
                        "type": "Remote Worldwide",
                        "date_posted": job.get("publication_date", str(datetime.now().date())),
                        "scraped_at": datetime.now().isoformat(),
                        "salary": job.get("salary", ""),
                        "tags": job.get("tags", []),
                    })
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            print(f"   ⚠️ Remotive error: {e}")

    print(f"   ✅ Remotive: {len(jobs)} jobs")
    return deduplicate(jobs)


def scrape_weworkremotely() -> list:
    """Scrape We Work Remotely for QA jobs."""
    jobs = []
    categories = [
        "https://weworkremotely.com/categories/remote-programming-jobs",
        "https://weworkremotely.com/categories/remote-qa-jobs",
    ]

    for cat_url in categories:
        try:
            resp = requests.get(cat_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            job_sections = soup.select("section.jobs article")

            for article in job_sections[:30]:
                title_el = article.select_one("span.title")
                company_el = article.select_one("span.company")
                link_el = article.select_one("a[href*='/remote-jobs/']")
                region_el = article.select_one("span.region")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                url = "https://weworkremotely.com" + link_el["href"] if link_el else ""
                location = region_el.get_text(strip=True) if region_el else "Worldwide"

                # Filter for QA-related jobs
                if not any(kw in title.lower() for kw in ["qa", "test", "quality", "sdet", "automation"]):
                    continue

                if title and url:
                    jobs.append({
                        "id": f"wwr_{url.split('/')[-1]}",
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url,
                        "description": "",
                        "source": "weworkremotely",
                        "category": "remote_worldwide",
                        "type": "Remote Worldwide",
                        "date_posted": str(datetime.now().date()),
                        "scraped_at": datetime.now().isoformat(),
                    })

            time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"   ⚠️ WWR error: {e}")

    print(f"   ✅ We Work Remotely: {len(jobs)} jobs")
    return jobs


def scrape_himalayas() -> list:
    """Scrape Himalayas.app via their public API."""
    jobs = []
    searches = ["QA automation engineer", "SDET", "test automation engineer", "software test engineer"]

    for query in searches:
        try:
            url = f"https://himalayas.app/api/jobs?q={query.replace(' ', '+')}&remote=true&limit=20"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for job in data.get("jobs", []):
                    jobs.append({
                        "id": f"himalayas_{job.get('slug', '')}",
                        "title": job.get("title", ""),
                        "company": job.get("company", {}).get("name", ""),
                        "location": job.get("locationRestrictions", ["Worldwide"])[0] if job.get("locationRestrictions") else "Worldwide",
                        "url": f"https://himalayas.app/jobs/{job.get('slug', '')}",
                        "description": job.get("description", "")[:2000],
                        "source": "himalayas",
                        "category": "remote_worldwide",
                        "type": "Remote Worldwide",
                        "date_posted": job.get("publishedAt", str(datetime.now().date())),
                        "scraped_at": datetime.now().isoformat(),
                        "salary": job.get("salaryRange", ""),
                    })
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            print(f"   ⚠️ Himalayas error: {e}")

    print(f"   ✅ Himalayas: {len(jobs)} jobs")
    return deduplicate(jobs)


def scrape_relocate_me() -> list:
    """Scrape Relocate.me for sponsorship/relocation jobs."""
    jobs = []

    try:
        searches = ["qa-automation-engineer", "software-tester", "sdet"]
        for search in searches:
            url = f"https://relocate.me/search?q={search}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            job_cards = soup.select(".job-card, [data-testid='job-card'], article.job")

            for card in job_cards[:20]:
                title_el = card.select_one("h2, h3, .job-title, [class*='title']")
                company_el = card.select_one(".company-name, [class*='company']")
                location_el = card.select_one(".location, [class*='location']")
                link_el = card.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else ""
                href = link_el["href"] if link_el else ""
                url_job = href if href.startswith("http") else f"https://relocate.me{href}"

                if title and url_job:
                    jobs.append({
                        "id": f"relocate_{href.split('/')[-1]}",
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url_job,
                        "description": "",
                        "source": "relocate.me",
                        "category": "sponsorship_worldwide",
                        "type": "Outside India (Sponsorship)",
                        "sponsorship": True,
                        "date_posted": str(datetime.now().date()),
                        "scraped_at": datetime.now().isoformat(),
                    })

            time.sleep(random.uniform(2, 3))

    except Exception as e:
        print(f"   ⚠️ Relocate.me error: {e}")

    print(f"   ✅ Relocate.me: {len(jobs)} sponsorship jobs")
    return jobs


def scrape_naukri_remote() -> list:
    """Scrape Naukri.com for India remote QA jobs."""
    jobs = []

    searches = [
        "QA automation engineer remote",
        "test automation engineer work from home",
        "SDET remote",
        "software tester remote"
    ]

    for search in searches:
        try:
            encoded = search.replace(" ", "-")
            url = f"https://www.naukri.com/{encoded}-jobs?jobType=work+from+home&wfhType=wfh"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            job_articles = soup.select("article.jobTuple, [class*='jobTupleHeader'], .job-container")

            for article in job_articles[:20]:
                title_el = article.select_one("a.title, [class*='jobTitle'] a, .designation a")
                company_el = article.select_one(".companyInfo a, [class*='companyName']")
                location_el = article.select_one(".location, [class*='location']")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else "India (Remote)"
                url_job = title_el.get("href", "") if title_el else ""

                if title and url_job:
                    jobs.append({
                        "id": f"naukri_{url_job.split('/')[-1][:30]}",
                        "title": title,
                        "company": company,
                        "location": f"India - Remote ({location})",
                        "url": url_job,
                        "description": "",
                        "source": "naukri",
                        "category": "india_remote",
                        "type": "India Remote",
                        "date_posted": str(datetime.now().date()),
                        "scraped_at": datetime.now().isoformat(),
                    })

            time.sleep(random.uniform(3, 5))
        except Exception as e:
            print(f"   ⚠️ Naukri error for '{search}': {e}")

    print(f"   ✅ Naukri: {len(jobs)} India remote jobs")
    return deduplicate(jobs)


def deduplicate(jobs: list) -> list:
    seen = set()
    unique = []
    for job in jobs:
        key = job.get("url", "") or f"{job.get('title', '')}_{job.get('company', '')}"
        if key and key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def scrape_all_remote_boards() -> dict:
    """Scrape all remote job boards. Returns categorized jobs."""
    print("\n🌐 Scraping remote job boards...")

    results = {
        "remote_worldwide": [],
        "india_remote": [],
        "sponsorship_worldwide": [],
    }

    print("  📍 Remotive.io...")
    results["remote_worldwide"].extend(scrape_remotive())

    print("  📍 We Work Remotely...")
    results["remote_worldwide"].extend(scrape_weworkremotely())

    print("  📍 Himalayas.app...")
    results["remote_worldwide"].extend(scrape_himalayas())

    print("  📍 Relocate.me (Sponsorship)...")
    results["sponsorship_worldwide"].extend(scrape_relocate_me())

    print("  📍 Naukri (India Remote)...")
    results["india_remote"].extend(scrape_naukri_remote())

    for cat in results:
        results[cat] = deduplicate(results[cat])
        print(f"  📊 {cat}: {len(results[cat])} unique jobs")

    return results
