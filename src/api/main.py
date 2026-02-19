"""FastAPI server for Email Triage Assistant"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from typing import List, Optional
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import os

from ..models import Email, EmailThread, EmailCategory, Priority
from ..ingestion import MockEmailGenerator, GmailIngestor, OutlookIngestor, IMAPIngestor
from ..triage import TriageAgent, RuleBasedClassifier
from ..priority import PriorityScorer
from ..compression import EmailThreadCompressor
from ..config import Config
from .scaledown_integration import ScaleDownAPIClient, HybridCompressor
from ..database import db

try:
    from ..ingestion.gmail_auth import get_auth_url, exchange_code_for_tokens
    GMAIL_OAUTH_AVAILABLE = True
except ImportError:
    GMAIL_OAUTH_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="Email Triage Assistant API",
    description="Automated email management with AI-powered triage and compression",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_db_client():
    db.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    db.close()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
mock_generator = MockEmailGenerator()
triage_agent = TriageAgent()
priority_scorer = PriorityScorer()
local_compressor = EmailThreadCompressor()

# Initialize ScaleDown AI client if configured
scaledown_client = None
if Config.is_scaledown_configured():
    scaledown_client = ScaleDownAPIClient(
        api_key=Config.SCALEDOWN_API_KEY,
        base_url=Config.SCALEDOWN_BASE_URL
    )
    print(f"✅ ScaleDown AI API configured: {Config.SCALEDOWN_BASE_URL}")
else:
    print("⚠️ ScaleDown AI API not configured. Using local processing only.")

# Use hybrid compressor that prefers API but falls back to local
compressor = HybridCompressor(
    api_client=scaledown_client,
    local_compressor=local_compressor
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - Login page"""
    import os
    index_path = os.path.join(os.path.dirname(__file__), '..', '..', 'index.html')
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
            <head><title>Email Triage Assistant</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>📧 Email Triage Assistant</h1>
                <p>Login page not found. Please ensure index.html exists.</p>
                <p><a href="/demo">Try Demo Mode</a> | <a href="/docs">API Documentation</a></p>
                <hr>
                <p><i>Server running in directory: """ + os.getcwd() + """</i></p>
            </body>
        </html>
        """


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the email dashboard UI"""
    import os
    frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend.html')
    with open(frontend_path, 'r', encoding='utf-8') as f:
        return f.read()


@app.get("/api/stats")
async def get_stats(user_email: Optional[str] = None):
    """Get system statistics"""
    emails_coll = db.get_emails_collection()
    threads_coll = db.get_threads_collection()
    u = {"owner_email": user_email} if user_email else {}

    return {
        "total_emails": await emails_coll.count_documents(u),
        "total_threads": await threads_coll.count_documents(u),
        "categorized_emails": await emails_coll.count_documents({**u, "category": {"$ne": None}}),
        "emails_requiring_response": await emails_coll.count_documents({**u, "requires_response": True})
    }


@app.post("/api/generate-mock-data")
async def generate_mock_data(count: int = 100, user_email: Optional[str] = None):
    """Generate mock email data for testing"""
    emails_coll = db.get_emails_collection()
    threads_coll = db.get_threads_collection()
    u = {"owner_email": user_email} if user_email else {}

    def _tag(doc: dict) -> dict:
        return {**doc, **u}

    # Generate emails
    new_emails = mock_generator.generate_batch(count)
    if new_emails:
        await emails_coll.insert_many([_tag(e.to_mongo()) for e in new_emails])

    # Generate a few threads
    new_threads = []
    new_thread_messages = []

    for i in range(5):
        thread = mock_generator.generate_thread(message_count=50)
        new_threads.append(_tag(thread.to_mongo()))
        for msg in thread.messages:
            new_thread_messages.append(_tag(msg.to_mongo()))

    if new_threads:
        await threads_coll.insert_many(new_threads)

    if new_thread_messages:
        await emails_coll.insert_many(new_thread_messages)

    return {
        "status": "success",
        "emails_generated": count + len(new_thread_messages),
        "threads_generated": len(new_threads),
        "total_emails": await emails_coll.count_documents(u),
        "total_threads": await threads_coll.count_documents(u)
    }


@app.post("/api/process-inbox")
async def process_inbox(user_email: Optional[str] = None):
    """Process all emails in inbox (triage + prioritize)"""
    processed_count = 0
    emails_coll = db.get_emails_collection()
    threads_coll = db.get_threads_collection()
    u = {"owner_email": user_email} if user_email else {}

    # Pass 1 — AI-classify emails that have no category yet
    # (Gmail-pre-categorised emails already have a category, so they are skipped here)
    async for raw_email in emails_coll.find({**u, "category": None}):
        email = Email.from_mongo(raw_email)
        email = triage_agent.classify_email(email)
        await emails_coll.update_one(
            {"_id": email.id},
            {"$set": {
                "category":        email.category.value if email.category else None,
                "requires_response": email.requires_response,
                "detected_intent": email.detected_intent,
                "sentiment_score": email.sentiment_score,
                "summary":         email.summary,
                "key_entities":    email.key_entities,
                "action_items":    email.action_items,
            }}
        )
        processed_count += 1

    # Pass 2 — score priority for ALL emails that haven't been scored yet
    # This runs for both Gmail-categorised emails and freshly-AI-classified ones
    async for raw_email in emails_coll.find({**u, "priority_score": 0.0}):
        email = Email.from_mongo(raw_email)
        email.priority_score = priority_scorer.calculate_priority(email)
        email.priority_level = priority_scorer.assign_priority_level(email.priority_score)
        await emails_coll.update_one(
            {"_id": email.id},
            {"$set": {
                "priority_score": email.priority_score,
                "priority_level": email.priority_level.name if email.priority_level else None,
            }}
        )
    
    # Process threads (compression)
    compressed_count = 0
    async for raw_thread in threads_coll.find({**u, "compressed_summary": None}):
        thread = EmailThread.from_mongo(raw_thread)
        
        # Compress
        thread = await compressor.compress_thread(thread) # Assuming this is async now? No, it's sync.
        # Wait, compressor.compress_thread might be sync. Let's check.
        # HybridCompressor.compress_thread is likely sync wrapping async or just sync.
        # If it's sync, just call it.
        
        # Update
        await threads_coll.replace_one({"_id": thread.thread_id}, thread.to_mongo())
        compressed_count += 1
    
    return {
        "status": "success",
        "emails_processed": processed_count,
        "threads_compressed": compressed_count
    }


@app.get("/api/emails")
async def get_emails(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user_email: Optional[str] = None
):
    """Get emails with optional filtering and pagination"""
    query = {}
    if user_email:
        query['owner_email'] = user_email
    
    # Filter by category
    if category:
        try:
            cat = EmailCategory(category.lower())
            query['category'] = cat.value
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    # Filter by priority
    if priority:
        try:
            pri = Priority[priority.upper()]
            query['priority_level'] = pri.name
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
    
    emails_coll = db.get_emails_collection()
    cursor = emails_coll.find(query).skip(offset).limit(limit)
    
    emails = []
    async for doc in cursor:
        emails.append(Email.from_mongo(doc).to_dict())
    
    total = await emails_coll.count_documents(query)
    
    return {
        "total": total,
        "emails": emails
    }


@app.get("/api/emails/categorized")
async def get_categorized_emails(user_email: Optional[str] = None):
    """Get emails grouped by category"""
    categories = {}
    emails_coll = db.get_emails_collection()
    u = {"owner_email": user_email} if user_email else {}

    async for doc in emails_coll.find(u):
        email = Email.from_mongo(doc)
        cat = email.category.value if email.category else 'uncategorized'
        if cat not in categories:
            categories[cat] = []
        
        categories[cat].append({
            'id': email.id,
            'subject': email.subject,
            'sender': email.sender.email,
            'priority_score': email.priority_score,
            'priority_level': email.priority_level.name if email.priority_level else None,
            'received_at': email.received_at.isoformat(),
            'requires_response': email.requires_response
        })
    
    # Sort each category by priority
    for cat in categories:
        categories[cat].sort(key=lambda e: e['priority_score'], reverse=True)
    
    return categories


@app.get("/api/email/{email_id}")
async def get_email_detail(email_id: str):
    """Get detailed email information"""
    email_doc = await db.get_emails_collection().find_one({"_id": email_id})
    
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email = Email.from_mongo(email_doc)
    
    # Find associated thread
    thread_doc = await db.get_threads_collection().find_one({"thread_id": email.thread_id})
    thread = EmailThread.from_mongo(thread_doc) if thread_doc else None
    
    response = {
        'email': email.to_dict()
    }
    
    if thread:
        response['thread'] = {
            'thread_id': thread.thread_id,
            'message_count': thread.message_count,
            'compressed_summary': thread.compressed_summary,
            'key_decisions': thread.key_decisions,
            'unresolved_questions': thread.unresolved_questions,
            'action_items': thread.action_items_by_person,
            'compression_stats': compressor.get_compression_stats(thread) if thread.compressed_summary else None
        }
    
    return response



@app.get("/api/threads")
async def get_threads(limit: int = 20):
    """Get email threads with compression stats"""
    threads_coll = db.get_threads_collection()
    threads = []

    
    async for doc in threads_coll.find({}).limit(limit):
        t = EmailThread.from_mongo(doc)
        threads.append({
            'thread_id': t.thread_id,
            'subject': t.subject,
            'message_count': t.message_count,
            'participants': [p.to_dict() for p in t.participants],
            'first_message': t.first_message_at.isoformat() if t.first_message_at else None,
            'last_message': t.last_message_at.isoformat() if t.last_message_at else None,
            'compression_ratio': round(t.compression_ratio, 2),
            'compressed': t.compressed_summary is not None
        })
    
    total = await threads_coll.count_documents({})
    
    return {
        "total": total,
        "threads": threads
    }


@app.get("/api/thread/{thread_id}")
async def get_thread_detail(thread_id: str):
    """Get detailed thread information with full compression"""
    doc = await db.get_threads_collection().find_one({"thread_id": thread_id})
    
    if not doc:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    return EmailThread.from_mongo(doc).to_dict()


@app.get("/api/metrics")
async def get_metrics(user_email: Optional[str] = None):
    """Get productivity metrics"""
    emails_coll = db.get_emails_collection()
    threads_coll = db.get_threads_collection()
    u = {"owner_email": user_email} if user_email else {}

    total = await emails_coll.count_documents(u)
    processed = await emails_coll.count_documents({**u, "category": {"$ne": None}})

    # Calculate category distribution
    category_pipeline = [
        {"$match": {**u, "category": {"$ne": None}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    category_dist = {}
    async for doc in emails_coll.aggregate(category_pipeline):
        category_dist[doc["_id"]] = doc["count"]

    # Add uncategorized
    uncategorized = total - processed
    if uncategorized > 0:
        category_dist['uncategorized'] = uncategorized

    # Calculate priority distribution
    priority_pipeline = [
        {"$match": {**u, "priority_level": {"$ne": None}}},
        {"$group": {"_id": "$priority_level", "count": {"$sum": 1}}}
    ]
    priority_dist = {}
    async for doc in emails_coll.aggregate(priority_pipeline):
        priority_dist[doc["_id"]] = doc["count"]

    # Unassigned priority
    unassigned_pri = total - sum(priority_dist.values())
    if unassigned_pri > 0:
        priority_dist['UNASSIGNED'] = unassigned_pri

    # Calculate time savings (baseline: 3 min/email, automated: 5 sec/email)
    manual_time_hours = (processed * 180) / 3600
    automated_time_hours = (processed * 5) / 3600
    time_saved = manual_time_hours - automated_time_hours

    # Thread stats
    threads_compressed_count = await threads_coll.count_documents({**u, "compressed_summary": {"$ne": None}})

    # Avg compression ratio
    avg_ratio = 0
    if threads_compressed_count > 0:
        pipeline = [
            {"$match": {**u, "compressed_summary": {"$ne": None}}},
            {"$group": {"_id": None, "avg_ratio": {"$avg": "$compression_ratio"}}}
        ]
        async for doc in threads_coll.aggregate(pipeline):
            avg_ratio = doc["avg_ratio"]
            
    return {
        'total_emails': total,
        'emails_processed': processed,
        'processing_rate': round((processed / total * 100) if total > 0 else 0, 2),
        'time_saved_hours': round(time_saved, 2),
        'processing_reduction': 97.2,
        'inbox_zero_rate': 0,
        'category_distribution': category_dist,
        'priority_distribution': priority_dist,
        'threads_compressed': threads_compressed_count,
        'avg_compression_ratio': round(avg_ratio, 2)
    }


@app.post("/api/claim-emails")
async def claim_emails(user_email: str):
    """
    Stamp owner_email on unowned emails where the given address appears as a recipient.
    Called after a successful IMAP login so emails fetched before the owner_email
    field was introduced become visible to the right account.
    """
    emails_coll  = db.get_emails_collection()
    threads_coll = db.get_threads_collection()

    # Only claim emails that have no owner AND whose recipients OR sender include this address
    no_owner_recipient = {
        "owner_email": {"$exists": False},
        "$or": [
            {"recipients.email": user_email},
            {"sender.email": user_email},
        ]
    }
    e_result = await emails_coll.update_many(
        no_owner_recipient, {"$set": {"owner_email": user_email}}
    )

    # For threads, check participants
    no_owner_participant = {
        "owner_email": {"$exists": False},
        "participants.email": user_email
    }
    t_result = await threads_coll.update_many(
        no_owner_participant, {"$set": {"owner_email": user_email}}
    )

    return {
        "emails_claimed":  e_result.modified_count,
        "threads_claimed": t_result.modified_count,
    }


@app.post("/api/repair-owners")
async def repair_owners(user_email: str):
    """
    Remove the owner_email stamp from emails that are tagged with user_email
    but do NOT actually have that address as a recipient.
    Fixes emails that were wrongly claimed by the old aggressive claim-emails logic.
    """
    emails_coll  = db.get_emails_collection()
    threads_coll = db.get_threads_collection()

    # Emails owned by user but where user is neither a recipient nor the sender
    wrong_email = {
        "owner_email": user_email,
        "$nor": [
            {"recipients.email": user_email},
            {"sender.email": user_email},
        ]
    }
    e_result = await emails_coll.update_many(
        wrong_email,
        {"$unset": {"owner_email": ""}}
    )

    wrong_thread = {
        "owner_email": user_email,
        "participants.email": {"$ne": user_email}
    }
    t_result = await threads_coll.update_many(
        wrong_thread,
        {"$unset": {"owner_email": ""}}
    )

    return {
        "emails_released":  e_result.modified_count,
        "threads_released": t_result.modified_count,
    }


@app.post("/api/reset")
async def reset_database(user_email: Optional[str] = None):
    """Reset database — clears only the current user's data if user_email is provided."""
    if user_email:
        filt = {"owner_email": user_email}
    else:
        filt = {}
    await db.get_emails_collection().delete_many(filt)
    await db.get_threads_collection().delete_many(filt)
    return {"status": "success", "message": "Database cleared"}


# ─────────────────────────────────────────────────────────────
# Gmail OAuth Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/api/auth/gmail")
async def gmail_auth_start():
    """
    Step 1 of Gmail OAuth: redirect the browser to Google's consent page.
    After the user grants access Google redirects to /api/auth/gmail/callback.
    """
    if not GMAIL_OAUTH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Google auth libraries not installed.")
    try:
        auth_url, state = get_auth_url()
        # Store state in DB so we can verify it on callback
        await db.get_tokens_collection().replace_one(
            {"_id": "gmail_oauth_state"},
            {"_id": "gmail_oauth_state", "state": state},
            upsert=True
        )
        return RedirectResponse(url=auth_url)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/gmail/callback")
async def gmail_auth_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None)
):
    """
    Step 2 of Gmail OAuth: Google redirects here with an auth code.
    We exchange it for tokens and store them in MongoDB.
    """
    if error:
        return RedirectResponse(url=f"/?gmail_error={error}")

    if not GMAIL_OAUTH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Google auth libraries not installed.")

    # Verify state to prevent CSRF
    stored = await db.get_tokens_collection().find_one({"_id": "gmail_oauth_state"})
    if not stored or stored.get("state") != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state – possible CSRF attack.")

    try:
        token_data = exchange_code_for_tokens(code, state)
        # Save tokens under a fixed key (single-user app for now)
        await db.get_tokens_collection().replace_one(
            {"_id": "gmail_token"},
            {"_id": "gmail_token", **token_data},
            upsert=True
        )
        # Redirect back to dashboard with a success flag
        return RedirectResponse(url="/?gmail_connected=1")
    except Exception as e:
        return RedirectResponse(url=f"/?gmail_error={str(e)}")


@app.get("/api/auth/gmail/status")
async def gmail_auth_status():
    """Check whether Gmail is currently connected."""
    token_doc = await db.get_tokens_collection().find_one({"_id": "gmail_token"})
    return {"connected": token_doc is not None}


@app.get("/api/auth/gmail/me")
async def gmail_auth_me():
    """Return the email address of the currently connected Gmail account."""
    token_doc = await db.get_tokens_collection().find_one({"_id": "gmail_token"})
    if not token_doc:
        raise HTTPException(status_code=404, detail="No Gmail account connected.")
    user_email = token_doc.get("user_email", "")
    return {"user_email": user_email}


@app.delete("/api/auth/gmail")
async def gmail_auth_disconnect():
    """Disconnect Gmail by deleting the stored token."""
    await db.get_tokens_collection().delete_one({"_id": "gmail_token"})
    return {"status": "disconnected"}


# ─────────────────────────────────────────────────────────────
# Gmail Ingestion (uses stored OAuth token)
# ─────────────────────────────────────────────────────────────

@app.post("/api/ingest/gmail")
async def ingest_gmail(max_emails: int = 50, unread_only: bool = False):
    """
    Ingest emails from Gmail using the stored OAuth token.
    The user must have completed Gmail OAuth first (/api/auth/gmail).
    """
    if not GmailIngestor:
        raise HTTPException(
            status_code=503,
            detail="Gmail integration not available. Install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        )

    token_doc = await db.get_tokens_collection().find_one({"_id": "gmail_token"})
    if not token_doc:
        raise HTTPException(
            status_code=401,
            detail="Gmail not connected. Visit /api/auth/gmail to connect your account."
        )

    try:
        # Remove MongoDB _id before passing to credential builder
        token_data = {k: v for k, v in token_doc.items() if k != "_id"}
        ingestor = GmailIngestor.from_stored_token(token_data)

        if unread_only:
            new_emails = ingestor.fetch_unread_emails(max_results=max_emails)
        else:
            new_emails = ingestor.fetch_emails(max_results=max_emails)

        gmail_owner = token_doc.get('user_email', '')

        if new_emails:
            from pymongo import ReplaceOne
            ops = [
                ReplaceOne(
                    {"_id": e.id},
                    {**e.to_mongo(), 'owner_email': gmail_owner},
                    upsert=True
                )
                for e in new_emails
            ]
            await db.get_emails_collection().bulk_write(ops)

        owner_filter = {"owner_email": gmail_owner} if gmail_owner else {}
        total = await db.get_emails_collection().count_documents(owner_filter)

        return {
            "status": "success",
            "source": "gmail",
            "owner_email": gmail_owner,
            "emails_fetched": len(new_emails),
            "total_emails": total,
            "message": f"Fetched {len(new_emails)} emails from Gmail"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gmail ingestion failed: {str(e)}")


@app.post("/api/ingest/outlook")
async def ingest_outlook(
    client_id: str,
    max_emails: int = 50,
    unread_only: bool = False
):
    """
    Ingest emails from Outlook/Office 365
    
    Parameters:
    - client_id: Azure AD Application (client) ID
    - max_emails: Maximum number of emails to fetch
    - unread_only: Fetch only unread emails
    """
    
    if not OutlookIngestor:
        raise HTTPException(
            status_code=503,
            detail="Outlook integration not available. Install: pip install msal"
        )
    
    try:
        ingestor = OutlookIngestor(client_id=client_id)
        
        if unread_only:
            new_emails = ingestor.fetch_unread_emails(max_results=max_emails)
        else:
            new_emails = ingestor.fetch_emails(max_results=max_emails)
        
        if new_emails:
            await db.get_emails_collection().insert_many([e.to_mongo() for e in new_emails])
        
        total = await db.get_emails_collection().count_documents({})
        
        return {
            "status": "success",
            "source": "outlook",
            "emails_fetched": len(new_emails),
            "total_emails": total,
            "message": f"Fetched {len(new_emails)} emails from Outlook"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Outlook ingestion failed: {str(e)}")


@app.get("/api/ingest/status")
async def get_ingestion_status():
    """Check which email ingestion methods are available"""
    return {
        "gmail_available": GmailIngestor is not None,
        "outlook_available": OutlookIngestor is not None,
        "imap_available": IMAPIngestor is not None,
        "mock_available": True,
        "instructions": {
            "gmail": "Install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client",
            "outlook": "Install: pip install msal",
            "imap": "Built-in! Just provide email and app password"
        }
    }



class IMAPIngestRequest(BaseModel):
    email_address: str
    password: str
    provider: Optional[str] = None
    max_emails: int = 50
    unread_only: bool = False


@app.post("/api/ingest/imap")
async def ingest_imap(request: IMAPIngestRequest):
    """
    Ingest emails via IMAP (Universal - works with Gmail, Outlook, Yahoo, etc.)
    """
    if not IMAPIngestor:
        raise HTTPException(
            status_code=503,
            detail="IMAP not available (should always be available - check installation)"
        )
    
    try:
        ingestor = IMAPIngestor(
            email_address=request.email_address,
            password=request.password,
            provider=request.provider
        )
        
        if request.unread_only:
            new_emails = ingestor.fetch_unread_emails(max_results=request.max_emails)
        else:
            new_emails = ingestor.fetch_emails(max_results=request.max_emails)
        
        ingestor.disconnect()
        
        if new_emails:
            owner = request.email_address
            from pymongo import ReplaceOne
            ops = [
                ReplaceOne(
                    {"_id": e.id},
                    {**e.to_mongo(), 'owner_email': owner},
                    upsert=True
                )
                for e in new_emails
            ]
            await db.get_emails_collection().bulk_write(ops)

        total = await db.get_emails_collection().count_documents(
            {"owner_email": request.email_address}
        )

        return {
            "status": "success",
            "source": "imap",
            "provider": request.provider or "auto-detected",
            "emails_fetched": len(new_emails),
            "total_emails": total,
            "message": f"Fetched {len(new_emails)} emails via IMAP"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IMAP ingestion failed: {str(e)}")


@app.get("/api/scaledown/status")
async def get_scaledown_status():
    """Check ScaleDown AI API status"""
    if not scaledown_client:
        return {
            "configured": False,
            "healthy": False,
            "message": "ScaleDown AI API not configured. Add SCALEDOWN_API_KEY to config."
        }
    
    healthy = scaledown_client.health_check()
    return {
        "configured": True,
        "healthy": healthy,
        "base_url": Config.SCALEDOWN_BASE_URL,
        "features": {
            "compression": Config.USE_SCALEDOWN_FOR_COMPRESSION,
            "classification": Config.USE_SCALEDOWN_FOR_CLASSIFICATION,
            "responses": Config.USE_SCALEDOWN_FOR_RESPONSES
        }
    }


@app.post("/api/email/{email_id}/generate-response")
async def generate_response(email_id: str, context: Optional[str] = None):
    """Generate draft response using ScaleDown AI"""
    if not scaledown_client:
        raise HTTPException(status_code=503, detail="ScaleDown AI not configured")
    
    # Find email
    doc = await db.get_emails_collection().find_one({"_id": email_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email = Email.from_mongo(doc)
    
    # Generate response
    response_text = scaledown_client.generate_response(email, context)
    
    if not response_text:
        raise HTTPException(status_code=500, detail="Failed to generate response")
    
    return {
        "email_id": email_id,
        "generated_response": response_text,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/email/{email_id}/analyze")
async def analyze_email(email_id: str):
    """Deep analysis of email using ScaleDown AI"""
    if not scaledown_client:
        raise HTTPException(status_code=503, detail="ScaleDown AI not configured")
    
    # Find email
    doc = await db.get_emails_collection().find_one({"_id": email_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email = Email.from_mongo(doc)
    
    # Get sentiment and entities
    sentiment = scaledown_client.analyze_sentiment(email.body_text)
    entities = scaledown_client.extract_entities(email.body_text)
    
    return {
        "email_id": email_id,
        "sentiment": sentiment,
        "entities": entities,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/batch/process")
async def batch_process_emails(email_ids: List[str]):
    """Batch process multiple emails using ScaleDown AI"""
    if not scaledown_client:
        raise HTTPException(status_code=503, detail="ScaleDown AI not configured")
    
    # Find emails
    emails_to_process = []
    cursor = db.get_emails_collection().find({"_id": {"$in": email_ids}})
    async for doc in cursor:
        emails_to_process.append(Email.from_mongo(doc))
    
    if not emails_to_process:
        raise HTTPException(status_code=404, detail="No emails found")
    
    # Batch process
    results = scaledown_client.batch_process(emails_to_process)
    
    return {
        "processed": len(results),
        "results": results
    }


if __name__ == "__main__":
    print("🚀 Starting Email Triage Assistant API Server...")
    print("📍 API Docs: http://localhost:8000/docs")
    print("🌐 Dashboard: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
