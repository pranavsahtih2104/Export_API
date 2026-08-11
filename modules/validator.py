import re
from email_validator import validate_email, EmailNotValidError

# Common image/asset extensions that get mistakenly extracted as emails
INVALID_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js')

def is_valid_email(email: str) -> bool:
    """Validate email syntax and filter out invalid or asset strings."""
    if not email or not isinstance(email, str):
        return False
        
    email = email.strip().lower()
    
    # 1. Reject if it ends with an image/asset extension
    if email.endswith(INVALID_EXTENSIONS):
        return False
        
    # 2. Reject if the domain part is suspiciously long (> 50 chars)
    if '@' in email:
        domain = email.split('@')[-1]
        if len(domain) > 50:
            return False
            
    # 3. Standard library validation check
    try:
        # validate_email checks for syntax (local-part@domain)
        valid = validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

def extract_and_clean_emails(raw_text: str) -> list:
    """Find all valid emails from a raw block of scraped web text."""
    if not raw_text:
        return []
        
    # Regex pattern to capture candidate emails from unformatted HTML/text
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    candidates = re.findall(email_regex, raw_text)
    
    # Filter candidates through our validation rules and remove duplicates
    valid_emails = set()
    for candidate in candidates:
        if is_valid_email(candidate):
            valid_emails.add(candidate.strip().lower())
            
    return list(valid_emails)