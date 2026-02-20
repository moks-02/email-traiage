# 🚀 Quick Start Guide - User Interface

## Running the Email Triage Assistant

### Step 1: Start the Server

Open a terminal and run:

```bash
cd "c:\Users\admin\Desktop\Email Triage Assistant"
python src/api/main.py
```

Or using uvicorn:

```bash
uvicorn src.api.main:app --reload --port 8000
```

The server will start on **http://localhost:8000**

### Step 2: Open the Login Page

1. Open your browser
2. Go to **http://localhost:8000** (this is the login page)
3. You'll see the Email Triage Assistant login interface

### Step 3: Connect Your Email

#### For Gmail Users:

1. **Enable 2-Factor Authentication**:
   - Go to [myaccount.google.com/security](https://myaccount.google.com/security)
   - Enable 2FA if not already enabled

2. **Generate App Password**:
   - Click on "App passwords" (under 2-Step Verification)
   - Select "Mail" and "Other (Custom name)"
   - Name it "Email Triage"
   - Copy the 16-character password

3. **Connect**:
   - Enter your Gmail address: `your.email@gmail.com`
   - Select Provider: **Gmail** (or leave as Auto-detect)
   - Enter the app password you just generated
   - Click "🚀 Connect & Start"

#### For Outlook Users:

1. **Generate App Password**:
   - Go to [account.microsoft.com/security](https://account.microsoft.com/security)
   - Click "Advanced security options"
   - Under "App passwords", click "Create a new app password"
   - Copy the generated password

2. **Connect**:
   - Enter your Outlook address: `your.email@outlook.com`
   - Select Provider: **Outlook**
   - Enter the app password
   - Click "🚀 Connect & Start"

#### For Other Providers (Yahoo, iCloud, AOL):

Click "❓ How to get an App Password?" button on the login page for specific instructions for your provider.

### Step 4: Wait for Processing

The system will:
1. ✅ Connect to your email via IMAP
2. 📧 Fetch up to 100 emails
3. 🤖 Process them with AI (categorize, prioritize, compress threads)
4. 🎉 Redirect you to the dashboard

This usually takes 10-30 seconds depending on the number of emails.

### Step 5: Use the Dashboard

Once logged in, you can:

- **View emails** organized by category and priority
- **Search** for specific emails
- **Filter** by category (Urgent, Work, Personal, etc.) or priority
- **Click any email** to view full details
- **Refresh Emails** to fetch new messages from your inbox
- **Process Inbox** to re-analyze emails with AI

## Available Pages

| URL | Description |
|-----|-------------|
| http://localhost:8000 | **Login page** - Connect your email |
| http://localhost:8000/dashboard | **Main dashboard** - View your emails (requires login) |
| http://localhost:8000/demo | **Demo mode** - Try with mock emails |
| http://localhost:8000/docs | **API documentation** - Interactive API docs |

## Troubleshooting

### "Connection failed" Error

**Problem**: Can't connect to email account

**Solutions**:
1. ✅ Make sure you're using an **app password**, not your regular password
2. ✅ For Gmail, check that 2FA is enabled
3. ✅ For Outlook, verify app password was created correctly
4. ✅ Check your email address is typed correctly
5. ✅ Make sure the server is running (check terminal)

### "Server not responding"

**Problem**: Can't access http://localhost:8000

**Solutions**:
1. ✅ Check the terminal - is the server running?
2. ✅ Look for "Uvicorn running on http://127.0.0.1:8000" message
3. ✅ Try restarting the server:
   ```bash
   # Stop: Press Ctrl+C in the terminal
   # Start: python src/api/main.py
   ```
4. ✅ Check if port 8000 is already in use:
   ```powershell
   netstat -ano | findstr :8000
   # If something is using it, kill that process or use a different port
   ```

### "No emails appearing"

**Problem**: Connected successfully but no emails shown

**Solutions**:
1. ✅ Click "⚡ Process Inbox" button to trigger processing
2. ✅ Check the browser console (F12) for errors
3. ✅ Verify emails were fetched - check terminal output
4. ✅ Try clicking "🔄 Refresh Emails"

## Demo Mode (No Email Account Needed)

Want to try without connecting your email?

1. Go to **http://localhost:8000/demo**
2. Click "📨 Generate Mock Emails"
3. Click "⚡ Process Inbox"
4. Explore the features with sample data!

## Features Overview

### 📊 Dashboard Features

- **Email List**: All your emails with previews
- **Category Badges**: Visual categorization (Urgent, Work, Personal, etc.)
- **Priority Scores**: 0-100 priority scoring with levels
- **Smart Filters**: Filter by category or priority
- **Search**: Full-text search across all emails
- **Email Details**: Click any email to see full content, entities, and action items

### 🤖 AI Features

- **Automatic Categorization**: 7 categories (Urgent, Work, Personal, Newsletter, Promotional, Spam, Social)
- **Priority Scoring**: Multi-factor algorithm considering sender, keywords, deadlines, thread context
- **Thread Compression**: Reduces long conversations by 85-98% while preserving key information
- **Entity Extraction**: Identifies people, dates, and important information
- **Action Items**: Automatically detects tasks and to-dos

### 📈 Productivity Metrics

- **Total Emails**: Number of emails in your inbox
- **Processed**: Emails analyzed by AI
- **Threads**: Compressed conversation threads
- **Time Saved**: Estimated hours saved vs manual triage

## Next Steps

Once you're comfortable with the interface:

1. **Schedule Regular Fetches**: Set up a cron job or scheduled task to fetch new emails automatically
2. **Customize Categories**: Edit `src/triage/rule_classifier.py` to add custom categories
3. **Adjust Priority Weights**: Modify `src/priority/priority_scorer.py` to fine-tune scoring
4. **Add Database**: Replace in-memory storage with PostgreSQL or MongoDB for persistence
5. **Deploy**: Host on Heroku, AWS, or Azure for always-on access

## Support

- 📚 Full documentation: [README.md](README.md)
- 🔧 API reference: http://localhost:8000/docs
- 🐛 Issues: [GitHub Issues](https://github.com/moks-02/email-traiage/issues)

---

**Enjoy your AI-powered email assistant! 🎉**
