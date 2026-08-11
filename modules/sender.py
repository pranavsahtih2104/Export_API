import os
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import pandas as pd

from config import GMAIL_EMAIL, GMAIL_APP_PASSWORD, PRESENTATION_PATH, DATA_DIR
from modules.logger import (
    BUYERS_CSV,
    BUSINESS_CSV,
    INDIVIDUAL_CSV,
    get_already_sent_emails,
    log_send_attempt
)

def send_outreach_campaign(
    subject: str = "Exclusive Export Opportunities — Singing Bowls Catalog",
    body_template: str = None,
    audience: str = "business",  # Options: "business", "individual", "all"
    send_delay: int = 2
) -> dict:
    """
    Reads recipient emails for the chosen audience, attaches the presentation PDF,
    and sends personalized emails via Gmail SMTP while avoiding duplicates.
    """
    # 1. Determine target audience CSV file
    if audience == "business":
        target_file = BUSINESS_CSV
    elif audience == "individual":
        target_file = INDIVIDUAL_CSV
    else:
        target_file = BUYERS_CSV

    if not os.path.exists(target_file) or os.path.getsize(target_file) == 0:
        print(f"[Sender] Target file '{target_file}' is empty or missing.")
        return {"total": 0, "sent": 0, "skipped": 0, "failed": 0}

    # 2. Read contacts and filter out already contacted emails
    df = pd.read_csv(target_file)
    if df.empty or "email_address" not in df.columns:
        return {"total": 0, "sent": 0, "skipped": 0, "failed": 0}

    already_sent = get_already_sent_emails()
    recipients = df.to_dict(orient="records")

    sent_count = 0
    skipped_count = 0
    failed_count = 0

    # Default email body template if none is provided
    if not body_template:
        body_template = """Hello {name},

We are pleased to share our latest collection of premium hand-crafted Singing Bowls.
Please find our complete product catalog and export pricing attached to this email.

We look forward to discussing a potential partnership with {company}.

Best regards,
Export Business Development Team
"""

    # 3. Establish SMTP connection to Gmail
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Secure connection via TLS
        server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
    except Exception as e:
        print(f"[Sender] Failed to authenticate with Gmail SMTP: {e}")
        return {"total": len(recipients), "sent": 0, "skipped": 0, "failed": len(recipients)}

    # 4. Process each recipient sequentially
    for recipient in recipients:
        email = recipient.get("email_address")
        if not email or str(email).lower() in already_sent:
            skipped_count += 1
            continue

        name = recipient.get("buyer_name", "Valued Customer")
        company = recipient.get("company_name", "your organization")

        # Create MIME message
        msg = MIMEMultipart()
        msg["From"] = GMAIL_EMAIL
        msg["To"] = email
        msg["Subject"] = subject

        # Fill personalized text template
        personalized_body = body_template.format(name=name, company=company)
        msg.attach(MIMEText(personalized_body, "plain"))

        # Attach PDF presentation file if present
        if os.path.exists(PRESENTATION_PATH):
            try:
                with open(PRESENTATION_PATH, "rb") as pdf_file:
                    part = MIMEApplication(pdf_file.read(), Name=os.path.basename(PRESENTATION_PATH))
                    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(PRESENTATION_PATH)}"'
                    msg.attach(part)
            except Exception as pdf_err:
                print(f"[Sender] Failed to attach presentation PDF: {pdf_err}")

        # Send email over SMTP
        try:
            server.send_message(msg)
            log_send_attempt(email, "sent")
            already_sent.add(str(email).lower())
            sent_count += 1
            print(f"[Sender] Successfully sent outreach email to: {email}")
            
            # Rate limit delay between sends
            time.sleep(send_delay)

        except Exception as send_err:
            print(f"[Sender] Failed to send email to {email}: {send_err}")
            log_send_attempt(email, "failed")
            failed_count += 1

    # Close SMTP session
    try:
        server.quit()
    except Exception:
        pass

    return {
        "total": len(recipients),
        "sent": sent_count,
        "skipped": skipped_count,
        "failed": failed_count
    }