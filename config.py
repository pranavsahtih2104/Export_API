import os
from dotenv import load_dotenv

# Load key-value pairs from .env into memory
load_dotenv()

# Read individual configuration values
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SEARCH_KEYWORD = os.getenv("SEARCH_KEYWORD", "Singing Bowls")
PRESENTATION_PATH = os.getenv("PRESENTATION_PATH", "assets/company_presentation.pdf")

# Data directory where our flat CSV files will live
DATA_DIR = "data"