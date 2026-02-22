"""
job_matcher.py
Uses Google Gemini AI (FREE) to score each job against your resume profile.
Returns match score 0-100, reasons, and missing skills.

Free tier: 15 requests/min, 1500 requests/day
"""

import google.generativeai as genai
import json
import os
import sys
import time
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.json")
PROFILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "resume_profile.json")

# QA keywords for title-based fallback scoring
QA_TITLE_KEYWORDS = [
    "qa automation", "test automation", "sdet", "quality assurance",
    "selenium", "playwright", "cypress", "appium", "software tester",
    "automation engineer", "quality engineer", "test engineer", "qa engineer",
    "qa analyst", "automation tester", "software testing"
]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_profile():
    with open(PROFILE_PATH) as f:
        return json.load(f)


def clean_json_response(raw: str) -> str:
    """Strip markdown code fences if Gemini adds them."""
    raw = raw.strip()
    # Remove ```json or ``` fences
    if "```" in raw:
        lines = raw.split("\n")
        cleaned = []
        in_fence = False
        for line in lines:
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            cleaned.append(line)
        raw = "\n".join(cleaned)
    return raw.strip()


def title_based_score(job: dict, profile: dict) -> dict:
    """
    Fallback scoring based on job title matching alone.
    Used when Gemini fails or description is too short.
    """
    title = job.get("title", "").lower()
    score = 0
    reasons = []
    missing = []

    # Check if title matches QA domain
    qa_match = any(kw in title for kw in QA_TITLE_KEYWORDS)
    if qa_match:
        score += 50
        reasons.append(f"Job title matches QA/Testing domain")

    # Check seniority match
    exp = profile.get("experience_years", 0)
    level = profile.get("current_level", "mid")

    if exp >= 4 and any(w in title for w in ["senior", "lead", "principal"]):
        score += 20
        reasons.append("Seniority level matches your experience")
    elif exp <= 3 and any(w in title for w in ["junior", "associate"]):
        score += 20
        reasons.append("Junior level matches your experience")
    elif not any(w in title for w in ["senior", "lead", "junior", "principal"]):
        score += 15
        reasons.append("Mid-level position matches your profile")

    # Check specific tech in title
    profile_skills = (
        profile.get("tech_skills", {}).get("test_frameworks", []) +
        profile.get("tech_skills", {}).get("programming_languages", [])
    )
    for skill in profile_skills:
        if skill.lower() in title:
            score += 10
            reasons.append(f"{skill} mentioned in job title")
            break

    # Common missing skills for QA roles
    if "cypress" not in [s.lower() for s in profile_skills]:
        missing.append("Cypress (popular JS framework)")
    if "playwright" not in [s.lower() for s in profile_skills]:
        missing.append("Playwright")
    if "k6" not in [s.lower() for s in profile_skills]:
        missing.append("K6 performance testing")

    return {
        "match_score": min(score, 85),  # Cap fallback at 85
        "match_reasons": reasons if reasons else ["QA role matching your profile"],
        "missing_skills": missing[:3],
        "nice_to_have_present": [],
        "recommendation": "APPLY" if score >= 50 else "MAYBE",
        "recommendation_reason": "Title-based match (AI scoring unavailable)",
        "seniority_match": True,
        "remote_type": "not_specified",
        "scored_by": "title_fallback"
    }


def match_job_to_profile(job: dict, profile: dict, model) -> dict:
    """
    Match a single job using Gemini AI.
    Falls back to title-based scoring if Gemini fails.
    """
    profile_summary = {
        "experience_years": profile.get("experience_years", 0),
        "current_level": profile.get("current_level", "mid"),
        "job_titles": profile.get("job_titles", []),
        "test_frameworks": profile["tech_skills"].get("test_frameworks", []),
        "programming_languages": profile["tech_skills"].get("programming_languages", []),
        "api_testing": profile["tech_skills"].get("api_testing", []),
        "ci_cd": profile["tech_skills"].get("ci_cd", []),
        "cloud": profile["tech_skills"].get("cloud", []),
        "methodologies": profile.get("methodologies", []),
        "certifications": profile.get("certifications", []),
        "domains_tested": profile.get("domains_tested", []),
    }

    description = job.get("description", "").strip()
    title = job.get("title", "N/A")

    # If description is very short, use title-based fallback directly
    if len(description) < 100:
        print(f"      ℹ️  Short description — using title-based scoring")
        fallback = title_based_score(job, profile)
        job.update(fallback)
        return job

    prompt = f"""You are an expert QA/Testing job recruiter. Score how well this candidate matches this job.

CANDIDATE PROFILE:
{json.dumps(profile_summary, indent=2)}

JOB POSTING:
Title: {title}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Description: {description[:2000]}

IMPORTANT RULES:
- If the job is clearly a QA/Testing/Automation role and candidate has QA experience, score minimum 50
- Score based on skill overlap, experience match, and title relevance
- A title like "QA Automation Engineer" with Selenium/Java skills = at least 65 score

Return ONLY this exact JSON structure, no markdown, no explanation:
{{
  "match_score": 75,
  "match_reasons": ["Has Selenium which job requires", "Java matches", "5yr exp fits senior role"],
  "missing_skills": ["Cypress", "K6"],
  "nice_to_have_present": ["JIRA", "Agile"],
  "recommendation": "APPLY",
  "recommendation_reason": "Strong match on core automation skills",
  "seniority_match": true,
  "remote_type": "fully_remote"
}}

recommendation: APPLY (score 60+), MAYBE (40-59), SKIP (below 40)
remote_type: fully_remote, hybrid, onsite, not_specified"""

    try:
        response = model.generate_content(prompt)
        raw = clean_json_response(response.text)

        # Try to parse JSON
        try:
            match_data = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                match_data = json.loads(json_match.group())
            else:
                raise ValueError(f"No valid JSON in response: {raw[:200]}")

        job.update({
            "match_score": int(match_data.get("match_score", 0)),
            "match_reasons": match_data.get("match_reasons", []),
            "missing_skills": match_data.get("missing_skills", []),
            "nice_to_have_present": match_data.get("nice_to_have_present", []),
            "recommendation": match_data.get("recommendation", "MAYBE"),
            "recommendation_reason": match_data.get("recommendation_reason", ""),
            "seniority_match": match_data.get("seniority_match", False),
            "remote_type": match_data.get("remote_type", "not_specified"),
            "scored_by": "gemini",
        })
        print(f"      ✅ Score: {job['match_score']}% ({job['recommendation']})")

    except Exception as e:
        print(f"      ⚠️  Gemini error: {str(e)[:80]} — using title fallback")
        # Use title-based fallback
        fallback = title_based_score(job, profile)
        job.update(fallback)

    return job


def batch_match_jobs(jobs: list, min_score: int = 0) -> list:
    """Match all jobs and return those above min_score."""
    config = load_config()
    profile = load_profile()
    api_key = config["api_keys"]["gemini_api_key"]

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    matched = []
    errors = 0
    print(f"🤖 Matching {len(jobs)} jobs with Gemini AI (Free)...")

    for i, job in enumerate(jobs, 1):
        print(f"   [{i}/{len(jobs)}] {job.get('title', '?')[:40]} @ {job.get('company', '?')[:20]}...")
        matched_job = match_job_to_profile(job, profile, model)
        score = matched_job.get("match_score", 0)

        if score >= min_score:
            matched.append(matched_job)

        if matched_job.get("match_error"):
            errors += 1

        # Rate limit: 15 req/min free tier = 1 per 4 seconds
        # Only sleep every 10 jobs to speed things up
        if i % 10 == 0:
            print(f"   ⏳ Pausing 3s for rate limit...")
            time.sleep(3)

    matched.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    print(f"\n✅ Matched: {len(matched)} jobs (score >= {min_score}%)")
    if errors:
        print(f"⚠️  {errors} jobs used title-based fallback scoring")
    return matched


def generate_skill_gap_analysis(all_jobs: list, profile: dict, api_key: str) -> dict:
    """Analyze job requirements to find skill gaps."""
    genai.configure(api_key=api_key)

    # Try Pro first, fall back to Flash
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
    except:
        model = genai.GenerativeModel("gemini-1.5-flash")

    all_missing = []
    near_matches = [j for j in all_jobs if j.get("match_score", 0) >= 30]
    for job in near_matches[:20]:
        all_missing.extend(job.get("missing_skills", []))

    missing_counts = Counter(all_missing).most_common(15)

    # If no near matches, generate generic QA advice
    if not near_matches:
        missing_counts = [
            ("Cypress", 5), ("Playwright", 4), ("K6", 3),
            ("Docker", 3), ("AWS", 2), ("GitHub Actions", 2)
        ]

    prompt = f"""You are a QA/Test Automation career coach for someone with {profile.get('experience_years', 3)} years experience.

Current Skills: {', '.join(profile['tech_skills'].get('test_frameworks', []) + profile['tech_skills'].get('programming_languages', []))}

Skills frequently required in jobs but missing from profile:
{json.dumps(missing_counts, indent=2)}

Return ONLY this JSON (no markdown):
{{
  "critical_skills_to_learn": [
    {{
      "skill": "Cypress",
      "reason": "In-demand modern JS testing framework",
      "learning_time": "2-4 weeks",
      "resources": ["cypress.io/docs", "Udemy Cypress course"]
    }}
  ],
  "trending_in_qa": ["AI-powered testing", "Shift-left testing", "API contract testing"],
  "certifications_recommended": [
    {{
      "cert": "ISTQB Advanced Test Automation Engineer",
      "reason": "Boosts credibility for senior roles",
      "url": "istqb.org"
    }}
  ],
  "quick_wins": ["Learn K6 basics for performance testing - 1 week", "Add Docker to your skill set - 3 days"],
  "career_advice": "With 5 years of Selenium/Java experience, you are well positioned for senior QA roles globally. Focus on learning Playwright or Cypress to stay current with modern testing trends."
}}"""

    try:
        response = model.generate_content(prompt)
        raw = clean_json_response(response.text)
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️ Skill gap analysis error: {e}")
        return {
            "critical_skills_to_learn": [
                {"skill": "Cypress", "reason": "Modern JS testing framework, high demand", "learning_time": "2-4 weeks", "resources": ["cypress.io/docs"]},
                {"skill": "Playwright", "reason": "Microsoft's modern automation tool", "learning_time": "2-3 weeks", "resources": ["playwright.dev"]},
                {"skill": "K6", "reason": "Performance testing, often required", "learning_time": "1 week", "resources": ["k6.io/docs"]},
            ],
            "trending_in_qa": ["AI-powered testing", "Shift-left testing", "API contract testing with Pact"],
            "certifications_recommended": [
                {"cert": "ISTQB Advanced", "reason": "Valued for senior roles", "url": "istqb.org"}
            ],
            "quick_wins": ["Add Docker basics to your profile", "Learn GitHub Actions for CI/CD"],
            "career_advice": "With 5 years of Selenium/Java experience, focus on modern frameworks like Playwright or Cypress to expand your opportunities globally."
        }
