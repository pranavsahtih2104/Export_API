import json
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from config import SEARCH_KEYWORD, GEMINI_API_KEY
from modules.validator import extract_and_clean_emails

# User-Agent header tricks web servers into treating our script like a normal browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_duckduckgo_buyers(keyword: str = SEARCH_KEYWORD, max_results: int = 5) -> list:
    """
    Search the web for potential export buyers.
    Uses Gemini AI with search grounding to discover qualified leads and their contact info,
    scraping their website pages if emails are missing from search snippets.
    Falls back to DuckDuckGo scraping if Gemini API fails or key is missing.
    """
    discovered_buyers = []

    # Try Gemini Search Grounding first
    if GEMINI_API_KEY:
        try:
            print(f"[Search] Querying Gemini with Search Grounding for keyword: '{keyword}'...")
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt = f"""
            Perform a Google search to find active wholesale buyers, importers, distributors, or specialty retail shops that purchase products related to '{keyword}'.
            Retrieve at least {max_results} different buyer/wholesale leads.
            
            For each lead, provide:
            1. Company Name
            2. Main Website URL (must be a valid public URL, e.g. https://example.com)
            3. Contact Email address (if you can find one in the search results or snippets)
            4. Country location
            
            Respond ONLY with a valid JSON list of objects.
            Example format:
            [
              {{
                "company_name": "Phoenix Import",
                "website": "https://www.phoeniximport.com",
                "email_address": "service@phoeniximport.nl",
                "country": "Netherlands"
              }}
            ]
            Do not add markdown formatting or extra text outside the JSON list.
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                )
            )
            
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text.replace("```json", "", 1)
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text.rsplit("```", 1)[0]
            cleaned_text = cleaned_text.strip()
            
            leads = json.loads(cleaned_text)
            print(f"[Search] Gemini discovered {len(leads)} potential leads.")
            
            for lead in leads:
                company = lead.get("company_name", "Unknown Company")
                website = lead.get("website", "")
                email = lead.get("email_address", "")
                country = lead.get("country", "Unknown")
                
                # If email is missing, try scraping the website
                if not email and website:
                    print(f"[Search] Email missing for {company}. Attempting to scrape {website}...")
                    try:
                        res = requests.get(website, headers=HEADERS, timeout=8)
                        if res.status_code == 200:
                            emails = extract_and_clean_emails(res.text)
                            if emails:
                                email = emails[0]
                                print(f"[Search] Found email via homepage scrape: {email}")
                            else:
                                # Try common contact paths
                                for path in ["/contact", "/contact-us", "/about"]:
                                    try:
                                        contact_url = f"{website.rstrip('/')}{path}"
                                        res_c = requests.get(contact_url, headers=HEADERS, timeout=5)
                                        if res_c.status_code == 200:
                                            c_emails = extract_and_clean_emails(res_c.text)
                                            if c_emails:
                                                email = c_emails[0]
                                                print(f"[Search] Found email via contact page ({path}): {email}")
                                                break
                                    except Exception:
                                        continue
                    except Exception as e:
                        print(f"[Search] Scrape failed for {website}: {e}")
                
                # Only save lead if we have an email address
                if email:
                    # Clean up buyer name from email or use company name
                    buyer_name = email.split("@")[0].replace(".", " ").title()
                    discovered_buyers.append({
                        "email_address": email.strip().lower(),
                        "buyer_name": buyer_name,
                        "company_name": company,
                        "website": website,
                        "country": country,
                        "source_platform": "Google Search (Gemini Grounding)"
                    })
                    
            if discovered_buyers:
                print(f"[Search] Successfully extracted {len(discovered_buyers)} buyer leads using Gemini.")
                return discovered_buyers
                
        except Exception as e:
            print(f"[Search] Gemini Search Grounding failed: {e}. Falling back to DuckDuckGo scraping.")
            
    # Fallback to DuckDuckGo Scraping if Gemini fails
    search_query = f"{keyword} buyers importers wholesale contact email"
    url = f"https://html.duckduckgo.com/html/?q={search_query}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"[Search] Fallback DDG fetch failed. Status: {response.status_code}")
            return discovered_buyers
            
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for a_tag in soup.find_all("a", class_="result__url"):
            href = a_tag.get("href")
            if href and href.startswith("http"):
                links.append(href)
                if len(links) >= max_results:
                    break
                    
        print(f"[Search] Fallback DDG discovered {len(links)} candidate web pages. Scraping contents...")
        
        for page_url in links:
            try:
                page_res = requests.get(page_url, headers=HEADERS, timeout=8)
                if page_res.status_code == 200:
                    emails = extract_and_clean_emails(page_res.text)
                    domain = page_url.split("//")[-1].split("/")[0]
                    for email in emails:
                        discovered_buyers.append({
                            "email_address": email.strip().lower(),
                            "buyer_name": email.split("@")[0].replace(".", " ").title(),
                            "company_name": domain,
                            "website": page_url,
                            "country": "Unknown",
                            "source_platform": "DuckDuckGo Web Search"
                        })
            except Exception:
                continue
    except Exception as e:
        print(f"[Search] Fallback error during search pipeline: {e}")
        
    return discovered_buyers