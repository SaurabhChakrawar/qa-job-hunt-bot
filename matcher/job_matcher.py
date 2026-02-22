"""
job_matcher.py
Uses Google Gemini AI (FREE) to score each job against your resume profile.
Returns match score 0-100, reasons, and missing skills.

Free tier: 15 requests/min, 1500 requests/day
For 100 jobs/day this is perfectly sufficient.
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


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_profile():
    with open(PROFILE_PATH) as f:
        return json.load(f)


def clean_json_response(raw: str) -> str:
    """Strip markdown code fences if Gemini adds them."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return raw.strip()


def match_job_to_profile(job: dict, profile: dict, model) -> dict:
    """
    Match a single job to the candidate profile using Gemini.
    Returns enriched job dict with match_score, match_reasons, missing_skills.
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

    prompt = f"""You are an expert QA/Testing job recruiter. Score how well this candidate matches this job.

CANDIDATE PROFILE:
{json.dumps(profile_summary, indent=2)}

JOB POSTING:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Description: {job.get('description', 'No description available')[:2000]}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "match_score": 75,
  "match_reasons": ["Has Selenium experience", "Python matches requirement", "3+ years matches"],
  "missing_skills": ["Cypress", "K6 performance testing"],
  "nice_to_have_present": ["JIRA", "Agile methodology"],
  "recommendation": "APPLY",
  "recommendation_reason": "Strong match on core automation skills",
  "seniority_match": true,
  "remote_type": "fully_remote"
}}

recommendation must be one of: APPLY, MAYBE, SKIP
remote_type must be one of: fully_remote, hybrid, onsite, not_specified

Scoring:
- 80-100: Excellent match
- 60-79: Good match
- 40-59: Partial match
- Below 40: Poor match"""

    try:
        response = model.generate_content(prompt)
        raw = clean_json_response(response.text)
        match_data = json.loads(raw)

        job.update({
            "match_score": match_data.get("match_score", 0),
            "match_reasons": match_data.get("match_reasons", []),
            "missing_skills": match_data.get("missing_skills", []),
            "nice_to_have_present": match_data.get("nice_to_have_present", []),
            "recommendation": match_data.get("recommendation", "SKIP"),
            "recommendation_reason": match_data.get("recommendation_reason", ""),
            "seniority_match": match_data.get("seniority_match", False),
            "remote_type": match_data.get("remote_type", "not_specified"),
        })
    except Exception as e:
        job.update({
            "match_score": 0,
            "match_reasons": [],
            "missing_skills": [],
            "recommendation": "SKIP",
            "match_error": str(e)
        })

    return job


def batch_match_jobs(jobs: list, min_score: int = 60) -> list:
    """Match a list of jobs and return only those above min_score."""
    config = load_config()
    profile = load_profile()
    api_key = config["api_keys"]["gemini_api_key"]

    genai.configure(api_key=api_key)
    # gemini-1.5-flash is free tier, fast, and handles JSON well
    model = genai.GenerativeModel("gemini-1.5-flash")

    matched = []
    print(f"🤖 Matching {len(jobs)} jobs with Gemini AI (Free)...")

    for i, job in enumerate(jobs, 1):
        print(f"   [{i}/{len(jobs)}] {job.get('title', '?')} @ {job.get('company', '?')}...")
        matched_job = match_job_to_profile(job, profile, model)
        if matched_job.get("match_score", 0) >= min_score:
            matched.append(matched_job)

        # Rate limit: free tier allows 15 req/min
        # Sleep 4 seconds between requests to stay safe (15 req/min = 1 req per 4s)
        if i % 14 == 0:
            print("   ⏳ Rate limit pause (4s)...")
            time.sleep(1)

    matched.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    print(f"✅ Found {len(matched)} jobs above {min_score}% match threshold")
    return matched


def generate_skill_gap_analysis(all_jobs: list, profile: dict, api_key: str) -> dict:
    """Analyze all job requirements to find skill gaps and trending skills."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")  # Use Pro for better analysis (still free tier)

    # Collect all missing skills from near-matches
    all_missing = []
    near_matches = [j for j in all_jobs if j.get("match_score", 0) >= 50]
    for job in near_matches[:20]:
        all_missing.extend(job.get("missing_skills", []))

    missing_counts = Counter(all_missing).most_common(20)

    prompt = f"""You are a QA/Test Automation career coach.

Candidate Profile:
- Level: {profile.get('current_level', 'mid')}
- Experience: {profile.get('experience_years', 0)} years
- Current Skills: {', '.join(profile['tech_skills'].get('test_frameworks', []) + profile['tech_skills'].get('programming_languages', []))}

Most frequently required skills they are missing (from {len(near_matches)} job postings analyzed):
{json.dumps(missing_counts, indent=2)}

Provide a skill gap analysis as a structured JSON (no markdown):
{{
  "critical_skills_to_learn": [
    {{
      "skill": "Cypress",
      "reason": "Missing in 8 jobs, modern JS testing framework",
      "learning_time": "2-4 weeks",
      "resources": ["cypress.io/docs", "Udemy Cypress Bootcamp"]
    }}
  ],
  "trending_in_qa": ["AI-powered testing", "Shift-left testing", "Contract testing with Pact"],
  "certifications_recommended": [
    {{
      "cert": "ISTQB Advanced",
      "reason": "Mentioned in 40% of senior roles",
      "url": "istqb.org"
    }}
  ],
  "quick_wins": ["Learn basic K6 for performance testing - 1 week", "Add Docker knowledge - 3 days"],
  "career_advice": "2-3 sentence personalized career growth advice"
}}

Return ONLY the JSON."""

    try:
        response = model.generate_content(prompt)
        raw = clean_json_response(response.text)
        return json.loads(raw)
    except Exception as e:
        return {
            "error": str(e),
            "critical_skills_to_learn": [],
            "trending_in_qa": [],
            "quick_wins": [],
            "career_advice": "Skill gap analysis unavailable today. Check logs."
        }
