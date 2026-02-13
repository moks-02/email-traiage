"""
Simple IMAP Email Integration Test
No Azure or Google Cloud Console required!
"""

from src.ingestion import IMAPIngestor, get_provider_help

def main():
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║      IMAP Email Integration - Simple Setup                       ║")
    print("║      Works with Gmail, Outlook, Yahoo, and more!                 ║")
    print("╚═══════════════════════════════════════════════════════════════════╝\n")
    
    print("✨ No Azure AD or Google Cloud Console required!")
    print("✨ Just your email and app password\n")
    
    # Show setup instructions
    choice = input("Show provider setup instructions? (y/n): ").lower()
    if choice == 'y':
        get_provider_help()
    
    print("\n" + "="*70)
    print("  Connect Your Email")
    print("="*70 + "\n")
    
    # Get email credentials
    email_address = input("Enter your email address: ").strip()
    password = input("Enter your app password: ").strip()
    
    if not email_address or not password:
        print("❌ Email and password are required")
        return
    
    # Optional: specify provider
    print("\n💡 Provider will be auto-detected from email address")
    provider = input("Or specify provider (gmail/outlook/yahoo/icloud/aol) [auto]: ").strip() or None
    
    print("\n" + "="*70)
    print("  Fetching Emails")
    print("="*70 + "\n")
    
    try:
        # Initialize IMAP ingestor
        imap = IMAPIngestor(
            email_address=email_address,
            password=password,
            provider=provider
        )
        
        # Connect
        if not imap.connect():
            print("\n❌ Failed to connect. Check your credentials.")
            print("💡 Make sure you're using an App Password, not your regular password")
            return
        
        # List folders
        print("\n📁 Available folders:")
        folders = imap.list_folders()
        for folder in folders[:10]:  # Show first 10
            print(f"   • {folder}")
        
        # Fetch emails
        print("\n📧 Fetching 10 most recent emails from INBOX...")
        emails = imap.fetch_emails(max_results=10)
        
        if emails:
            print(f"\n✅ Successfully fetched {len(emails)} emails!\n")
            print("Sample emails:")
            print("-" * 70)
            for i, email in enumerate(emails[:5], 1):
                print(f"\n{i}. From: {email.sender.name or email.sender.email}")
                print(f"   Subject: {email.subject[:60]}")
                print(f"   Date: {email.received_at.strftime('%Y-%m-%d %H:%M')}")
                print(f"   Preview: {email.body_text[:100]}...")
            
            # Test unread
            print("\n" + "="*70)
            print("📬 Fetching unread emails...")
            unread = imap.fetch_unread_emails(max_results=20)
            print(f"✅ Found {len(unread)} unread emails")
            
            # Success message
            print("\n" + "="*70)
            print("  ✅ SUCCESS! Integration Working!")
            print("="*70)
            print("\n🚀 Next Steps:")
            print("   1. Start the API server:")
            print("      python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
            print("\n   2. Fetch via API:")
            print(f"      POST http://localhost:8000/api/ingest/imap")
            print(f"      Body: {{'email_address': '{email_address}', 'password': '***', 'max_emails': 50}}")
            print("\n   3. View in dashboard:")
            print("      http://localhost:8000/dashboard")
            
        else:
            print("\n⚠️  No emails found (inbox might be empty)")
        
        # Disconnect
        imap.disconnect()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   • Verify email and app password are correct")
        print("   • For Gmail: Enable IMAP in Gmail settings")
        print("   • For Outlook: Check account security settings")
        print("   • Check your internet connection")


if __name__ == "__main__":
    main()
