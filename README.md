# Email Triage Assistant

AI-Powered Email Management System with automatic categorization, priority scoring, and thread compression.

## Features

- 🏷️ **Automatic Categorization**: Classifies emails into Urgent, Work, Personal, Newsletter, Promotional, etc.
- ⭐ **Priority Scoring**: Multi-factor algorithm scores emails 0-100 based on sender, keywords, deadlines, and context
- 🗜️ **Thread Compression**: Reduces 50+ message threads by 85% while preserving key information
- 📊 **Productivity Metrics**: Track time saved, inbox zero achievement, and processing efficiency
- 🚀 **Fast API**: RESTful API built with FastAPI

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python src/api/main.py
```

Or using uvicorn directly:

```bash
uvicorn src.api.main:app --reload
```

### 3. Access the Dashboard

Open your browser to: http://localhost:8000

API Documentation: http://localhost:8000/docs

## API Endpoints

### Generate Mock Data
```bash
curl -X POST "http://localhost:8000/api/generate-mock-data?count=100"
```

### Process Inbox (Triage + Prioritize)
```bash
curl -X POST "http://localhost:8000/api/process-inbox"
```

### Get Categorized Emails
```bash
curl "http://localhost:8000/api/emails/categorized"
```

### Get Metrics
```bash
curl "http://localhost:8000/api/metrics"
```

### Get Threads with Compression
```bash
curl "http://localhost:8000/api/threads"
```

## Architecture

```
src/
├── models/          # Data models (Email, EmailThread, etc.)
├── ingestion/       # Email ingestion (Gmail, Outlook, Mock generator)
├── triage/          # Classification agents
├── priority/        # Priority scoring system
├── compression/     # Thread compression (ScaleDown algorithm)
├── api/            # FastAPI server
└── metrics/        # Productivity metrics
```

## Key Components

### 1. Email Data Model
- Structured email representation
- Support for 50+ message threads
- Metadata extraction (entities, action items, etc.)

### 2. Triage Agent
- Rule-based classification
- Category detection (Urgent, Work, Personal, etc.)
- Intent detection (meeting request, info request, etc.)

### 3. Priority Scorer
- Multi-factor scoring (sender, keywords, deadlines, thread context, recency)
- VIP sender management
- Configurable thresholds

### 4. Thread Compressor
- 85% token reduction
- Extracts key decisions, questions, action items
- Timeline generation

## Example Usage

```python
from src.models import Email, EmailAddress
from src.triage import TriageAgent
from src.priority import PriorityScorer

# Create email
email = Email(
    id="123",
    thread_id="thread-1",
    subject="URGENT: Server Down",
    sender=EmailAddress(email="admin@company.com", name="Admin"),
    recipients=[EmailAddress(email="you@company.com")],
    body_text="The production server is down. Please investigate ASAP."
)

# Classify
triage = TriageAgent()
email = triage.classify_email(email)
print(f"Category: {email.category}")  # Output: URGENT

# Score priority
scorer = PriorityScorer()
email.priority_score = scorer.calculate_priority(email)
email.priority_level = scorer.assign_priority_level(email.priority_score)
print(f"Priority: {email.priority_score} ({email.priority_level})")
```

## Metrics

The system tracks:
- **Time Saved**: Baseline 3 min/email vs 5 sec/email automated = 97% reduction
- **Inbox Zero Rate**: % of days achieving inbox zero
- **Processing Efficiency**: Emails processed per hour
- **Compression Ratio**: Average thread compression percentage

## Development

Run in development mode:
```bash
uvicorn src.api.main:app --reload --port 8000
```

## License

MIT

## Author

Email Triage Assistant - AI Systems Architecture Demo
