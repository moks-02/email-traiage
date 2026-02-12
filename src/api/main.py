"""FastAPI server for Email Triage Assistant"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Optional
import uvicorn
from datetime import datetime

from ..models import Email, EmailThread, EmailCategory, Priority
from ..ingestion import MockEmailGenerator
from ..triage import TriageAgent, RuleBasedClassifier
from ..priority import PriorityScorer
from ..compression import EmailThreadCompressor
from ..config import Config
from .scaledown_integration import ScaleDownAPIClient, HybridCompressor

# Initialize FastAPI app
app = FastAPI(
    title="Email Triage Assistant API",
    description="Automated email management with AI-powered triage and compression",
    version="1.0.0"
)

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

# In-memory storage (for demo - replace with database in production)
emails_db: List[Email] = []
threads_db: List[EmailThread] = []


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with welcome page"""
    return """
    <html>
        <head>
            <title>Email Triage Assistant</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 800px; 
                    margin: 50px auto; 
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                h1 { font-size: 2.5em; margin-bottom: 10px; }
                .subtitle { font-size: 1.2em; opacity: 0.9; margin-bottom: 30px; }
                .card { 
                    background: rgba(255,255,255,0.1); 
                    padding: 20px; 
                    border-radius: 10px; 
                    margin: 15px 0;
                    backdrop-filter: blur(10px);
                }
                a { 
                    color: #ffd700; 
                    text-decoration: none; 
                    font-weight: bold;
                }
                a:hover { text-decoration: underline; }
                code { 
                    background: rgba(0,0,0,0.3); 
                    padding: 3px 8px; 
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                }
                .big-button {
                    display: inline-block;
                    background: rgba(255, 255, 255, 0.2);
                    padding: 20px 40px;
                    border-radius: 10px;
                    margin: 20px 10px;
                    font-size: 1.2em;
                    transition: all 0.3s;
                }
                .big-button:hover {
                    background: rgba(255, 255, 255, 0.3);
                    transform: translateY(-3px);
                }
            </style>
        </head>
        <body>
            <h1>📧 Email Triage Assistant</h1>
            <div class="subtitle">AI-Powered Email Management at Scale</div>
            
            <div class="card">
                <h2>🚀 Quick Access</h2>
                <a href="/dashboard" class="big-button">📊 Open Dashboard</a>
                <a href="/docs" class="big-button">📚 API Documentation</a>
            </div>
            
            <div class="card">
                <h2>✨ Features</h2>
                <ul>
                    <li>Automatic email categorization (Urgent, Work, Personal, Newsletter, etc.)</li>
                    <li>Multi-factor priority scoring (0-100 scale)</li>
                    <li>Thread compression with 85% token reduction</li>
                    <li>Smart response detection</li>
                    <li>Real-time productivity metrics</li>
                    <li>ScaleDown AI Integration</li>
                </ul>
            </div>
            
            <div class="card">
                <h2>📊 API Status</h2>
                <p>Status: <strong style="color: #00ff00;">✓ Online</strong></p>
                <p>Emails in database: <strong id="email-count">Loading...</strong></p>
                <p>Threads in database: <strong id="thread-count">Loading...</strong></p>
            </div>
            
            <script>
                fetch('/api/stats')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('email-count').textContent = data.total_emails;
                        document.getElementById('thread-count').textContent = data.total_threads;
                    });
            </script>
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
async def get_stats():
    """Get system statistics"""
    return {
        "total_emails": len(emails_db),
        "total_threads": len(threads_db),
        "categorized_emails": sum(1 for e in emails_db if e.category is not None),
        "emails_requiring_response": sum(1 for e in emails_db if e.requires_response)
    }


@app.post("/api/generate-mock-data")
async def generate_mock_data(count: int = 100):
    """Generate mock email data for testing"""
    global emails_db, threads_db
    
    # Generate emails
    new_emails = mock_generator.generate_batch(count)
    emails_db.extend(new_emails)
    
    # Generate a few threads
    new_threads = []
    for i in range(5):
        thread = mock_generator.generate_thread(message_count=50)
        new_threads.append(thread)
        # Add thread messages to emails_db
        emails_db.extend(thread.messages)
    
    threads_db.extend(new_threads)
    
    return {
        "status": "success",
        "emails_generated": count,
        "threads_generated": len(new_threads),
        "total_emails": len(emails_db),
        "total_threads": len(threads_db)
    }


@app.post("/api/process-inbox")
async def process_inbox():
    """Process all emails in inbox (triage + prioritize)"""
    processed_count = 0
    
    for email in emails_db:
        # Skip already processed emails
        if email.category and email.priority_score > 0:
            continue
        
        # Triage
        email = triage_agent.classify_email(email)
        
        # Calculate priority
        email.priority_score = priority_scorer.calculate_priority(email)
        email.priority_level = priority_scorer.assign_priority_level(email.priority_score)
        
        processed_count += 1
    
    # Process threads (compression)
    compressed_count = 0
    for thread in threads_db:
        if not thread.compressed_summary:
            thread = compressor.compress_thread(thread)
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
    limit: int = 50
):
    """Get emails with optional filtering"""
    filtered_emails = emails_db
    
    # Filter by category
    if category:
        try:
            cat = EmailCategory(category.lower())
            filtered_emails = [e for e in filtered_emails if e.category == cat]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    # Filter by priority
    if priority:
        try:
            pri = Priority[priority.upper()]
            filtered_emails = [e for e in filtered_emails if e.priority_level == pri]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
    
    # Limit results
    filtered_emails = filtered_emails[:limit]
    
    return {
        "total": len(filtered_emails),
        "emails": [e.to_dict() for e in filtered_emails]
    }


@app.get("/api/emails/categorized")
async def get_categorized_emails():
    """Get emails grouped by category"""
    categories = {}
    
    for email in emails_db:
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
    email = next((e for e in emails_db if e.id == email_id), None)
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Find associated thread
    thread = next((t for t in threads_db if t.thread_id == email.thread_id), None)
    
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
    limited_threads = threads_db[:limit]
    
    return {
        "total": len(threads_db),
        "threads": [
            {
                'thread_id': t.thread_id,
                'subject': t.subject,
                'message_count': t.message_count,
                'participants': [p.to_dict() for p in t.participants],
                'first_message': t.first_message_at.isoformat() if t.first_message_at else None,
                'last_message': t.last_message_at.isoformat() if t.last_message_at else None,
                'compression_ratio': round(t.compression_ratio, 2),
                'compressed': t.compressed_summary is not None
            }
            for t in limited_threads
        ]
    }


@app.get("/api/thread/{thread_id}")
async def get_thread_detail(thread_id: str):
    """Get detailed thread information with full compression"""
    thread = next((t for t in threads_db if t.thread_id == thread_id), None)
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    return thread.to_dict()


@app.get("/api/metrics")
async def get_metrics():
    """Get productivity metrics"""
    total = len(emails_db)
    processed = sum(1 for e in emails_db if e.category is not None)
    
    # Calculate category distribution
    category_dist = {}
    for email in emails_db:
        cat = email.category.value if email.category else 'uncategorized'
        category_dist[cat] = category_dist.get(cat, 0) + 1
    
    # Calculate priority distribution
    priority_dist = {}
    for email in emails_db:
        pri = email.priority_level.name if email.priority_level else 'UNASSIGNED'
        priority_dist[pri] = priority_dist.get(pri, 0) + 1
    
    # Calculate time savings (baseline: 3 min/email, automated: 5 sec/email)
    manual_time_hours = (processed * 180) / 3600  # 180 seconds = 3 minutes
    automated_time_hours = (processed * 5) / 3600  # 5 seconds
    time_saved = manual_time_hours - automated_time_hours
    
    return {
        'total_emails': total,
        'emails_processed': processed,
        'processing_rate': round((processed / total * 100) if total > 0 else 0, 2),
        'time_saved_hours': round(time_saved, 2),
        'processing_reduction': 97.2,  # (180-5)/180 * 100
        'inbox_zero_rate': 0,  # Would be calculated from user data
        'category_distribution': category_dist,
        'priority_distribution': priority_dist,
        'threads_compressed': sum(1 for t in threads_db if t.compressed_summary),
        'avg_compression_ratio': round(
            sum(t.compression_ratio for t in threads_db if t.compressed_summary) / 
            len([t for t in threads_db if t.compressed_summary])
            if any(t.compressed_summary for t in threads_db) else 0,
            2
        )
    }


@app.post("/api/reset")
async def reset_database():
    """Reset database (clear all data)"""
    global emails_db, threads_db
    emails_db = []
    threads_db = []
    
    return {"status": "success", "message": "Database cleared"}


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
    email = next((e for e in emails_db if e.id == email_id), None)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
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
    email = next((e for e in emails_db if e.id == email_id), None)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
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
    emails_to_process = [e for e in emails_db if e.id in email_ids]
    
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
