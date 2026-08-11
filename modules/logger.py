import os
import pandas as pd
from config import DATA_DIR

BUYERS_CSV = os.path.join(DATA_DIR, "buyers.csv")
BUSINESS_CSV = os.path.join(DATA_DIR, "business_emails.csv")
INDIVIDUAL_CSV = os.path.join(DATA_DIR, "individual_emails.csv")
SENT_LOG_CSV = os.path.join(DATA_DIR, "sent_log.csv")

def init_storage():
    """Ensure the data folder and base CSV files exist with proper headers."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if not os.path.exists(BUYERS_CSV):
        pd.DataFrame(columns=["email_address", "buyer_name", "company_name", "website", "country", "source_platform"]).to_csv(BUYERS_CSV, index=False)
        
    if not os.path.exists(SENT_LOG_CSV):
        pd.DataFrame(columns=["email_address", "status", "timestamp"]).to_csv(SENT_LOG_CSV, index=False)

def get_already_sent_emails() -> set:
    """Return a set of all email addresses that were already contacted."""
    init_storage()
    if not os.path.exists(SENT_LOG_CSV) or os.path.getsize(SENT_LOG_CSV) == 0:
        return set()
    df = pd.read_csv(SENT_LOG_CSV)
    return set(df["email_address"].dropna().unique()) if not df.empty else set()

def save_buyers(buyers_list: list):
    """Save extracted buyer dictionaries into buyers.csv without duplicates."""
    init_storage()
    if not buyers_list:
        return
        
    df_new = pd.DataFrame(buyers_list)
    if os.path.exists(BUYERS_CSV) and os.path.getsize(BUYERS_CSV) > 0:
        df_old = pd.read_csv(BUYERS_CSV)
        df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=["email_address"])
    else:
        df_combined = df_new
        
    df_combined.to_csv(BUYERS_CSV, index=False)

def log_send_attempt(email: str, status: str):
    """Log an outreach attempt (sent or failed) to sent_log.csv."""
    init_storage()
    from datetime import datetime
    new_entry = pd.DataFrame([{"email_address": email, "status": status, "timestamp": datetime.now().isoformat()}])
    new_entry.to_csv(SENT_LOG_CSV, mode='a', header=not os.path.exists(SENT_LOG_CSV), index=False)