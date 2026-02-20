# Real Email Integration Guide

## Connect Your Gmail or Outlook Inbox

Your Email Triage Assistant can now process **real emails** from your inbox!

## 📧 Gmail Integration

### Step 1: Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Gmail API**:
   - Search for "Gmail API" in the API Library
   - Click "Enable"

### Step 2: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth  client ID**
3. Choose **Desktop app** as application type
4. Name it `Email Triage Assistant`
5. Click **Create**
6. Download the JSON file
7. **Save it as `credentials.json`** in your project root

### Step 3: Install Gmail Libraries

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Step 4: Fetch Your Emails

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/ingest/gmail?max_emails=50&unread_only=false"
```

**Via Python:**
```python
from src.ingestion import GmailIngestor

# Initialize and authenticate
gmail = GmailIngestor(credentials_path='credentials.json')
gmail.authenticate()  # Opens browser for OAuth

# Fetch emails
emails = gmail.fetch_emails(max_results=50)
unread = gmail.fetch_unread_emails(max_results=20)
today = gmail.fetch_today_emails()
```

### Gmail Query Examples

```python
# Fetch from specific sender
emails = gmail.fetch_emails(query='from:boss@company.com')

# Fetch unread in inbox
emails = gmail.fetch_emails(query='is:unread in:inbox')

# Fetch starred emails
emails = gmail.fetch_emails(query='is:starred')

# Fetch emails with attachments
emails = gmail.fetch_emails(query='has:attachment')

# Fetch from last week
emails = gmail.fetch_emails(query='newer_than:7d')
```

---

## 📨 Outlook/Office 365 Integration

### Step 1: Register Azure AD Application

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Name: `Email Triage Assistant`
5. Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
6. Redirect URI: **Public client/native** → `http://localhost`
7. Click **Register**

### Step 2: Configure API Permissions

1. In your app, go to **API permissions**
2. Click **Add a permission** → **Microsoft Graph**
3. Choose **Delegated permissions**
4. Add these permissions:
   - `Mail.Read`
   - `Mail.ReadWrite` (optional, for marking as read)
   - `User.Read`
5. Click **Add permissions**
6. Click **Grant admin consent** (if you have admin rights)

### Step 3: Get Your Client ID

1. In **Overview** page, copy **Application (client) ID**
2. Store it securely

### Step 4: Install Outlook Libraries

```bash
pip install msal
```

### Step 5: Fetch Your Emails

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/ingest/outlook?client_id=YOUR_CLIENT_ID&max_emails=50"
```

**Via Python:**
```python
from src.ingestion import OutlookIngestor

# Initialize with your client ID
outlook = OutlookIngestor(client_id='your-client-id-here')
outlook.authenticate()  # Opens browser for OAuth

# Fetch emails
emails = outlook.fetch_emails(max_results=50)
unread = outlook.fetch_unread_emails(max_results=20)
important = outlook.fetch_important_emails()
today = outlook.fetch_today_emails()
```

### Outlook Filter Examples

```python
# Fetch from specific sender
emails = outlook.fetch_emails_by_sender('boss@company.com')

# Fetch by date range
from datetime import datetime
today = datetime.now().date().isoformat()
emails = outlook.fetch_emails(
    filter_query=f"receivedDateTime ge {today}T00:00:00Z"
)

# Fetch with specific subject
emails = outlook.fetch_emails(
    filter_query="contains(subject, 'urgent')"
)

# Fetch flagged emails
emails = outlook.fetch_emails(
    filter_query="flag/flagStatus eq 'flagged'"
)
```

---

## 🔄 Complete Workflow

### 1. Ingest Real Emails

```python
from src.ingestion import GmailIngestor
from src.triage import TriageAgent
from src.priority import PriorityScorer

# Fetch emails
gmail = GmailIngestor()
gmail.authenticate()
emails = gmail.fetch_unread_emails(max_results=100)

print(f"Fetched {len(emails)} unread emails")
```

### 2. Classify and Prioritize

```python
# Initialize triage components
triage = TriageAgent()
scorer = PriorityScorer()

# Process each email
for email in emails:
    # Classify
    email = triage.classify_email(email)
    
    # Score priority
    email.priority_score, email.priority_level = scorer.calculate_priority(email)
    
    print(f"{email.priority_level.name:8} | {email.category.name:12} | {email.subject}")
```

### 3. Process with ScaleDown AI

```python
from src.api.scaledown_integration import ScaleDownAPIClient
from src.config import Config

# Use your ScaleDown AI for advanced processing
if Config.is_scaledown_configured():
    client = ScaleDownAPIClient(Config.SCALEDOWN_API_KEY, Config.SCALEDOWN_BASE_URL)
    
    for email in emails:
        # Generate smart response
        response = client.generate_response(email)
        email.draft_response = response
        
        # Extract entities
        entities = client.extract_entities(email.body_text)
        email.key_entities = entities
```

---

## 🌐 Using the Web Dashboard

### Update Dashboard to Ingest Real Emails

Add buttons to your dashboard (`frontend.html`):

```javascript
// Add to your controls section
async function ingestGmail() {
    try {
        const response = await fetch('http://localhost:8000/api/ingest/gmail?max_emails=50&unread_only=true', {
            method: 'POST'
        });
        const data = await response.json();
        alert(`Fetched ${data.emails_fetched} emails from Gmail!`);
        await loadStats();
        await loadEmails();
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function ingestOutlook() {
    const clientId = prompt('Enter your Azure AD Client ID:');
    if (!clientId) return;
    
    try {
        const response = await fetch(`http://localhost:8000/api/ingest/outlook?client_id=${clientId}&max_emails=50&unread_only=true`, {
            method: 'POST'
        });
        const data = await response.json();
        alert(`Fetched ${data.emails_fetched} emails from Outlook!`);
        await loadStats();
        await loadEmails();
    } catch (error) {
        alert('Error: ' + error.message);
    }
}
```

Add buttons in HTML:

```html
<button class="btn btn-primary" onclick="ingestGmail()">
    📧 Fetch from Gmail
</button>
<button class="btn btn-primary" onclick="ingestOutlook()">
    📨 Fetch from Outlook
</button>
```

---

## 🔒 Security Best Practices

### Gmail
- ✅ `credentials.json` is in `.gitignore`
- ✅ `token.json` (generated after auth) is also ignored
- ✅ OAuth tokens are stored locally and encrypted

### Outlook
- ✅ Client ID is safe to share (it's public)
- ✅ Never commit client secrets if using confidential app
- ✅ Tokens are cached securely by MSAL

### Environment Variables (Recommended)

```bash
# Windows PowerShell
$env:GMAIL_CREDENTIALS_PATH="path/to/credentials.json"
$env:OUTLOOK_CLIENT_ID="your-client-id"

# Linux/Mac
export GMAIL_CREDENTIALS_PATH="path/to/credentials.json"
export OUTLOOK_CLIENT_ID="your-client-id"
```

---

## 🧪 Testing Your Integration

```python
# test_real_email.py
from src.ingestion import GmailIngestor, OutlookIngestor

def test_gmail():
    print("Testing Gmail integration...")
    try:
        gmail = GmailIngestor()
        gmail.authenticate()
        emails = gmail.fetch_emails(max_results=5)
        print(f"✅ Successfully fetched {len(emails)} emails from Gmail")
        for email in emails:
            print(f"   - {email.subject}")
        return True
    except Exception as e:
        print(f"❌ Gmail test failed: {e}")
        return False

def test_outlook():
    print("\nTesting Outlook integration...")
    client_id = input("Enter your Azure AD Client ID: ")
    try:
        outlook = OutlookIngestor(client_id=client_id)
        outlook.authenticate()
        emails = outlook.fetch_emails(max_results=5)
        print(f"✅ Successfully fetched {len(emails)} emails from Outlook")
        for email in emails:
            print(f"   - {email.subject}")
        return True
    except Exception as e:
        print(f"❌ Outlook test failed: {e}")
        return False

if __name__ == "__main__":
    test_gmail()
    test_outlook()
```

---

## 📊 Check Integration Status

```bash
curl http://localhost:8000/api/ingest/status
```

Response:
```json
{
  "gmail_available": true,
  "outlook_available": true,
  "mock_available": true
}
```

---

## 🚀 Production Deployment

### Environment Variables

```bash
# Gmail
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json
GMAIL_TOKEN_PATH=/path/to/token.json

# Outlook
OUTLOOK_CLIENT_ID=your-azure-client-id
OUTLOOK_CLIENT_SECRET=your-secret (if using confidential app)

# ScaleDown AI
SCALEDOWN_API_KEY=your-api-key
SCALEDOWN_BASE_URL=https://api.scaledown.ai/v1
```

### Scheduled Email Processing

Use cron (Linux) or Task Scheduler (Windows) to fetch emails periodically:

```bash
# Fetch and process emails every hour
0 * * * * cd /path/to/project && python -c "from src.ingestion import GmailIngestor; from src.triage import TriageAgent; g=GmailIngestor(); g.authenticate(); emails=g.fetch_unread_emails(); [TriageAgent().classify_email(e) for e in emails]"
```

---

## 🎉 You're Ready!

Your Email Triage Assistant can now:
- ✅ Read emails from Gmail
- ✅ Read emails from Outlook/Office 365
- ✅ Classify and prioritize real emails
- ✅ Compress email threads
- ✅ Generate responses with ScaleDown AI
- ✅ Track productivity metrics

**Start processing your real inbox today!** 🚀
