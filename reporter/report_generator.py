"""
report_generator.py
Generates a beautiful HTML daily job report email.
"""

import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_score_color(score: int) -> str:
    if score >= 80:
        return "#22c55e"  # Green
    elif score >= 65:
        return "#f59e0b"  # Amber
    else:
        return "#ef4444"  # Red


def get_score_emoji(score: int) -> str:
    if score >= 80:
        return "🔥"
    elif score >= 65:
        return "👍"
    else:
        return "🤔"


def build_job_card_html(job: dict) -> str:
    score = job.get("match_score", 0)
    color = get_score_color(score)
    emoji = get_score_emoji(score)
    reasons = job.get("match_reasons", [])
    missing = job.get("missing_skills", [])
    salary = job.get("estimated_salary_usd", "") or job.get("salary", "")

    reasons_html = "".join([f"<li>✅ {r}</li>" for r in reasons[:3]])
    missing_html = "".join([f"<li>❌ {m}</li>" for m in missing[:3]])

    return f"""
    <div style="border:1px solid #e5e7eb; border-radius:12px; padding:20px; margin:12px 0; background:#fff; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
            <div style="flex:1;">
                <h3 style="margin:0 0 4px 0; font-size:17px; color:#1f2937;">
                    <a href="{job.get('url', '#')}" style="color:#2563eb; text-decoration:none;">{job.get('title', 'N/A')}</a>
                </h3>
                <p style="margin:0; color:#6b7280; font-size:14px;">
                    🏢 <strong>{job.get('company', 'N/A')}</strong> &nbsp;|&nbsp;
                    📍 {job.get('location', 'N/A')} &nbsp;|&nbsp;
                    🌐 {job.get('source', '').upper()}
                    {f"&nbsp;|&nbsp; 💰 ${salary:,}" if salary and isinstance(salary, int) else f"&nbsp;|&nbsp; 💰 {salary}" if salary else ""}
                </p>
            </div>
            <div style="text-align:center; background:{color}; color:#fff; border-radius:10px; padding:8px 16px; min-width:70px;">
                <div style="font-size:22px; font-weight:bold;">{score}%</div>
                <div style="font-size:12px;">{emoji} Match</div>
            </div>
        </div>

        <div style="display:flex; gap:20px; margin-top:14px; flex-wrap:wrap;">
            {"<div style='flex:1; min-width:200px;'><p style='font-size:12px; font-weight:bold; color:#374151; margin:0 0 4px 0;'>WHY YOU MATCH:</p><ul style='margin:0; padding-left:20px; font-size:13px; color:#374151;'>" + reasons_html + "</ul></div>" if reasons_html else ""}
            {"<div style='flex:1; min-width:200px;'><p style='font-size:12px; font-weight:bold; color:#374151; margin:0 0 4px 0;'>GAPS TO ADDRESS:</p><ul style='margin:0; padding-left:20px; font-size:13px; color:#6b7280;'>" + missing_html + "</ul></div>" if missing_html else ""}
        </div>

        <div style="margin-top:12px; display:flex; gap:10px; flex-wrap:wrap;">
            <a href="{job.get('url', '#')}" style="background:#2563eb; color:#fff; padding:8px 16px; border-radius:6px; text-decoration:none; font-size:13px; font-weight:600;">
                Apply Now →
            </a>
            {"<span style='background:#dcfce7; color:#166534; padding:8px 12px; border-radius:6px; font-size:12px; font-weight:600;'>✈️ VISA/SPONSORSHIP</span>" if job.get('sponsorship') or job.get('category') == 'sponsorship_worldwide' else ""}
            {"<span style='background:#fef3c7; color:#92400e; padding:8px 12px; border-radius:6px; font-size:12px; font-weight:600;'>🏠 REMOTE</span>" if 'remote' in job.get('type', '').lower() else ""}
            {"<span style='background:#dbeafe; color:#1d4ed8; padding:8px 12px; border-radius:6px; font-size:12px; font-weight:600;'>⚡ AUTO-APPLIED</span>" if job.get('auto_applied') else ""}
        </div>
    </div>
    """


def build_skill_gap_section(skill_gap: dict) -> str:
    if not skill_gap or "error" in skill_gap:
        return "<p>Skill gap analysis unavailable today.</p>"

    critical = skill_gap.get("critical_skills_to_learn", [])
    trending = skill_gap.get("trending_in_qa", [])
    certs = skill_gap.get("certifications_recommended", [])
    quick_wins = skill_gap.get("quick_wins", [])
    advice = skill_gap.get("career_advice", "")

    critical_html = ""
    for skill in critical[:5]:
        critical_html += f"""
        <div style="border-left:4px solid #f59e0b; padding:10px 16px; margin:8px 0; background:#fffbeb; border-radius:0 8px 8px 0;">
            <strong style="color:#92400e;">📚 {skill.get('skill', '')}</strong>
            <p style="margin:4px 0 2px 0; font-size:13px; color:#374151;">{skill.get('reason', '')}</p>
            <span style="font-size:12px; color:#6b7280;">⏱️ {skill.get('learning_time', '')} &nbsp;|&nbsp;
            Resources: {', '.join(skill.get('resources', []))}</span>
        </div>"""

    trending_html = " &nbsp;|&nbsp; ".join([f"<span style='background:#f3e8ff; color:#7c3aed; padding:4px 10px; border-radius:20px; font-size:12px;'>{t}</span>" for t in trending[:5]])
    quick_html = "".join([f"<li style='margin:6px 0; font-size:14px;'>⚡ {w}</li>" for w in quick_wins[:4]])
    cert_html = ""
    for cert in certs[:3]:
        cert_html += f"<li style='margin:6px 0; font-size:14px;'>🏆 <strong>{cert.get('cert', '')}</strong> - {cert.get('reason', '')}</li>"

    return f"""
    {f'<p style="background:#eff6ff; border-radius:8px; padding:14px; font-size:14px; color:#1e40af; border-left:4px solid #2563eb;">{advice}</p>' if advice else ""}

    <h3 style="color:#1f2937; border-bottom:2px solid #f59e0b; padding-bottom:6px;">🎯 Critical Skills to Learn</h3>
    {critical_html}

    <h3 style="color:#1f2937; margin-top:24px;">⚡ Quick Wins (This Week)</h3>
    <ul style="padding-left:20px;">{quick_html}</ul>

    <h3 style="color:#1f2937; margin-top:24px;">🔥 Trending in QA Right Now</h3>
    <p>{trending_html}</p>

    {"<h3 style='color:#1f2937; margin-top:24px;'>🏅 Recommended Certifications</h3><ul style='padding-left:20px;'>" + cert_html + "</ul>" if cert_html else ""}
    """


def generate_report(
    matched_jobs: dict,  # category -> list of matched jobs
    applied_results: list,
    skill_gap: dict,
    total_scraped: int
) -> str:
    """Generate full HTML report."""

    date_str = datetime.now().strftime("%A, %B %d, %Y")
    time_str = datetime.now().strftime("%I:%M %p IST")

    # Stats
    all_jobs = []
    for jobs in matched_jobs.values():
        all_jobs.extend(jobs)

    total_matched = len(all_jobs)
    total_applied = len([r for r in applied_results if r.get("status") == "applied"])
    excellent_matches = len([j for j in all_jobs if j.get("match_score", 0) >= 80])

    # Build category sections
    category_sections = ""

    category_config = {
        "sponsorship_worldwide": {
            "icon": "✈️",
            "title": "Outside India (with Visa Sponsorship)",
            "color": "#16a34a",
            "bg": "#f0fdf4"
        },
        "india_remote": {
            "icon": "🇮🇳",
            "title": "India — Remote Only",
            "color": "#2563eb",
            "bg": "#eff6ff"
        },
        "remote_worldwide": {
            "icon": "🌍",
            "title": "Remote Worldwide",
            "color": "#7c3aed",
            "bg": "#f5f3ff"
        }
    }

    for category, jobs in matched_jobs.items():
        if not jobs:
            continue

        cat_cfg = category_config.get(category, {"icon": "💼", "title": category, "color": "#374151", "bg": "#f9fafb"})
        job_cards = "".join([build_job_card_html(j) for j in jobs[:10]])  # Max 10 per category

        category_sections += f"""
        <div style="margin:30px 0;">
            <h2 style="color:{cat_cfg['color']}; background:{cat_cfg['bg']}; padding:14px 20px; border-radius:10px; margin:0 0 16px 0; font-size:18px;">
                {cat_cfg['icon']} {cat_cfg['title']}
                <span style="font-size:14px; font-weight:normal; color:#6b7280;"> — {len(jobs)} jobs found</span>
            </h2>
            {job_cards}
            {"<p style='text-align:center; color:#6b7280; font-size:13px;'>... and " + str(len(jobs) - 10) + " more jobs. Check your Google Sheet for full list.</p>" if len(jobs) > 10 else ""}
        </div>
        """

    # Applied jobs section
    applied_html = ""
    if applied_results:
        applied_rows = ""
        for r in applied_results:
            job = r.get("job", {})
            status = r.get("status", "")
            status_badge = "✅ Applied" if status == "applied" else f"⚠️ {status}"
            applied_rows += f"""
            <tr>
                <td style="padding:10px; border-bottom:1px solid #e5e7eb;">{job.get('title', 'N/A')}</td>
                <td style="padding:10px; border-bottom:1px solid #e5e7eb;">{job.get('company', 'N/A')}</td>
                <td style="padding:10px; border-bottom:1px solid #e5e7eb;">{job.get('match_score', 0)}%</td>
                <td style="padding:10px; border-bottom:1px solid #e5e7eb;">{status_badge}</td>
                <td style="padding:10px; border-bottom:1px solid #e5e7eb;"><a href="{job.get('url', '#')}" style="color:#2563eb;">View Job</a></td>
            </tr>"""

        applied_html = f"""
        <div style="margin:30px 0;">
            <h2 style="color:#374151; border-bottom:2px solid #e5e7eb; padding-bottom:10px;">⚡ Auto-Applied Jobs Today</h2>
            <table style="width:100%; border-collapse:collapse; font-size:14px;">
                <thead>
                    <tr style="background:#f9fafb;">
                        <th style="padding:10px; text-align:left; border-bottom:2px solid #e5e7eb;">Title</th>
                        <th style="padding:10px; text-align:left; border-bottom:2px solid #e5e7eb;">Company</th>
                        <th style="padding:10px; text-align:left; border-bottom:2px solid #e5e7eb;">Match</th>
                        <th style="padding:10px; text-align:left; border-bottom:2px solid #e5e7eb;">Status</th>
                        <th style="padding:10px; text-align:left; border-bottom:2px solid #e5e7eb;">Link</th>
                    </tr>
                </thead>
                <tbody>{applied_rows}</tbody>
            </table>
        </div>"""

    skill_gap_html = build_skill_gap_section(skill_gap)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Report - {date_str}</title>
</head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif; max-width:800px; margin:0 auto; background:#f8fafc; color:#1f2937;">

<!-- Header -->
<div style="background:linear-gradient(135deg, #1e40af 0%, #7c3aed 100%); color:#fff; padding:30px; border-radius:0 0 16px 16px; text-align:center;">
    <h1 style="margin:0; font-size:24px;">🤖 Daily Job Hunt Report</h1>
    <p style="margin:8px 0 0 0; opacity:0.85; font-size:15px;">{date_str} &nbsp;|&nbsp; {time_str}</p>
    <p style="margin:4px 0 0 0; opacity:0.7; font-size:13px;">QA Automation Engineer &bull; Worldwide Search</p>
</div>

<!-- Stats -->
<div style="display:flex; gap:12px; margin:20px; flex-wrap:wrap;">
    <div style="flex:1; min-width:120px; background:#fff; border-radius:10px; padding:16px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:28px; font-weight:bold; color:#2563eb;">{total_scraped}</div>
        <div style="font-size:12px; color:#6b7280; margin-top:4px;">Jobs Scanned</div>
    </div>
    <div style="flex:1; min-width:120px; background:#fff; border-radius:10px; padding:16px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:28px; font-weight:bold; color:#7c3aed;">{total_matched}</div>
        <div style="font-size:12px; color:#6b7280; margin-top:4px;">Matched Jobs</div>
    </div>
    <div style="flex:1; min-width:120px; background:#fff; border-radius:10px; padding:16px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:28px; font-weight:bold; color:#16a34a;">{excellent_matches}</div>
        <div style="font-size:12px; color:#6b7280; margin-top:4px;">Excellent Matches (80%+)</div>
    </div>
    <div style="flex:1; min-width:120px; background:#fff; border-radius:10px; padding:16px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:28px; font-weight:bold; color:#f59e0b;">{total_applied}</div>
        <div style="font-size:12px; color:#6b7280; margin-top:4px;">Auto-Applied</div>
    </div>
</div>

<!-- Job Categories -->
<div style="background:#fff; margin:0 20px; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    {category_sections}
</div>

<!-- Auto-Applied Section -->
{f'<div style="background:#fff; margin:16px 20px; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">{applied_html}</div>' if applied_html else ""}

<!-- Skill Gap Analysis -->
<div style="background:#fff; margin:16px 20px; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <h2 style="color:#1f2937; margin-top:0; border-bottom:2px solid #e5e7eb; padding-bottom:10px;">
        🧠 Skill Gap Analysis & Career Growth
    </h2>
    {skill_gap_html}
</div>

<!-- Footer -->
<div style="text-align:center; padding:20px; color:#9ca3af; font-size:12px;">
    <p>Generated by your QA Job Hunt Bot &bull; Next report: tomorrow at 9:00 AM IST</p>
    <p>Powered by Claude AI &bull; <a href="#" style="color:#6b7280;">Manage Preferences</a></p>
</div>

</body>
</html>
"""
    return html
