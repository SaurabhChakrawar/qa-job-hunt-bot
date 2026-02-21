"""
scheduler.py
Runs the job hunt pipeline every day at 9:00 AM IST (3:30 AM UTC).
Run as a background process: python scheduler/scheduler.py &

Alternatively, use crontab (recommended):
  crontab -e
  30 3 * * * cd /path/to/job-automation && python main.py >> logs/cron.log 2>&1
"""

import schedule
import time
import subprocess
import sys
import os
import pytz
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IST = pytz.timezone("Asia/Kolkata")


def run_job_hunt():
    """Execute the main pipeline."""
    now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    print(f"\n⏰ Scheduler triggered at {now_ist}")

    log_path = os.path.join(PROJECT_ROOT, "logs", f"run_{datetime.now().strftime('%Y%m%d')}.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "a") as log:
        result = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "main.py")],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        log.write(f"\n{'='*60}\n")
        log.write(f"Run at: {now_ist}\n")
        log.write(result.stdout)
        if result.stderr:
            log.write(f"\nSTDERR:\n{result.stderr}")

    if result.returncode == 0:
        print(f"✅ Job hunt completed successfully. Log: {log_path}")
    else:
        print(f"❌ Job hunt failed. Check log: {log_path}")


def get_ist_time_for_schedule(time_str: str) -> str:
    """Convert IST time to UTC for scheduling."""
    # schedule library uses local time, so if server is UTC:
    # IST 09:00 = UTC 03:30
    # This function returns the UTC equivalent for the given IST time
    h, m = map(int, time_str.split(":"))
    ist_hour = h - 5
    ist_min = m - 30
    if ist_min < 0:
        ist_min += 60
        ist_hour -= 1
    if ist_hour < 0:
        ist_hour += 24
    return f"{ist_hour:02d}:{ist_min:02d}"


if __name__ == "__main__":
    print("🤖 QA Job Hunt Scheduler Started")
    print("   Runs daily at 9:00 AM IST (3:30 AM UTC)")
    print("   Press Ctrl+C to stop\n")

    # Schedule at 9am IST = 3:30am UTC
    # If your system is already in IST, use "09:00" directly
    server_tz = "UTC"  # Change to "IST" if your system runs on IST

    if server_tz == "IST":
        schedule.every().day.at("09:00").do(run_job_hunt)
        print("   Scheduled for 09:00 IST daily")
    else:
        schedule.every().day.at("03:30").do(run_job_hunt)
        print("   Scheduled for 03:30 UTC (= 09:00 IST) daily")

    # Also run immediately on start if --run-now flag
    if "--run-now" in sys.argv:
        print("   Running immediately...")
        run_job_hunt()

    # Keep scheduler running
    while True:
        schedule.run_pending()
        next_run = schedule.next_run()
        now_ist = datetime.now(IST)
        print(f"\r⏳ Next run: {next_run} | Current IST: {now_ist.strftime('%H:%M:%S')}", end="")
        time.sleep(30)
