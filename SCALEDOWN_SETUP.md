# ScaleDown AI API Integration Guide

## Overview
Your Email Triage Assistant now supports integration with **ScaleDown AI API** for enhanced email processing capabilities including:
- Advanced thread compression
- AI-powered email classification
- Smart response generation
- Entity extraction
- Sentiment analysis
- Batch processing

## Setup Instructions

### 1. Get Your API Key
- Sign up or log in to your ScaleDown AI account
- Navigate to API settings
- Copy your API key

### 2. Configure the Application

**Option A: Using config.py (Recommended)**
```bash
# Copy the example config
cp config.example.py config.py

# Edit config.py and add your API key
# SCALEDOWN_API_KEY = "sk-your-actual-key-here"
# SCALEDOWN_BASE_URL = "https://api.scaledown.ai/v1"  # or your custom endpoint
```

**Option B: Using Environment Variables**
```bash
# Windows PowerShell
$env:SCALEDOWN_API_KEY="sk-your-actual-key-here"
$env:SCALEDOWN_BASE_URL="https://api.scaledown.ai/v1"

# Linux/Mac
export SCALEDOWN_API_KEY="sk-your-actual-key-here"
export SCALEDOWN_BASE_URL="https://api.scaledown.ai/v1"
```

### 3. Install Dependencies
```bash
pip install requests
```

### 4. Test the Integration
```bash
python test_scaledown.py
```

## API Endpoints

### Check API Status
```http
GET /api/scaledown/status
```
Returns ScaleDown AI configuration status and health check.

### Generate Email Response
```http
POST /api/email/{email_id}/generate-response
Content-Type: application/json

{
  "context": "Optional additional context"
}
```

### Analyze Email
```http
POST /api/email/{email_id}/analyze
```
Returns sentiment analysis and extracted entities.

### Batch Process Emails
```http
POST /api/batch/process
Content-Type: application/json

{
  "email_ids": ["id1", "id2", "id3"]
}
```

## Feature Configuration

Edit `config.py` to enable/disable features:

```python
# Enable/disable specific ScaleDown AI features
USE_SCALEDOWN_FOR_COMPRESSION = True   # Use API for thread compression
USE_SCALEDOWN_FOR_CLASSIFICATION = True  # Use API for email classification
USE_SCALEDOWN_FOR_RESPONSES = True     # Use API for response generation
USE_SCALEDOWN_FOR_ENTITIES = True      # Use API for entity extraction
```

## Fallback Behavior

The system uses a **hybrid approach**:
1. Tries to use ScaleDown AI API first (if configured and healthy)
2. Falls back to local processing if:
   - API key not configured
   - API is unavailable
   - Request times out
   - Error occurs

This ensures your system always works, even if the API is down.

## API Expected Formats

Your ScaleDown AI API should support these endpoints:

### POST /v1/compress/thread
```json
Request:
{
  "thread_id": "string",
  "subject": "string",
  "message_count": 50,
  "messages": [
    {
      "id": "msg-123",
      "sender": "user@example.com",
      "timestamp": "2026-02-08T10:00:00",
      "content": "Email body text..."
    }
  ]
}

Response:
{
  "summary": "Compressed summary...",
  "decisions": ["Decision 1", "Decision 2"],
  "questions": ["Question 1"],
  "action_items": {"person@example.com": ["Action 1"]},
  "original_tokens": 3500,
  "compressed_tokens": 150,
  "compression_ratio": 95.7
}
```

### POST /v1/classify/email
```json
Request:
{
  "email_id": "email-123",
  "subject": "Meeting tomorrow",
  "sender": "boss@company.com",
  "body": "Email text...",
  "received_at": "2026-02-08T10:00:00"
}

Response:
{
  "category": "work",
  "confidence": 0.95,
  "detected_intent": "schedule_meeting"
}
```

### POST /v1/generate/response
```json
Request:
{
  "email_id": "email-123",
  "subject": "Question about project",
  "sender": "colleague@company.com",
  "body": "Email text...",
  "context": "Optional context"
}

Response:
{
  "response": "Dear Colleague,\n\nThank you for your email..."
}
```

### POST /v1/extract/entities
```json
Request:
{
  "text": "Meeting with John Smith on Monday at 2pm in New York office."
}

Response:
{
  "entities": [
    {"type": "person", "value": "John Smith"},
    {"type": "date", "value": "Monday"},
    {"type": "time", "value": "2pm"},
    {"type": "location", "value": "New York office"}
  ]
}
```

### POST /v1/analyze/sentiment
```json
Request:
{
  "text": "I'm very happy with the results!"
}

Response:
{
  "sentiment": "positive",
  "score": 0.9,
  "confidence": 0.95
}
```

### POST /v1/batch/process
```json
Request:
{
  "emails": [
    {"id": "1", "subject": "...", "sender": "...", "body": "..."},
    {"id": "2", "subject": "...", "sender": "...", "body": "..."}
  ]
}

Response:
{
  "results": [
    {"email_id": "1", "category": "work", "priority": 85},
    {"email_id": "2", "category": "personal", "priority": 45}
  ]
}
```

### GET /v1/health
```json
Response:
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## Usage Examples

See `test_scaledown.py` for complete examples.

## Troubleshooting

### API Key Issues
```
⚠️ ScaleDown AI API not configured
```
**Solution:** Add your API key to `config.py` or environment variables.

### Connection Errors
```
ScaleDown API Error: HTTPConnectionPool...
```
**Solution:** Check your SCALEDOWN_BASE_URL is correct and your network allows outbound HTTPS.

### Timeout Errors
```
ScaleDown API Error: Request timeout
```
**Solution:** Increase SCALEDOWN_TIMEOUT in config.py (default: 30 seconds).

### Fallback Mode
```
Falling back to local compression...
```
**Info:** This is normal when API is unavailable. System continues with local processing.

## Security Best Practices

1. **Never commit config.py** - Add to `.gitignore`
2. **Use environment variables** in production
3. **Rotate API keys** regularly
4. **Use HTTPS** for all API calls
5. **Monitor API usage** to detect anomalies

## Performance Tips

1. **Use batch processing** for multiple emails
2. **Enable caching** for repeated requests
3. **Set appropriate timeouts** based on your needs
4. **Monitor API health** before making requests
5. **Use async operations** for better throughput

## Support

For ScaleDown AI API support:
- Documentation: https://docs.scaledown.ai
- Email: support@scaledown.ai
- Status page: https://status.scaledown.ai
