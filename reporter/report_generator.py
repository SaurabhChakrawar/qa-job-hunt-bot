"""
report_generator.py
Modern, beautiful HTML email report - fully self-contained, no Google Sheets needed.
"""

import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_score_color(score: int) -> str:
    if score >= 80: return "#16a34a"
    elif score >= 60: return "#d97706"
    else: return "#6b7280"


def get_score_bg(score: int) -> str:
    if score >= 80: return "#f0fdf4"
    elif score >= 60: return "#fffbeb"
    else: return "#f9fafb"


def get_score_label(score: int) -> str:
    if score >= 80: return "🔥 Excellent"
    elif score >= 60: return "👍 Good"
    elif score >= 40: return "🤔 Fair"
    else: return "💡 Possible"


def get_category_style(category: str) -> dict:
    styles = {
        "sponsorship_worldwide": {
            "icon": "✈️", "title": "Outside India — Visa Sponsorship",
            "color": "#16a34a", "bg": "#f0fdf4", "border": "#86efac"
        },
        "india_remote": {
            "icon": "🇮🇳", "title": "India — Remote Only",
            "color": "#2563eb", "bg": "#eff6ff", "border": "#93c5fd"
        },
        "remote_worldwide": {
            "icon": "🌍", "title": "Remote — Worldwide",
            "color": "#7c3aed", "bg": "#f5f3ff", "border": "#c4b5fd"
        },
    }
    return styles.get(category, {"icon": "💼", "title": category, "color": "#374151", "bg": "#f9fafb", "border": "#e5e7eb"})


def build_job_card(job: dict) -> str:
    score = job.get("match_score", 0)
    score_color = get_score_color(score)
    score_bg = get_score_bg(score)
    score_label = get_score_label(score)
    reasons = job.get("match_reasons", [])[:3]
    missing = job.get("missing_skills", [])[:3]
    url = job.get("url", "#")
    title = job.get("title", "N/A")
    company = job.get("company", "N/A")
    location = job.get("location", "")
    source = job.get("source", "").upper()
    salary = job.get("salary", "") or job.get("estimated_salary_usd", "")
    category = job.get("category", "")
    sponsorship = job.get("sponsorship", False) or category == "sponsorship_worldwide"
    auto_applied = job.get("auto_applied", False)

    # Badges
    badges = ""
    if sponsorship:
        badges += '<span style="display:inline-block;background:#dcfce7;color:#166534;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;margin:2px;">✈️ VISA/SPONSORSHIP</span>'
    if "remote" in job.get("type", "").lower() or "remote" in location.lower():
        badges += '<span style="display:inline-block;background:#ede9fe;color:#6d28d9;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;margin:2px;">🏠 REMOTE</span>'
    if auto_applied:
        badges += '<span style="display:inline-block;background:#dbeafe;color:#1d4ed8;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;margin:2px;">⚡ AUTO-APPLIED</span>'
    if source:
        badges += f'<span style="display:inline-block;background:#f3f4f6;color:#6b7280;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;margin:2px;">{source}</span>'

    # Match reasons
    reasons_html = ""
    if reasons:
        items = "".join([f'<li style="margin:4px 0;font-size:13px;color:#374151;">✅ {r}</li>' for r in reasons])
        reasons_html = f'<div style="flex:1;min-width:180px;"><p style="margin:0 0 6px;font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Why You Match</p><ul style="margin:0;padding-left:16px;">{items}</ul></div>'

    # Missing skills
    missing_html = ""
    if missing:
        items = "".join([f'<li style="margin:4px 0;font-size:13px;color:#6b7280;">❌ {m}</li>' for m in missing])
        missing_html = f'<div style="flex:1;min-width:180px;"><p style="margin:0 0 6px;font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Skill Gaps</p><ul style="margin:0;padding-left:16px;">{items}</ul></div>'

    salary_html = f'<span style="color:#6b7280;font-size:13px;"> · 💰 {salary}</span>' if salary else ""

    return f"""
<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:20px 24px;margin:12px 0;box-shadow:0 1px 4px rgba(0,0,0,0.06);">

  <!-- Header row -->
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;">
    <div style="flex:1;min-width:200px;">
      <a href="{url}" style="font-size:17px;font-weight:700;color:#1d4ed8;text-decoration:none;line-height:1.3;">{title}</a>
      <div style="margin-top:5px;font-size:13px;color:#4b5563;">
        🏢 <strong>{company}</strong>
        {f'&nbsp;·&nbsp; 📍 {location}' if location else ""}
        {salary_html}
      </div>
      <div style="margin-top:8px;">{badges}</div>
    </div>
    <!-- Score badge -->
    <div style="background:{score_bg};border:2px solid {score_color};border-radius:14px;padding:10px 16px;text-align:center;min-width:80px;flex-shrink:0;">
      <div style="font-size:26px;font-weight:800;color:{score_color};line-height:1;">{score}%</div>
      <div style="font-size:11px;color:{score_color};font-weight:600;margin-top:2px;">{score_label}</div>
    </div>
  </div>

  <!-- Match details -->
  {f'<div style="display:flex;gap:16px;margin-top:16px;flex-wrap:wrap;">{reasons_html}{missing_html}</div>' if reasons_html or missing_html else ""}

  <!-- Apply button -->
  <div style="margin-top:16px;">
    <a href="{url}" style="display:inline-block;background:#1d4ed8;color:#ffffff;padding:10px 22px;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;">Apply Now →</a>
  </div>

</div>"""


def build_skill_gap_html(skill_gap: dict) -> str:
    if not skill_gap or "error" in skill_gap:
        return '<p style="color:#6b7280;font-size:14px;">Skill gap analysis unavailable today.</p>'

    critical = skill_gap.get("critical_skills_to_learn", [])
    trending = skill_gap.get("trending_in_qa", [])
    certs = skill_gap.get("certifications_recommended", [])
    quick_wins = skill_gap.get("quick_wins", [])
    advice = skill_gap.get("career_advice", "")

    # Career advice box
    advice_html = ""
    if advice:
        advice_html = f'<div style="background:#eff6ff;border-left:4px solid #2563eb;border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:20px;font-size:14px;color:#1e40af;line-height:1.6;">{advice}</div>'

    # Critical skills
    skills_html = ""
    for skill in critical[:5]:
        resources = " · ".join(skill.get("resources", [])[:2])
        skills_html += f"""
        <div style="border:1px solid #fde68a;background:#fffbeb;border-radius:10px;padding:14px 16px;margin:8px 0;">
          <div style="font-size:15px;font-weight:700;color:#92400e;">📚 {skill.get('skill', '')}</div>
          <div style="font-size:13px;color:#374151;margin-top:4px;">{skill.get('reason', '')}</div>
          <div style="font-size:12px;color:#6b7280;margin-top:4px;">⏱️ {skill.get('learning_time', '')}
          {f' &nbsp;·&nbsp; 🔗 {resources}' if resources else ''}</div>
        </div>"""

    # Trending pills
    trending_html = ""
    if trending:
        pills = "".join([f'<span style="display:inline-block;background:#f3e8ff;color:#7c3aed;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;margin:3px;">{t}</span>' for t in trending[:6]])
        trending_html = f'<div style="margin-top:20px;"><p style="font-size:13px;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">🔥 Trending in QA</p>{pills}</div>'

    # Quick wins
    quick_html = ""
    if quick_wins:
        items = "".join([f'<li style="margin:6px 0;font-size:13px;color:#374151;">⚡ {w}</li>' for w in quick_wins[:4]])
        quick_html = f'<div style="margin-top:20px;"><p style="font-size:13px;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Quick Wins This Week</p><ul style="margin:0;padding-left:18px;">{items}</ul></div>'

    # Certs
    cert_html = ""
    if certs:
        items = "".join([f'<li style="margin:6px 0;font-size:13px;color:#374151;">🏆 <strong>{c.get("cert","")}</strong> — {c.get("reason","")}</li>' for c in certs[:3]])
        cert_html = f'<div style="margin-top:20px;"><p style="font-size:13px;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Recommended Certifications</p><ul style="margin:0;padding-left:18px;">{items}</ul></div>'

    return advice_html + skills_html + trending_html + quick_html + cert_html


def generate_report(matched_jobs: dict, applied_results: list, skill_gap: dict, total_scraped: int) -> str:
    date_str = datetime.now().strftime("%A, %B %d, %Y")
    time_str = datetime.now().strftime("%I:%M %p IST")

    all_jobs = [j for jobs in matched_jobs.values() for j in jobs]
    total_matched = len(all_jobs)
    total_applied = len([r for r in applied_results if r.get("status") == "applied"])
    excellent = len([j for j in all_jobs if j.get("match_score", 0) >= 80])
    good = len([j for j in all_jobs if 60 <= j.get("match_score", 0) < 80])

    # Build category sections
    category_sections = ""
    for category, jobs in matched_jobs.items():
        if not jobs:
            continue
        style = get_category_style(category)
        cards = "".join([build_job_card(j) for j in jobs[:15]])
        more = f'<p style="text-align:center;color:#6b7280;font-size:13px;padding:8px;">+{len(jobs)-15} more jobs in this category</p>' if len(jobs) > 15 else ""

        category_sections += f"""
        <div style="margin:28px 0;">
          <div style="background:{style['bg']};border:1px solid {style['border']};border-radius:12px;padding:14px 20px;margin-bottom:16px;display:flex;align-items:center;gap:10px;">
            <span style="font-size:22px;">{style['icon']}</span>
            <div>
              <span style="font-size:17px;font-weight:700;color:{style['color']};">{style['title']}</span>
              <span style="font-size:13px;color:#6b7280;margin-left:8px;">— {len(jobs)} jobs found</span>
            </div>
          </div>
          {cards}
          {more}
        </div>"""

    # Applied section
    applied_html = ""
    if applied_results:
        rows = ""
        for r in applied_results:
            job = r.get("job", {})
            status = r.get("status", "")
            badge = '<span style="color:#16a34a;font-weight:600;">✅ Applied</span>' if status == "applied" else f'<span style="color:#f59e0b;">⚠️ {status}</span>'
            rows += f"""<tr>
              <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px;">{job.get('title','')}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px;">{job.get('company','')}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px;font-weight:700;">{job.get('match_score',0)}%</td>
              <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px;">{badge}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #f3f4f6;font-size:13px;"><a href="{job.get('url','#')}" style="color:#2563eb;">View</a></td>
            </tr>"""
        applied_html = f"""
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:24px;margin:16px 0;">
          <h2 style="margin:0 0 16px;font-size:18px;color:#1f2937;">⚡ Auto-Applied Jobs</h2>
          <table style="width:100%;border-collapse:collapse;">
            <tr style="background:#f9fafb;">
              <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">Title</th>
              <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">Company</th>
              <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">Match</th>
              <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">Status</th>
              <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">Link</th>
            </tr>
            {rows}
          </table>
        </div>"""

    skill_gap_html = build_skill_gap_html(skill_gap)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">

<div style="max-width:680px;margin:0 auto;padding:20px 16px 40px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e40af 0%,#6d28d9 100%);border-radius:20px;padding:32px;text-align:center;margin-bottom:20px;">
    <div style="font-size:36px;margin-bottom:8px;">🤖</div>
    <h1 style="margin:0;color:#fff;font-size:26px;font-weight:800;">Daily Job Hunt Report</h1>
    <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:14px;">{date_str} &nbsp;·&nbsp; {time_str}</p>
    <p style="margin:4px 0 0;color:rgba(255,255,255,0.6);font-size:12px;">QA Automation Engineer &nbsp;·&nbsp; Worldwide Search</p>
  </div>

  <!-- Stats -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px;">
    <div style="background:#fff;border-radius:14px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
      <div style="font-size:30px;font-weight:800;color:#2563eb;">{total_scraped}</div>
      <div style="font-size:11px;color:#6b7280;margin-top:4px;font-weight:600;">SCANNED</div>
    </div>
    <div style="background:#fff;border-radius:14px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
      <div style="font-size:30px;font-weight:800;color:#7c3aed;">{total_matched}</div>
      <div style="font-size:11px;color:#6b7280;margin-top:4px;font-weight:600;">MATCHED</div>
    </div>
    <div style="background:#fff;border-radius:14px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
      <div style="font-size:30px;font-weight:800;color:#16a34a;">{excellent}</div>
      <div style="font-size:11px;color:#6b7280;margin-top:4px;font-weight:600;">EXCELLENT</div>
    </div>
    <div style="background:#fff;border-radius:14px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
      <div style="font-size:30px;font-weight:800;color:#d97706;">{total_applied}</div>
      <div style="font-size:11px;color:#6b7280;margin-top:4px;font-weight:600;">APPLIED</div>
    </div>
  </div>

  <!-- Jobs by category -->
  <div style="background:#fff;border-radius:20px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-bottom:16px;">
    {category_sections if category_sections else '<p style="text-align:center;color:#6b7280;padding:20px;">No jobs matched today. Bot will try again tomorrow.</p>'}
  </div>

  <!-- Auto applied -->
  {applied_html}

  <!-- Skill Gap -->
  <div style="background:#fff;border-radius:20px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-bottom:16px;">
    <h2 style="margin:0 0 20px;font-size:20px;color:#1f2937;border-bottom:2px solid #f3f4f6;padding-bottom:12px;">🧠 Skill Gap Analysis & Career Growth</h2>
    {skill_gap_html}
  </div>

  <!-- Footer -->
  <div style="text-align:center;padding:20px;color:#94a3b8;font-size:12px;">
    <p style="margin:0;">🤖 QA Job Hunt Bot &nbsp;·&nbsp; Powered by Gemini AI (Free) &nbsp;·&nbsp; Next report tomorrow at 9:00 AM IST</p>
  </div>

</div>
</body>
</html>"""
