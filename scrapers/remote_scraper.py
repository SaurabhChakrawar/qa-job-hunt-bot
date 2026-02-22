"""
remote_scraper.py - HIGH IMPACT VERSION
Improvement 1: LinkedIn session-based scraping (more jobs)
Improvement 2: India-specific job boards (Naukri, Shine, Foundit, Instahyre)
Improvement 3: Full job description fetching before AI matching
"""

import requests
import json
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup
import time
import xml.etree.ElementTree as ET
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

QA_KEYWORDS = [
    "qa", "quality assurance", "test automation", "automation engineer",
    "sdet", "selenium", "playwright", "cypress", "appium", "testng",
    "software tester", "quality engineer", "test engineer", "automation tester",
    "qa analyst", "qa lead", "test lead", "automation lead"
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
        return str(html_text)[:3000]


# ─────────────────────────────────────────────────────────────
# IMPROVEMENT 3: Full description fetcher
# Visits each job URL to get complete description for better AI matching
# ─────────────────────────────────────────────────────────────

def fetch_full_description(url: str, source: str) -> str:
    """
    Fetch full job description from job URL.
    Returns enriched description for better Gemini scoring.
    """
    if not url or url == "#":
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "lxml")

        # Source-specific selectors
        selectors = {
            "remotive": [".job-description", "#job-description", ".description"],
            "arbeitnow": [".job-description", ".prose", "article"],
            "indeed_india": [".jobsearch-jobDescriptionText", "#jobDescriptionText"],
            "indeed": [".jobsearch-jobDescriptionText", "#jobDescriptionText"],
            "naukri": [".job-desc", ".dang-inner-html", ".jd-desc"],
            "shine": [".job-desc-detail", ".job-description"],
            "foundit": [".job-desc", ".job-description-text"],
            "instahyre": [".job-description", ".description-text"],
            "linkedin": [".description__text", ".show-more-less-html__markup"],
            "default": [
                ".job-description", "#job-description", ".description",
                ".job-details", ".jd", "article", "[class*='description']",
                "[class*='jobDescription']", "[id*='description']"
            ]
        }

        source_selectors = selectors.get(source, []) + selectors["default"]

        for selector in source_selectors:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 200:  # Only use if substantial content
                    return text[:3000]

        # Fallback: get main content area
        for tag in ["main", "article", ".content", "#content"]:
            el = soup.select_one(tag)
            if el:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 200:
                    return text[:3000]

        return ""
    except Exception:
        return ""


def enrich_jobs_with_descriptions(jobs: list, max_fetch: int = 40) -> list:
    """
    Fetch full descriptions for jobs that have short/empty descriptions.
    Improves AI matching accuracy significantly.
    """
    needs_fetch = [j for j in jobs if len(j.get("description", "")) < 300]
    has_desc = [j for j in jobs if len(j.get("description", "")) >= 300]

    print(f"   🔍 Fetching full descriptions for {min(len(needs_fetch), max_fetch)} jobs...")

    for i, job in enumerate(needs_fetch[:max_fetch]):
        url = job.get("url", "")
        source = job.get("source", "default")
        if url and url != "#":
            full_desc = fetch_full_description(url, source)
            if full_desc:
                job["description"] = full_desc
                job["description_enriched"] = True
        time.sleep(0.5)  # Be polite

    enriched = len([j for j in needs_fetch[:max_fetch] if j.get("description_enriched")])
    print(f"   ✅ Enriched {enriched} job descriptions")
    return has_desc + needs_fetch


# ─────────────────────────────────────────────────────────────
# IMPROVEMENT 1: LinkedIn - Multiple strategies
# ─────────────────────────────────────────────────────────────

def scrape_linkedin_public() -> list:
    """
    LinkedIn public job search - uses rotating search strategies
    to maximize jobs retrieved without login.
    """
    jobs = []
    seen = set()

    searches = [
        # (search_term, location_filter, category, geo_id)
        ("QA Automation Engineer", "India", "india_remote", "102713980"),
        ("SDET", "India", "india_remote", "102713980"),
        ("Test Automation Engineer", "India", "india_remote", "102713980"),
        ("Selenium Automation Engineer", "India", "india_remote", "102713980"),
        ("QA Automation Engineer", "", "remote_worldwide", ""),
        ("Test Automation Engineer", "", "remote_worldwide", ""),
        ("SDET remote", "", "remote_worldwide", ""),
        ("QA Automation visa sponsorship", "United States", "sponsorship_worldwide", "103644278"),
        ("Test Automation Engineer visa sponsorship", "United Kingdom", "sponsorship_worldwide", "101165590"),
        ("QA Engineer visa sponsorship", "Germany", "sponsorship_worldwide", "101282230"),
    ]

    for search_term, location, category, geo_id in searches:
        try:
            # LinkedIn public job search URL (no login)
            params = {
                "keywords": search_term,
                "f_WT": "2",  # Remote work type
                "f_TPR": "r86400",  # Last 24 hours
                "position": "1",
                "pageNum": "0",
            }
            if geo_id:
                params["geoId"] = geo_id

            url = "https://www.linkedin.com/jobs/search?" + "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())

            resp = requests.get(url, headers={
                **HEADERS,
                "Referer": "https://www.linkedin.com/jobs/",
            }, timeout=20)

            if resp.status_code != 200:
                time.sleep(2)
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Try multiple card selectors
            cards = (soup.select("div.base-card") or
                    soup.select("li.jobs-search-results__list-item") or
                    soup.select(".job-search-card") or
                    soup.select("[data-entity-urn]"))

            for card in cards[:20]:
                # Title
                title_el = (card.select_one("h3.base-search-card__title") or
                           card.select_one("h3") or
                           card.select_one(".job-search-card__title"))
                # Company
                company_el = (card.select_one("h4.base-search-card__subtitle") or
                             card.select_one("h4") or
                             card.select_one(".job-search-card__company-name"))
                # Location
                loc_el = (card.select_one(".job-search-card__location") or
                         card.select_one(".base-search-card__metadata"))
                # URL
                link_el = card.select_one("a[href*='/jobs/view/']")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc = loc_el.get_text(strip=True) if loc_el else location
                job_url = link_el.get("href", "").split("?")[0] if link_el else ""

                if not title or not job_url or job_url in seen:
                    continue
                if not is_qa_job(title):
                    continue

                seen.add(job_url)
                jobs.append({
                    "id": f"linkedin_{hash(job_url) % 1000000}",
                    "title": title,
                    "company": company,
                    "location": loc or location,
                    "url": job_url,
                    "description": f"{title} at {company}. Location: {loc}.",
                    "source": "linkedin",
                    "category": category,
                    "type": {
                        "india_remote": "India Remote",
                        "remote_worldwide": "Remote Worldwide",
                        "sponsorship_worldwide": "Outside India (Sponsorship)"
                    }.get(category, "Remote Worldwide"),
                    "date_posted": str(datetime.now().date()),
                    "scraped_at": datetime.now().isoformat(),
                })

            time.sleep(3)  # Important: LinkedIn rate limits aggressively

        except Exception as e:
            print(f"   ⚠️ LinkedIn '{search_term}': {e}")
            time.sleep(2)

    print(f"   ✅ LinkedIn: {len(jobs)} QA jobs")
    return jobs


# ─────────────────────────────────────────────────────────────
# IMPROVEMENT 2: India-specific job boards
# ─────────────────────────────────────────────────────────────

def scrape_naukri() -> list:
    """Naukri.com - India's #1 job board. Scrapes via their search API."""
    jobs = []
    seen = set()

    searches = [
        "qa automation engineer",
        "test automation engineer",
        "sdet",
        "selenium automation",
        "automation tester",
    ]

    for query in searches:
        try:
            # Naukri's search endpoint
            url = "https://www.naukri.com/jobapi/v3/search"
            params = {
                "noOfResults": 20,
                "urlType": "search_by_keyword",
                "searchType": "adv",
                "keyword": query,
                "jobAge": 3,  # Last 3 days
                "experience": "1,10",
                "workType": "5",  # 5 = Work from home
                "src": "jobsearchDesk",
            }
            headers = {
                **HEADERS,
                "appid": "109",
                "systemid": "109",
                "Referer": "https://www.naukri.com/",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=20)

            if resp.status_code != 200:
                # Fallback: scrape HTML
                html_url = f"https://www.naukri.com/{query.replace(' ', '-')}-jobs?jobAge=3&jobType=wfh"
                resp2 = requests.get(html_url, headers=HEADERS, timeout=20)
                if resp2.status_code == 200:
                    soup = BeautifulSoup(resp2.text, "lxml")
                    for card in soup.select(".jobTuple, [class*='jobTuple'], .job-tuple")[:15]:
                        title_el = card.select_one("a.title, [class*='jobTitle']")
                        company_el = card.select_one("[class*='companyName'], .company-name")
                        link_el = card.select_one("a[href*='naukri.com']")
                        title = title_el.get_text(strip=True) if title_el else ""
                        company = company_el.get_text(strip=True) if company_el else ""
                        job_url = link_el.get("href", "") if link_el else ""
                        if title and job_url and job_url not in seen:
                            seen.add(job_url)
                            jobs.append({
                                "id": f"naukri_{hash(job_url) % 1000000}",
                                "title": title,
                                "company": company,
                                "location": "India (Remote)",
                                "url": job_url,
                                "description": f"{title} at {company}. Remote QA role in India.",
                                "source": "naukri",
                                "category": "india_remote",
                                "type": "India Remote",
                                "date_posted": str(datetime.now().date()),
                                "scraped_at": datetime.now().isoformat(),
                            })
                continue

            data = resp.json()
            for job in data.get("jobDetails", []):
                job_id = str(job.get("jobId", ""))
                job_url = f"https://www.naukri.com/job-listings-{job_id}"
                if job_url in seen:
                    continue
                seen.add(job_url)
                title = job.get("title", "")
                company = job.get("companyName", "")
                desc = clean_html(job.get("jobDescription", ""))
                jobs.append({
                    "id": f"naukri_{job_id}",
                    "title": title,
                    "company": company,
                    "location": "India (Remote)",
                    "url": job_url,
                    "description": desc or f"{title} at {company}. WFH QA role.",
                    "source": "naukri",
                    "category": "india_remote",
                    "type": "India Remote",
                    "salary": job.get("salary", ""),
                    "date_posted": str(datetime.now().date()),
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(1.5)

        except Exception as e:
            print(f"   ⚠️ Naukri '{query}': {e}")

    print(f"   ✅ Naukri: {len(jobs)} India remote jobs")
    return jobs


def scrape_shine() -> list:
    """Shine.com - popular India IT job board."""
    jobs = []
    seen = set()

    searches = ["qa-automation-engineer", "test-automation-engineer", "sdet", "selenium-engineer"]

    for query in searches:
        try:
            url = f"https://www.shine.com/job-search/{query}-jobs?work_from_home=true&q={query}"
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select(".jobCard, .job-card, [class*='jobCard']")

            for card in cards[:15]:
                title_el = card.select_one("h2 a, h3 a, .job-title a")
                company_el = card.select_one(".company-name, [class*='company']")
                link_el = card.select_one("a[href*='shine.com/jobs']")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                job_url = link_el.get("href", "") if link_el else ""

                if not job_url.startswith("http"):
                    job_url = "https://www.shine.com" + job_url

                if title and job_url and job_url not in seen:
                    seen.add(job_url)
                    jobs.append({
                        "id": f"shine_{hash(job_url) % 1000000}",
                        "title": title,
                        "company": company,
                        "location": "India (Remote)",
                        "url": job_url,
                        "description": f"{title} at {company}. Remote/WFH QA role in India.",
                        "source": "shine",
                        "category": "india_remote",
                        "type": "India Remote",
                        "date_posted": str(datetime.now().date()),
                        "scraped_at": datetime.now().isoformat(),
                    })
            time.sleep(2)

        except Exception as e:
            print(f"   ⚠️ Shine '{query}': {e}")

    print(f"   ✅ Shine.com: {len(jobs)} India remote jobs")
    return jobs


def scrape_foundit() -> list:
    """Foundit (formerly Monster India) - good for QA roles."""
    jobs = []
    seen = set()

    try:
        # Foundit API endpoint
        url = "https://www.foundit.in/middleware/jobsearch/v2/search"
        payload = {
            "query": "qa automation engineer",
            "locations": [],
            "experienceRanges": [{"minExperience": 1, "maxExperience": 10}],
            "workModes": ["remote"],
            "pageNo": 1,
            "limit": 30,
            "sort": "date",
        }
        resp = requests.post(url, json=payload, headers={
            **HEADERS,
            "Content-Type": "application/json",
        }, timeout=20)

        if resp.status_code == 200:
            for job in resp.json().get("jobSearchResponse", {}).get("data", []):
                title = job.get("jobTitle", "")
                if not is_qa_job(title):
                    continue
                job_url = f"https://www.foundit.in/job/{job.get('jobId', '')}"
                if job_url in seen:
                    continue
                seen.add(job_url)
                jobs.append({
                    "id": f"foundit_{job.get('jobId', '')}",
                    "title": title,
                    "company": job.get("companyName", ""),
                    "location": "India (Remote)",
                    "url": job_url,
                    "description": clean_html(job.get("jobDescription", "")),
                    "source": "foundit",
                    "category": "india_remote",
                    "type": "India Remote",
                    "salary": job.get("salaryDetails", ""),
                    "date_posted": str(datetime.now().date()),
                    "scraped_at": datetime.now().isoformat(),
                })
        else:
            # HTML fallback
            html_url = "https://www.foundit.in/srp/results?query=qa+automation+engineer&locations=&experienceRanges=1~10&workModes=remote"
            resp2 = requests.get(html_url, headers=HEADERS, timeout=20)
            if resp2.status_code == 200:
                soup = BeautifulSoup(resp2.text, "lxml")
                for card in soup.select(".card, .job-card, [class*='jobCard']")[:15]:
                    title_el = card.select_one("h3 a, .job-title")
                    company_el = card.select_one(".company-name")
                    link_el = card.select_one("a[href*='foundit.in']")
                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    job_url = link_el.get("href", "") if link_el else ""
                    if title and job_url and job_url not in seen and is_qa_job(title):
                        seen.add(job_url)
                        jobs.append({
                            "id": f"foundit_{hash(job_url) % 1000000}",
                            "title": title,
                            "company": company,
                            "location": "India (Remote)",
                            "url": job_url if job_url.startswith("http") else f"https://www.foundit.in{job_url}",
                            "description": f"{title} at {company}. Remote QA role.",
                            "source": "foundit",
                            "category": "india_remote",
                            "type": "India Remote",
                            "date_posted": str(datetime.now().date()),
                            "scraped_at": datetime.now().isoformat(),
                        })

    except Exception as e:
        print(f"   ⚠️ Foundit: {e}")

    print(f"   ✅ Foundit: {len(jobs)} India remote jobs")
    return jobs


def scrape_instahyre() -> list:
    """Instahyre - startup-focused, good salaries, India remote."""
    jobs = []
    seen = set()

    try:
        searches = ["qa automation", "test automation", "sdet"]
        for query in searches:
            url = f"https://www.instahyre.com/api/v1/opportunity/?format=json&search={requests.utils.quote(query)}&work_from_home=true"
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            for job in resp.json().get("results", [])[:15]:
                title = job.get("title", "")
                if not is_qa_job(title):
                    continue
                job_id = str(job.get("id", ""))
                job_url = f"https://www.instahyre.com/job-{job_id}/"
                if job_url in seen:
                    continue
                seen.add(job_url)
                employer = job.get("employer", {})
                jobs.append({
                    "id": f"instahyre_{job_id}",
                    "title": title,
                    "company": employer.get("name", ""),
                    "location": "India (Remote)",
                    "url": job_url,
                    "description": clean_html(job.get("description", "")),
                    "source": "instahyre",
                    "category": "india_remote",
                    "type": "India Remote",
                    "salary": f"₹{job.get('min_salary','')} - ₹{job.get('max_salary','')} LPA" if job.get("min_salary") else "",
                    "date_posted": str(datetime.now().date()),
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(1)

    except Exception as e:
        print(f"   ⚠️ Instahyre: {e}")

    print(f"   ✅ Instahyre: {len(jobs)} India remote jobs")
    return jobs


# ─────────────────────────────────────────────────────────────
# Existing reliable sources (kept from before)
# ─────────────────────────────────────────────────────────────

def scrape_remotive() -> list:
    jobs = []
    seen = set()
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
                if not is_qa_job(title, desc[:300]):
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
    jobs = []
    try:
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
                if not is_qa_job(title, desc[:300]):
                    continue
                visa = job.get("visa_sponsorship", False)
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
    jobs = []
    seen = set()
    tags = ["qa", "testing", "quality-assurance", "test-automation", "sdet", "selenium", "software-testing", "automation"]
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
                jobs.append({
                    "id": f"jobicy_{jid}",
                    "title": title,
                    "company": job.get("companyName", ""),
                    "location": job.get("jobGeo", "Worldwide"),
                    "url": job.get("url", ""),
                    "description": clean_html(job.get("jobDescription", "")),
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


def scrape_indeed_india_rss() -> list:
    jobs = []
    seen = set()
    searches = [
        "qa+automation+engineer", "test+automation+engineer",
        "sdet", "selenium+automation", "automation+tester"
    ]
    for query in searches:
        try:
            url = f"https://in.indeed.com/rss?q={query}&l=India&rbl=Remote&jt=fulltime&sort=date"
            resp = requests.get(url, headers={**HEADERS, "Accept": "application/rss+xml,*/*"}, timeout=20)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:15]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                desc = clean_html(item.findtext("description", ""))
                company_el = item.find("{http://www.indeed.com/about/feed}company")
                company = company_el.text.strip() if company_el is not None else ""
                if not title or not link or link in seen:
                    continue
                seen.add(link)
                jobs.append({
                    "id": f"indeed_in_{hash(link) % 1000000}",
                    "title": title,
                    "company": company,
                    "location": "India (Remote)",
                    "url": link,
                    "description": desc or f"{title} at {company}.",
                    "source": "indeed_india",
                    "category": "india_remote",
                    "type": "India Remote",
                    "date_posted": item.findtext("pubDate", str(datetime.now().date())),
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(1)
        except Exception as e:
            print(f"   ⚠️ Indeed India: {e}")
    print(f"   ✅ Indeed India: {len(jobs)} jobs")
    return jobs


def scrape_indeed_worldwide_rss() -> list:
    jobs = []
    seen = set()
    searches = [
        ("qa+automation+engineer+visa+sponsorship", "US", "sponsorship_worldwide"),
        ("sdet+remote", "US", "remote_worldwide"),
        ("qa+automation+engineer+remote", "GB", "sponsorship_worldwide"),
        ("automation+test+engineer+remote", "AU", "sponsorship_worldwide"),
        ("qa+engineer+remote", "CA", "sponsorship_worldwide"),
    ]
    domains = {"US": "www.indeed.com", "GB": "uk.indeed.com", "AU": "au.indeed.com", "CA": "ca.indeed.com"}
    country_names = {"US": "United States", "GB": "United Kingdom", "AU": "Australia", "CA": "Canada"}

    for query, country, category in searches:
        try:
            domain = domains.get(country, "www.indeed.com")
            url = f"https://{domain}/rss?q={query}&rbl=Remote&jt=fulltime&sort=date"
            resp = requests.get(url, headers={**HEADERS, "Accept": "application/rss+xml,*/*"}, timeout=20)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                if not title or not link or link in seen or not is_qa_job(title):
                    continue
                seen.add(link)
                company_el = item.find("{http://www.indeed.com/about/feed}company")
                company = company_el.text.strip() if company_el is not None else ""
                jobs.append({
                    "id": f"indeed_{country}_{hash(link) % 1000000}",
                    "title": title,
                    "company": company,
                    "location": f"{country_names.get(country, country)} (Remote)",
                    "url": link,
                    "description": clean_html(item.findtext("description", "")),
                    "source": "indeed",
                    "category": category,
                    "type": "Outside India (Sponsorship)" if category == "sponsorship_worldwide" else "Remote Worldwide",
                    "date_posted": item.findtext("pubDate", str(datetime.now().date())),
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(1.5)
        except Exception as e:
            print(f"   ⚠️ Indeed {country}: {e}")
    print(f"   ✅ Indeed Worldwide: {len(jobs)} jobs")
    return jobs


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
    print("\n🌐 Scraping job boards (High Impact Version)...")

    results = {
        "remote_worldwide": [],
        "india_remote": [],
        "sponsorship_worldwide": [],
    }

    # Remote worldwide sources
    print("  📍 Remotive.io...")
    results["remote_worldwide"].extend(scrape_remotive())

    print("  📍 Arbeitnow (Europe + Visa)...")
    for job in scrape_arbeitnow():
        results[job.get("category", "remote_worldwide")].append(job)

    print("  📍 Jobicy...")
    results["remote_worldwide"].extend(scrape_jobicy())

    print("  📍 Indeed Worldwide (US/UK/AU/CA)...")
    for job in scrape_indeed_worldwide_rss():
        results[job.get("category", "remote_worldwide")].append(job)

    # IMPROVEMENT 1: Better LinkedIn
    print("  📍 LinkedIn (public search)...")
    for job in scrape_linkedin_public():
        results[job.get("category", "remote_worldwide")].append(job)

    # IMPROVEMENT 2: India job boards
    print("  📍 Indeed India (Remote)...")
    results["india_remote"].extend(scrape_indeed_india_rss())

    print("  📍 Naukri.com...")
    results["india_remote"].extend(scrape_naukri())

    print("  📍 Shine.com...")
    results["india_remote"].extend(scrape_shine())

    print("  📍 Foundit (Monster India)...")
    results["india_remote"].extend(scrape_foundit())

    print("  📍 Instahyre...")
    results["india_remote"].extend(scrape_instahyre())

    # Deduplicate each category
    for cat in results:
        results[cat] = deduplicate(results[cat])

    # IMPROVEMENT 3: Fetch full descriptions for better AI matching
    print("\n  🔍 Enriching job descriptions for better AI matching...")
    for cat in results:
        if results[cat]:
            results[cat] = enrich_jobs_with_descriptions(results[cat], max_fetch=30)

    # Final stats
    for cat in results:
        print(f"  📊 {cat}: {len(results[cat])} unique jobs")

    total = sum(len(j) for j in results.values())
    print(f"\n  🎯 Total: {total} jobs ready for AI matching")
    return results
