import shutil
from fastapi import FastAPI, Request, HTTPException, Query,UploadFile,File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import os
import pandas as pd

from config import SEARCH_KEYWORD
from modules.logger import (
    init_storage,
    get_already_sent_emails,
    BUYERS_CSV,
    BUSINESS_CSV,
    INDIVIDUAL_CSV,
    SENT_LOG_CSV,
    save_buyers
)
from modules.search import search_duckduckgo_buyers
from modules.classifier import classify_buyer_emails
from modules.sender import send_outreach_campaign

# Initialize FastAPI app
app = FastAPI(
    title="EXPORT Automation System API & UI",
    description="Automated Lead Discovery, AI Email Classification, and Outreach System",
    version="1.0.0"
)

# Setup Jinja2 Template rendering directory
templates = Jinja2Templates(directory="templates")

# Ensure storage environment exists on startup
@app.on_event("startup")
def startup_event():
    init_storage()

# Request Body Schema Models (Pydantic)
class SearchRequest(BaseModel):
    keyword: Optional[str] = SEARCH_KEYWORD
    max_results: Optional[int] = 5

class SendRequest(BaseModel):
    subject: Optional[str] = "Exclusive Export Opportunities — Singing Bowls Catalog"
    body_template: Optional[str] = None
    audience: Optional[str] = "business"  # "business", "individual", or "all"
    send_delay: Optional[int] = 2

# ==========================================
# FRONTEND UI ROUTES (HTML Pages)
# ==========================================

# ==========================================
# FRONTEND UI ROUTES (HTML Pages)
# ==========================================

@app.get("/", response_class=HTMLResponse)
def render_dashboard(request: Request):
    """Render the Home Dashboard UI."""
    already_sent = get_already_sent_emails()
    buyers_count = 0
    if os.path.exists(BUYERS_CSV) and os.path.getsize(BUYERS_CSV) > 0:
        df = pd.read_csv(BUYERS_CSV)
        buyers_count = len(df)

    # Use explicitly named 'request' parameter or pass context dictionary directly
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "total_buyers": buyers_count,
            "total_sent": len(already_sent)
        }
    )
@app.get("/ui/upload", response_class=HTMLResponse)
def render_upload_page(request: Request):
    """Render the CSV Lead Upload Page UI."""
    return templates.TemplateResponse(request=request, name="upload.html")

@app.get("/ui/search", response_class=HTMLResponse)
def render_search_page(request: Request):
    """Render the Buyer Discovery Search Page UI."""
    return templates.TemplateResponse(request=request, name="search.html")

@app.get("/ui/classify", response_class=HTMLResponse)
def render_classify_page(request: Request):
    """Render the AI Email Classification Page UI."""
    return templates.TemplateResponse(request=request, name="classify.html")

@app.get("/ui/send", response_class=HTMLResponse)
def render_send_page(request: Request):
    """Render the Campaign Launch Page UI."""
    return templates.TemplateResponse(request=request, name="send.html")

# ==========================================
# BACKEND REST API ENDPOINTS
# ==========================================

@app.post("/search")
def trigger_buyer_search(request: SearchRequest):
    """Search the web for potential export buyers and save valid leads to buyers.csv."""
    discovered = search_duckduckgo_buyers(
        keyword=request.keyword,
        max_results=request.max_results
    )
    if discovered:
        save_buyers(discovered)
        
    return {
        "status": "success",
        "keyword": request.keyword,
        "new_leads_found": len(discovered)
    }

@app.post("/classify")
def trigger_ai_classification():
    """Use Gemini AI to categorize buyers in buyers.csv into business vs. individual lists."""
    result = classify_buyer_emails()
    return {
        "status": "success",
        "classification_summary": result
    }

@app.post("/send")
def trigger_email_campaign(request: SendRequest):
    """Launch email campaign attaching presentation PDF while preventing duplicates."""
    result = send_outreach_campaign(
        subject=request.subject,
        body_template=request.body_template,
        audience=request.audience,
        send_delay=request.send_delay
    )
    return {
        "status": "completed",
        "campaign_summary": result
    }

@app.post("/upload-presentation")
async def upload_presentation_pdf(file: UploadFile = File(...)):
    """Upload or update the company presentation PDF attached to campaign emails."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are allowed.")

    try:
        # Save uploaded file directly to assets/company_presentation.pdf
        target_path = os.path.join("assets", "company_presentation.pdf")
        os.makedirs("assets", exist_ok=True)
        
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "status": "success",
            "filename": file.filename,
            "message": "Presentation PDF updated successfully in assets/company_presentation.pdf!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload PDF: {str(e)}")

@app.get("/ui/report", response_class=HTMLResponse)
def render_report_page(request: Request):
    """Render the Campaign Analytics & Download Report Page UI."""
    return templates.TemplateResponse(request=request, name="report.html")


@app.get("/report")
def get_campaign_report(download: bool = Query(False, description="Set to true to stream sent_log.csv file")):
    """View campaign summary stats or download sent_log.csv directly."""
    if download:
        if os.path.exists(SENT_LOG_CSV):
            return FileResponse(
                path=SENT_LOG_CSV,
                filename="outreach_sent_log.csv",
                media_type="text/csv"
            )
        else:
            raise HTTPException(status_code=404, detail="Sent log file does not exist yet.")

    total_sent = 0
    total_failed = 0
    if os.path.exists(SENT_LOG_CSV) and os.path.getsize(SENT_LOG_CSV) > 0:
        df = pd.read_csv(SENT_LOG_CSV)
        total_sent = len(df[df["status"] == "sent"])
        total_failed = len(df[df["status"] == "failed"])

    return {
        "report": {
            "total_sent": total_sent,
            "total_failed": total_failed,
            "success_rate": f"{(total_sent / (total_sent + total_failed) * 100):.1f}%" if (total_sent + total_failed) > 0 else "N/A"
        }
    }
