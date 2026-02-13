"""
Quick test script for real email integration
Tests Gmail and Outlook connectivity
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gmail():
    """Test Gmail integration"""
    print("\n" + "="*70)
    print("  Testing Gmail Integration")
    print("="*70 + "\n")
    
    try:
        from src.ingestion import GmailIngestor
        
        if GmailIngestor is None:
            print("❌ Gmail libraries not installed")
            print("\n📦 Install with:")
            print("   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            return False
        
        print("✅ Gmail libraries installed")
        print("\n📋 Setup checklist:")
        print("   1. Create/download credentials.json from Google Cloud Console")
        print("   2. Enable Gmail API in your project")
        print("   3. Configure OAuth consent screen")
        
        if not os.path.exists('credentials.json'):
            print("\n⚠️  credentials.json not found in project root")
            print("   Download it from: https://console.cloud.google.com/")
            return False
        
        print("\n✅ credentials.json found")
        
        # Try to initialize
        print("\n🔐 Attempting authentication...")
        gmail = GmailIngestor()
        
        if gmail.authenticate():
            print("✅ Gmail authentication successful!")
            
            # Try to fetch a small number of emails
            print("\n📧 Fetching 5 test emails...")
            emails = gmail.fetch_emails(max_results=5)
            
            if emails:
                print(f"✅ Successfully fetched {len(emails)} emails")
                print("\nSample emails:")
                for i, email in enumerate(emails[:3], 1):
                    print(f"   {i}. {email.subject[:60]}")
                return True
            else:
                print("⚠️  No emails fetched (inbox might be empty)")
                return True
        else:
            print("❌ Gmail authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Gmail test failed: {e}")
        return False


def test_outlook():
    """Test Outlook integration"""
    print("\n" + "="*70)
    print("  Testing Outlook Integration")
    print("="*70 + "\n")
    
    try:
        from src.ingestion import OutlookIngestor
        
        if OutlookIngestor is None:
            print("❌ Outlook libraries not installed")
            print("\n📦 Install with:")
            print("   pip install msal")
            return False
        
        print("✅ Outlook libraries installed")
        print("\n📋 Setup checklist:")
        print("   1. Register app in Azure AD")
        print("   2. Get Application (client) ID")
        print("   3. Configure Mail.Read permissions")
        
        client_id = input("\n🔑 Enter your Azure AD Client ID (or press Enter to skip): ").strip()
        
        if not client_id:
            print("⏭️  Skipping Outlook test")
            return False
        
        print("\n🔐 Attempting authentication...")
        outlook = OutlookIngestor(client_id=client_id)
        
        if outlook.authenticate():
            print("✅ Outlook authentication successful!")
            
            # Try to fetch emails
            print("\n📧 Fetching 5 test emails...")
            emails = outlook.fetch_emails(max_results=5)
            
            if emails:
                print(f"✅ Successfully fetched {len(emails)} emails")
                print("\nSample emails:")
                for i, email in enumerate(emails[:3], 1):
                    print(f"   {i}. {email.subject[:60]}")
                return True
            else:
                print("⚠️  No emails fetched (inbox might be empty)")
                return True
        else:
            print("❌ Outlook authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Outlook test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║      Real Email Integration Test                                 ║")
    print("║      Email Triage Assistant                                      ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    
    gmail_ok = test_gmail()
    outlook_ok = test_outlook()
    
    # Summary
    print("\n" + "="*70)
    print("  Test Summary")
    print("="*70 + "\n")
    
    print(f"Gmail:   {'✅ Working' if gmail_ok else '❌ Not configured'}")
    print(f"Outlook: {'✅ Working' if outlook_ok else '❌ Not configured'}")
    
    if gmail_ok or outlook_ok:
        print("\n🎉 At least one email integration is working!")
        print("\n🚀 Next steps:")
        print("   1. Start the API server:")
        print("      python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        print("\n   2. Ingest emails via API:")
        if gmail_ok:
            print("      curl -X POST 'http://localhost:8000/api/ingest/gmail?max_emails=50'")
        if outlook_ok:
            print("      curl -X POST 'http://localhost:8000/api/ingest/outlook?client_id=YOUR_ID&max_emails=50'")
        print("\n   3. View in dashboard:")
        print("      http://localhost:8000/dashboard")
    else:
        print("\n📚 Setup instructions:")
        print("   See REAL_EMAIL_SETUP.md for detailed setup guide")
    
    print("\n")


if __name__ == "__main__":
    main()
