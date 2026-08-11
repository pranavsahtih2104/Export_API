import os
import json
import pandas as pd
from google import genai
from config import GEMINI_API_KEY, DATA_DIR
from modules.logger import BUYERS_CSV, BUSINESS_CSV, INDIVIDUAL_CSV, init_storage

def classify_buyer_emails():
    """
    Reads buyers.csv, sends email addresses to Gemini API for classification,
    and splits them into business_emails.csv and individual_emails.csv.
    """
    init_storage()
    
    if not os.path.exists(BUYERS_CSV) or os.path.getsize(BUYERS_CSV) == 0:
        print("[Classifier] buyers.csv is empty or missing.")
        return {"business_count": 0, "individual_count": 0}

    # 1. Read unique buyers from CSV
    df = pd.read_csv(BUYERS_CSV)
    if df.empty or "email_address" not in df.columns:
        return {"business_count": 0, "individual_count": 0}

    # Extract unique, non-empty email addresses
    emails = df["email_address"].dropna().unique().tolist()
    if not emails:
        return {"business_count": 0, "individual_count": 0}

    # 2. Initialize the Google Gemini API client
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    You are an expert lead classification assistant.
    Classify the following email addresses into two distinct categories based on domain type and structure:
    1. "business": Corporate, company, distributor, or wholesale business domains (e.g., info@company.com, sales@bowlsimport.de).
    2. "individual": Personal email providers (e.g., @gmail.com, @yahoo.com, @outlook.com) or individual personal contacts.

    Emails to classify:
    {json.dumps(emails)}

    Respond ONLY with a valid JSON object mapping each email address to its assigned label ("business" or "individual").
    Example format:
    {{
      "john@company.com": "business",
      "alice@gmail.com": "individual"
    }}
    """

    business_list = []
    individual_list = []

    try:
        # 3. Call Gemini API
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        # 4. Clean up response string and parse JSON
        cleaned_text = response.text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text.replace("```json", "", 1)
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text.rsplit("```", 1)[0]
        cleaned_text = cleaned_text.strip()

        classified_map = json.loads(cleaned_text)

        # 5. Sort buyer records into respective lists based on AI output
        for _, row in df.iterrows():
            email = row["email_address"]
            category = classified_map.get(email, "individual")  # Default to individual if unmapped
            
            record = row.to_dict()
            if category.lower() == "business":
                business_list.append(record)
            else:
                individual_list.append(record)

    except Exception as e:
        print(f"[Classifier] Error during Gemini API classification: {e}")
        # Fallback: simple domain heuristic if API fails or quota is exceeded
        for _, row in df.iterrows():
            email = str(row["email_address"])
            if any(domain in email for domain in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]):
                individual_list.append(row.to_dict())
            else:
                business_list.append(row.to_dict())

    # 6. Save split datasets to flat CSV files
    pd.DataFrame(business_list).to_csv(BUSINESS_CSV, index=False)
    pd.DataFrame(individual_list).to_csv(INDIVIDUAL_CSV, index=False)

    print(f"[Classifier] Classified {len(business_list)} business and {len(individual_list)} individual contacts.")
    return {
        "business_count": len(business_list),
        "individual_count": len(individual_list)
    }