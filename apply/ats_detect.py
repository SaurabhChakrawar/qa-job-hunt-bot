"""
ats_detect.py
Resolves job board URLs to actual ATS application forms.
Detects ATS type (Greenhouse, Lever, etc.) from URL patterns.
"""

import re

# ATS URL patterns
ATS_PATTERNS = {
    "greenhouse": [
        r"boards\.greenhouse\.io",
        r"job-boards\.greenhouse\.io",
        r"greenhouse\.io/.*?/jobs",
    ],
    "lever": [
        r"jobs\.lever\.co",
        r"lever\.co/.*/apply",
    ],
}


def detect_ats_type(url: str) -> str:
    """
    Detect ATS type from URL pattern.
    Returns: 'greenhouse', 'lever', or 'unknown'
    """
    if not url:
        return "unknown"
    url_lower = url.lower()
    for ats_name, patterns in ATS_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url_lower):
                return ats_name
    return "unknown"


async def resolve_apply_url(page, job_url: str) -> str:
    """
    Visit a job board page and find the actual application URL.
    Follows links to Greenhouse, Lever, etc.

    Returns the ATS apply URL, or empty string if not found.
    """
    if not job_url:
        return ""

    # If the URL is already an ATS URL, return it directly
    if detect_ats_type(job_url) != "unknown":
        return job_url

    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        # Strategy 1: Look for direct ATS links in href attributes
        apply_links = await page.query_selector_all("a[href]")
        for link in apply_links:
            href = await link.get_attribute("href")
            if href and detect_ats_type(href) != "unknown":
                return href

        # Strategy 2: Look for "Apply" buttons/links and extract their href
        apply_selectors = [
            "a[href*='greenhouse']",
            "a[href*='lever.co']",
            "a[href*='apply']",
            "a:has-text('Apply')",
            "a:has-text('Apply Now')",
            "a:has-text('Apply for this')",
            "button:has-text('Apply')",
        ]

        for selector in apply_selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    tag = await el.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "a":
                        href = await el.get_attribute("href")
                        if href and detect_ats_type(href) != "unknown":
                            return href
                        # If it's an apply link but not ATS, click and check redirect
                        if href and "apply" in href.lower():
                            await el.click()
                            await page.wait_for_timeout(3000)
                            new_url = page.url
                            if detect_ats_type(new_url) != "unknown":
                                return new_url
                            await page.go_back()
                            await page.wait_for_timeout(1000)
                    elif tag == "button":
                        # Click button and check if it redirects to ATS
                        await el.click()
                        await page.wait_for_timeout(3000)
                        new_url = page.url
                        if detect_ats_type(new_url) != "unknown":
                            return new_url
                        # Check for new window/popup
                        pages = page.context.pages
                        if len(pages) > 1:
                            new_page = pages[-1]
                            new_page_url = new_page.url
                            if detect_ats_type(new_page_url) != "unknown":
                                await new_page.close()
                                return new_page_url
                            await new_page.close()
                        await page.go_back()
                        await page.wait_for_timeout(1000)
            except Exception:
                continue

        # Strategy 3: Check if page itself redirected to an ATS
        current_url = page.url
        if detect_ats_type(current_url) != "unknown":
            return current_url

        return ""

    except Exception as e:
        print(f"      ⚠️ URL resolve error: {e}")
        return ""
