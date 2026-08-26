# 🤖 QA Job Hunt Bot — Free Edition (Powered by Google Gemini)

Automated daily job finder for QA/Test Automation Engineers.
**100% FREE** — uses Google Gemini AI free tier. No credit card needed.

## 💰 Total Monthly Cost: $0.00

| Component | Tool | Cost |
|---|---|---|
| AI Matching & Analysis | Google Gemini 1.5 Flash/Pro | FREE (1500 req/day) |
| Job Scraping | Playwright + requests | FREE |
| Email Reports | Gmail SMTP | FREE |
| Scheduler | Crontab / Python schedule | FREE |
| Database | Local JSON files | FREE |

## 🚀 Setup in 4 Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt && playwright install chromium

# 2. Get free Gemini API key → https://aistudio.google.com
#    Then edit config/config.json and set your gemini_api_key

# 3. Parse your resume
python main.py --parse-resume /path/to/your_resume.pdf

# 4. Test run
python main.py --run-now
```

## 📁 Project Structure

```
job-automation/
├── config/
│   ├── config.json              # Your settings (Gemini key, email, etc.)
│   └── resume_profile.json      # Auto-generated from your resume
├── scrapers/
│   ├── linkedin_scraper.py      # LinkedIn jobs (Playwright)
│   └── remote_scraper.py        # India and worldwide job-board sources
├── matcher/
│   ├── resume_parser.py         # Parse resume → profile (Gemini)
│   └── job_matcher.py           # Score jobs vs profile (Gemini)
├── reporter/
│   ├── report_generator.py      # Beautiful HTML report
│   └── email_sender.py          # Gmail SMTP delivery
├── apply/
│   └── auto_apply.py            # LinkedIn Easy Apply automation
├── scheduler/
│   └── scheduler.py             # Daily 9AM IST scheduler
├── data/
│   └── jobs_db.py               # Deduplication database
└── main.py                      # Entry point
```

## ⚙️ Get Your Free Gemini API Key

1. Go to **https://aistudio.google.com**
2. Sign in with your Google account
3. Click **"Get API Key"** → **"Create API Key"**
4. Copy the key and paste it in `config/config.json`

**Free tier limits:** 15 requests/minute, 1500 requests/day
Your bot uses ~100-150 requests/day — well within limits.

## ⏰ Schedule Daily at 9AM IST

```bash
# Linux/Mac — add to crontab (3:30 AM UTC = 9:00 AM IST)
crontab -e
30 3 * * * cd /path/to/job-automation && python main.py >> logs/cron.log 2>&1

# OR run background scheduler
nohup python scheduler/scheduler.py > logs/scheduler.log 2>&1 &
```

## 🎯 Job Categories Covered

- ✈️ **Outside India (Visa Sponsorship)** — US, UK, Germany, Canada, Australia, UAE, Singapore, Netherlands
- 🇮🇳 **India Remote** — Naukri, LinkedIn India Remote
- 🌍 **Remote Worldwide** — Remotive, We Work Remotely, Himalayas

Jobs shown in the sponsorship category must contain an explicit positive
sponsorship statement in the listing. Jobs merely returned by a visa-related
search, or with no clear statement, are moved to Remote Worldwide and are not
shown as sponsored.

## 🔎 Active Job Sources

The bot searches LinkedIn, Instahyre, Himalayas, Jobicy, Arbeitnow, Remote OK,
Shine, Remotive, Naukri, Foundit, and Indeed feeds. Availability can vary by
source because some job boards restrict automated access.

## 📧 Daily Report Includes

- Match score (0-100%) for each job with reasons
- An **Apply Today** shortlist of up to 8 new jobs scoring 75% or above
- Direct review/apply links (you submit every application yourself)
- Skill gap analysis — what to learn next

## ⭐ Apply Today

The dashboard's **Apply Today** view contains at most 10 jobs that are marked
`APPLY`, score at least 75%, have a working application URL, and were posted in
the last seven days. Each card explains why it was prioritized. Verified visa
sponsorship and LinkedIn Easy Apply receive a small priority boost.

## 📋 Dashboard Application Tracker

The GitHub Pages dashboard lets you mark a job as **Saved**, **Applied**,
**Interview**, or **Rejected**, and attach a short note. Tracker data is stored
locally in your browser, so it remains available across daily dashboard updates
without being committed to the repository.

> GitHub Pages is public by default. Do not publish your resume, contact
> information, application notes, or other sensitive data in `docs/`. Use an
> access-controlled host if the dashboard itself needs to be private.

## 👀 LinkedIn Easy Apply review mode

For high-match LinkedIn Easy Apply jobs, local runs can prefill only safe
fields (contact details and resume) and pause at the final Submit button for
your review. Enable it only in your local `config/config.json`:

```json
"linkedin": {
  "auto_apply": true,
  "review_before_submit": true,
  "max_apply_per_day": 5
}
```

The browser remains visible. Review every answer, submit it yourself, then
press Enter in the terminal so the bot can record the outcome. This does not
run in GitHub Actions.
