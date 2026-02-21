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
│   └── remote_scraper.py        # Remotive, WWR, Himalayas, Naukri, Relocate.me
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

## 📧 Daily Report Includes

- Match score (0-100%) for each job with reasons
- Direct apply links
- Auto-applied job status
- Skill gap analysis — what to learn next
