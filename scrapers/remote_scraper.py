"""
remote_scraper.py - CLOUD OPTIMIZED VERSION
Uses job board APIs that work reliably from GitHub Actions cloud servers.
"""

import requests
import json
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup
import time
import xml.etree.ElementTree as ET

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
}

QA_KEYWORDS = [
    "qa", "quality assurance", "test automation", "automation engineer",
    "sdet", "selenium", "playwright", "cypress", "appium", "testng",
    "software tester", "quality engineer", "test engineer"
]


def is_qa_job(title: str, description: str = "") -> bool:
    text = (title + " " + description).lower()
    return any(kw in text for kw in QA_KEYWORDS)


def clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    try:
        soup = BeautifulSoup(html_text, "lxml")
        return soup.get_text(separator=" ", strip=True)[:3000]
    except:
        return html_text[:3000]


def scrape_remotive() -> list:
    """Remotive free API - try all categories."""
    jobs = []
    seen = set()
    # Try broader categories since 'qa' may be empty
    categories = ["software-dev", "qa", "testing", "devops-sysadmin"]

    for cat in categories:
        try:
            url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=100"
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            for job in resp.json().get("jobs", []):
                jid = str(job.get("id", ""))
                if jid in seen:
                    continue
                title = job.get("title", "")
                desc = clean_html(job.get("description", ""))
                if not is_qa_job(title, desc[:500]):
                    continue
                seen.add(jid)
                jobs.append({
                    "id": f"remotive_{jid}",
                    "title": title,
                    "company": job.get("company_name", ""),
                    "location": job.get("candidate_required_location", "Worldwide"),
                    "url": job.get("url", ""),
                    "description": desc,
                    "source": "remotive",
                    "category": "remote_worldwide",
                    "type": "Remote Worldwide",
                    "date_posted": job.get("publication_date", str(datetime.now().date())),
                    "scraped_at": datetime.now().isoformat(),
                    "salary": job.get("salary", ""),
                })
            time.sleep(1)
        except Exception as e:
            print(f"   ⚠️ Remotive {cat}: {e}")

    print(f"   ✅ Remotive: {len(jobs)} QA jobs")
    return jobs


def scrape_arbeitnow() -> list:
    """Arbeitnow - reliable free API, good for Europe + sponsorship."""
    jobs = []
    try:
        # Try multiple pages
        for page in range(1, 4):
            url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                break
            data = resp.json().get("data", [])
            if not data:
                break
            for job in data:
                title = job.get("title", "")
                desc = clean_html(job.get("description", ""))
                if not is_qa_job(title, desc[:500]):
                    continue
                visa = job.get("visa_sponsorship", False)
                remote = job.get("remote", False)
                jobs.append({
                    "id": f"arbeitnow_{job.get('slug', '')}",
                    "title": title,
                    "company": job.get("company_name", ""),
                    "location": job.get("location", "Europe"),
                    "url": job.get("url", ""),
                    "description": desc,
                    "source": "arbeitnow",
                    "category": "sponsorship_worldwide" if visa else "remote_worldwide",
                    "type": "Outside India (Sponsorship)" if visa else "Remote Worldwide",
                    "sponsorship": visa,
                    "date_posted": str(datetime.now().date()),
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(1)
    except Exception as e:
        print(f"   ⚠️ Arbeitnow: {e}")

    print(f"   ✅ Arbeitnow: {len(jobs)} QA jobs")
    return jobs


def scrape_jobicy() -> list:
    """Jobicy API - try broader tags."""
    jobs = []
    seen = set()
    tags = ["qa", "testing", "quality-assurance", "test-automation",
            "sdet", "selenium", "software-testing", "automation"]

    for tag in tags:
        try:
            url = f"https://jobicy.com/api/v2/remote-jobs?tag={tag}&count=50"
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            for job in resp.json().get("jobs", []):
                jid = str(job.get("id", ""))
                if jid in seen:
                    continue
                title = job.get("jobTitle", "")
                if not title:
                    continue
                seen.add(jid)
                desc = clean_html(job.get("jobDescription", ""))
                jobs.append({
                    "id": f"jobicy_{jid}",
                    "title": title,
                    "company": job.get("companyName", ""),
                    "location": job.get("jobGeo", "Worldwide"),
                    "url": job.get("url", ""),
                    "description": desc,
                    "source": "jobicy",
                    "category": "remote_worldwide",
                    "type": "Remote Worldwide",
                    "date_posted": job.get("pubDate", str(datetime.now().date())),
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(1)
        except Exception as e:
            print(f"   ⚠️ Jobicy {tag}: {e}")

    print(f"   ✅ Jobicy: {len(jobs)} QA jobs")
    return jobs


def scrape_adzuna() -> list:
    """Adzuna - large job board with free API. Register at developer.adzuna.com"""
    jobs = []
    # Works without auth for basic searches
    searches = [
        "qa+automation+engineer+remote",
        "test+automation+engineer+remote",
        "sdet+remote",
        "selenium+automation+remote"
    ]
    countries = ["in", "gb", "us", "au", "ca"]

    for country in countries:
        for search in searches[:2]:  # Limit to avoid rate limits
            try:
                url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1?app_id=&app_key=&results_per_page=20&what={search}&content-type=application/json"
                resp = requests.get(url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    continue
                for job in resp.json().get("results", []):
                    title = job.get("title", "")
                    if not is_qa_job(title):
                        continue
                    desc = clean_html(job.get("description", ""))
                    is_india = country == "in"
                    jobs.append({
                        "id": f"adzuna_{job.get('id', '')}",
                        "title": title,
                        "company": job.get("company", {}).get("display_name", ""),
                        "location": job.get("location", {}).get("display_name", ""),
                        "url": job.get("redirect_url", ""),
                        "description": desc,
                        "source": "adzuna",
                        "category": "india_remote" if is_india else "remote_worldwide",
                        "type": "India Remote" if is_india else "Remote Worldwide",
                        "date_posted": str(datetime.now().date()),
                        "scraped_at": datetime.now().isoformat(),
                        "salary": str(job.get("salary_min", "")),
                    })
                time.sleep(1)
            except Exception as e:
                pass  # Silently skip if no API key

    if jobs:
        print(f"   ✅ Adzuna: {len(jobs)} QA jobs")
    return jobs


def scrape_reed_rss() -> list:
    """Scrape Reed.co.uk RSS feed - works without API key."""
    jobs = []
    searches = [
        "qa+automation+engineer",
        "test+automation+engineer",
        "sdet",
        "selenium+engineer"
    ]
    for search in searches:
        try:
            url = f"https://www.reed.co.uk/api/1.0/search?keywords={search}&locationName=london&distancefromlocation=100"
            # Reed requires basic auth but RSS doesn't
            rss_url = f"https://www.reed.co.uk/jobs/{search.replace('+', '-')}-jobs.rss"
            resp = requests.get(rss_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                desc = clean_html(item.findtext("description", ""))
                if title and link:
                    jobs.append({
                        "id": f"reed_{hash(link) % 100000}",
                        "title": title,
                        "company": "",
                        "location": "United Kingdom",
                        "url": link,
                        "description": desc,
                        "source": "reed",
                        "category": "sponsorship_worldwide",
                        "type": "Outside India (Sponsorship)",
                        "date_posted": str(datetime.now().date()),
                        "scraped_at": datetime.now().isoformat(),
                    })
            time.sleep(1)
        except Exception as e:
            pass

    if jobs:
        print(f"   ✅ Reed UK: {len(jobs)} QA jobs")
    return jobs


def scrape_workingnomads() -> list:
    """Working Nomads - curated remote jobs, has free API."""
    jobs = []
    categories = ["testing", "qa", "software-development"]
    for cat in categories:
        try:
            url = f"https://www.workingnomads.com/api/exposed_jobs/?category={cat}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            for job in resp.json()[:30]:
                title = job.get("title", "")
                if not is_qa_job(title):
                    continue
                jobs.append({
                    "id": f"workingnomads_{job.get('id', '')}",
                    "title": title,
                    "company": job.get("company", ""),
                    "location": job.get("region", "Worldwide"),
                    "url": job.get("url", ""),
                    "description": job.get("description", "")[:3000],
                    "source": "workingnomads",
                    "category": "remote_worldwide",
                    "type": "Remote Worldwide",
                    "date_posted": job.get("pub_date", str(datetime.now().date())),
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(1)
        except Exception as e:
            pass

    if jobs:
        print(f"   ✅ Working Nomads: {len(jobs)} QA jobs")
    return jobs


def scrape_linkedin_rss() -> list:
    """LinkedIn RSS feeds for job searches - no login needed."""
    jobs = []
    searches = [
        ("QA Automation Engineer", "remote_worldwide"),
        ("SDET remote", "remote_worldwide"),
        ("Test Automation Engineer India remote", "india_remote"),
        ("QA Automation Engineer visa sponsorship", "sponsorship_worldwide"),
        ("Selenium automation engineer", "remote_worldwide"),
    ]

    for search_term, category in searches:
        try:
            encoded = requests.utils.quote(search_term)
            url = f"https://www.linkedin.com/jobs/search/?keywords={encoded}&f_WT=2&f_TPR=r86400"
            resp = requests.get(url, headers={
                **HEADERS,
                "Accept-Language": "en-US,en;q=0.9",
            }, timeout=20)

            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            job_cards = soup.select(".base-card, .job-search-card")

            for card in job_cards[:15]:
                title_el = card.select_one(".base-search-card__title, h3")
                company_el = card.select_one(".base-search-card__subtitle, h4")
                location_el = card.select_one(".job-search-card__location")
                link_el = card.select_one("a[href*='/jobs/view/']")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else ""
                url_job = link_el.get("href", "").split("?")[0] if link_el else ""

                if title and url_job:
                    # Build a meaningful description from available data
                    desc = f"Position: {title} at {company}. Location: {location}. Search: {search_term}."
                    jobs.append({
                        "id": f"linkedin_{hash(url_job) % 1000000}",
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url_job,
                        "description": desc,
                        "source": "linkedin",
                        "category": category,
                        "type": {
                            "remote_worldwide": "Remote Worldwide",
                            "india_remote": "India Remote",
                            "sponsorship_worldwide": "Outside India (Sponsorship)"
                        }.get(category, "Remote Worldwide"),
                        "date_posted": str(datetime.now().date()),
                        "scraped_at": datetime.now().isoformat(),
                    })
            time.sleep(3)
        except Exception as e:
            print(f"   ⚠️ LinkedIn {search_term[:30]}: {e}")

    seen = set()
    unique = []
    for job in jobs:
        if job["id"] not in seen and job["title"]:
            seen.add(job["id"])
            unique.append(job)

    if unique:
        print(f"   ✅ LinkedIn: {len(unique)} QA jobs")
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
    print("\n🌐 Scraping job boards...")

    results = {
        "remote_worldwide": [],
        "india_remote": [],
        "sponsorship_worldwide": [],
    }

    print("  📍 Remotive.io...")
    results["remote_worldwide"].extend(scrape_remotive())

    print("  📍 Arbeitnow (Europe + Visa)...")
    for job in scrape_arbeitnow():
        results[job.get("category", "remote_worldwide")].append(job)

    print("  📍 Jobicy...")
    results["remote_worldwide"].extend(scrape_jobicy())

    print("  📍 Working Nomads...")
    results["remote_worldwide"].extend(scrape_workingnomads())

    print("  📍 LinkedIn (no login)...")
    for job in scrape_linkedin_rss():
        results[job.get("category", "remote_worldwide")].append(job)

    print("  📍 Reed UK (Sponsorship)...")
    results["sponsorship_worldwide"].extend(scrape_reed_rss())

    print("  📍 Adzuna...")
    for job in scrape_adzuna():
        results[job.get("category", "remote_worldwide")].append(job)

    print("  📍 Indeed India (Remote)...")
    results["india_remote"].extend(scrape_indeed_india_rss())

    print("  📍 Indeed Worldwide (US/UK/AU/CA)...")
    for job in scrape_indeed_worldwide_rss():
        results[job.get("category", "remote_worldwide")].append(job)

    for cat in results:
        results[cat] = deduplicate(results[cat])
        print(f"  📊 {cat}: {len(results[cat])} unique jobs")

    total = sum(len(j) for j in results.values())
    print(f"\n  🎯 Total: {total} jobs scraped")
    return results


def scrape_indeed_india_rss() -> list:
    """
    Indeed India RSS feeds for QA jobs — works from cloud servers.
    No login needed, returns real job listings.
    """
    jobs = []
    seen = set()

    searches = [
        ("qa+automation+engineer", "QA Automation Engineer"),
        ("test+automation+engineer", "Test Automation Engineer"),
        ("sdet", "SDET"),
        ("selenium+automation", "Selenium Automation"),
        ("automation+tester", "Automation Tester"),
        ("qa+engineer+remote", "QA Engineer Remote"),
    ]

    for query, label in searches:
        try:
            # Indeed RSS feed for India remote jobs
            url = f"https://in.indeed.com/rss?q={query}&l=India&rbl=Remote&jt=fulltime&sort=date"
            resp = requests.get(url, headers={
                **HEADERS,
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            }, timeout=20)

            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            items = root.findall(".//item")

            for item in items[:15]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                desc = clean_html(item.findtext("description", ""))
                company_el = item.find("{http://www.indeed.com/about/feed}company")
                company = company_el.text.strip() if company_el is not None else ""
                pub_date = item.findtext("pubDate", str(datetime.now().date()))

                if not title or not link:
                    continue
                if link in seen:
                    continue
                seen.add(link)

                jobs.append({
                    "id": f"indeed_in_{hash(link) % 1000000}",
                    "title": title,
                    "company": company,
                    "location": "India (Remote)",
                    "url": link,
                    "description": desc or f"{title} at {company}. Remote QA role in India.",
                    "source": "indeed_india",
                    "category": "india_remote",
                    "type": "India Remote",
                    "date_posted": pub_date,
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(1)

        except Exception as e:
            print(f"   ⚠️ Indeed India '{label}': {e}")

    print(f"   ✅ Indeed India: {len(jobs)} India remote QA jobs")
    return jobs


def scrape_indeed_worldwide_rss() -> list:
    """
    Indeed worldwide RSS for remote QA jobs — visa sponsorship focus.
    """
    jobs = []
    seen = set()

    searches = [
        ("qa+automation+engineer+visa+sponsorship", "US"),
        ("test+automation+engineer+visa+sponsorship", "UK"),
        ("sdet+remote", "US"),
        ("qa+automation+engineer+remote", "US"),
        ("selenium+engineer+remote", "US"),
        ("qa+automation+engineer+remote", "GB"),
        ("automation+test+engineer+remote", "AU"),
        ("qa+engineer+remote", "CA"),
    ]

    for query, country_code in searches:
        try:
            domain = {
                "US": "www.indeed.com",
                "UK": "uk.indeed.com",
                "GB": "uk.indeed.com",
                "AU": "au.indeed.com",
                "CA": "ca.indeed.com",
            }.get(country_code, "www.indeed.com")

            url = f"https://{domain}/rss?q={query}&rbl=Remote&jt=fulltime&sort=date"
            resp = requests.get(url, headers={
                **HEADERS,
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            }, timeout=20)

            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            is_sponsorship = "visa+sponsorship" in query

            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                desc = clean_html(item.findtext("description", ""))
                company_el = item.find("{http://www.indeed.com/about/feed}company")
                company = company_el.text.strip() if company_el is not None else ""

                if not title or not link or link in seen:
                    continue
                if not is_qa_job(title):
                    continue
                seen.add(link)

                country_names = {"US": "United States", "UK": "United Kingdom", "GB": "United Kingdom", "AU": "Australia", "CA": "Canada"}
                jobs.append({
                    "id": f"indeed_{country_code}_{hash(link) % 1000000}",
                    "title": title,
                    "company": company,
                    "location": f"{country_names.get(country_code, country_code)} (Remote)",
                    "url": link,
                    "description": desc or f"{title} at {company}. Remote role in {country_code}.",
                    "source": "indeed",
                    "category": "sponsorship_worldwide" if is_sponsorship else "remote_worldwide",
                    "type": "Outside India (Sponsorship)" if is_sponsorship else "Remote Worldwide",
                    "date_posted": item.findtext("pubDate", str(datetime.now().date())),
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(1.5)

        except Exception as e:
            print(f"   ⚠️ Indeed {country_code}: {e}")

    print(f"   ✅ Indeed Worldwide: {len(jobs)} jobs")
    return jobs
