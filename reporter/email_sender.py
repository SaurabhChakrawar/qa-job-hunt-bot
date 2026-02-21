"""
email_sender.py
Sends the daily HTML report via Gmail.
"""

import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.json")


def send_report_email(html_content: str, job_count: int = 0, match_count: int = 0):
    """Send the daily report email via Gmail SMTP."""
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    email_cfg = config["email"]
    sender = email_cfg["sender_email"]
    password = email_cfg["sender_app_password"]
    recipient = email_cfg["recipient_email"]

    date_str = datetime.now().strftime("%B %d, %Y")
    subject = f"🤖 Job Report {date_str} — {match_count} New Matches Found | {job_count} Jobs Scanned"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"QA Job Bot <{sender}>"
    msg["To"] = recipient

    # Attach HTML
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        print(f"✅ Report emailed to {recipient}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        print("   Make sure you're using a Gmail App Password, not your regular password.")
        print("   Get one at: https://myaccount.google.com/apppasswords")
        return False
