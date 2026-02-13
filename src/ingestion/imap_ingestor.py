"""
IMAP Email Ingestor
Universal email integration - works with Gmail, Outlook, Yahoo, and any IMAP server
No OAuth setup required - just email and password/app password
"""

import imaplib
import email
from email.header import decode_header
from typing import List, Optional
from datetime import datetime
import re

from ..models import Email, EmailAddress, EmailCategory


class IMAPIngestor:
    """
    Universal IMAP email ingestor
    Works with any IMAP-enabled email provider
    """
    
    # Common IMAP server configurations
    PROVIDERS = {
        'gmail': {
            'server': 'imap.gmail.com',
            'port': 993,
            'ssl': True,
            'note': 'Use App Password from Google Account settings'
        },
        'outlook': {
            'server': 'outlook.office365.com',
            'port': 993,
            'ssl': True,
            'note': 'Regular password or App Password'
        },
        'yahoo': {
            'server': 'imap.mail.yahoo.com',
            'port': 993,
            'ssl': True,
            'note': 'Use App Password from Yahoo Account security'
        },
        'icloud': {
            'server': 'imap.mail.me.com',
            'port': 993,
            'ssl': True,
            'note': 'Use App-Specific Password'
        },
        'aol': {
            'server': 'imap.aol.com',
            'port': 993,
            'ssl': True
        }
    }
    
    def __init__(self, email_address: str, password: str, 
                 provider: str = None, server: str = None, port: int = 993):
        """
        Initialize IMAP ingestor
        
        Args:
            email_address: Your email address
            password: Your password or app password
            provider: Provider name ('gmail', 'outlook', 'yahoo', 'icloud', 'aol')
            server: Custom IMAP server (if provider not in list)
            port: IMAP port (default: 993 for SSL)
        """
        self.email_address = email_address
        self.password = password
        self.mail = None
        
        # Auto-detect provider from email if not specified
        if not provider and not server:
            domain = email_address.split('@')[1].lower()
            if 'gmail' in domain:
                provider = 'gmail'
            elif 'outlook' in domain or 'hotmail' in domain or 'live' in domain:
                provider = 'outlook'
            elif 'yahoo' in domain:
                provider = 'yahoo'
            elif 'icloud' in domain or 'me.com' in domain:
                provider = 'icloud'
            elif 'aol' in domain:
                provider = 'aol'
        
        # Set server configuration
        if provider and provider.lower() in self.PROVIDERS:
            config = self.PROVIDERS[provider.lower()]
            self.server = config['server']
            self.port = config['port']
            print(f"📧 Using {provider.title()} configuration")
            if 'note' in config:
                print(f"   Note: {config['note']}")
        elif server:
            self.server = server
            self.port = port
            print(f"📧 Using custom IMAP server: {server}:{port}")
        else:
            raise ValueError("Must specify either provider or server")
    
    def connect(self) -> bool:
        """
        Connect to IMAP server
        
        Returns:
            True if connection successful
        """
        try:
            print(f"🔐 Connecting to {self.server}...")
            self.mail = imaplib.IMAP4_SSL(self.server, self.port)
            self.mail.login(self.email_address, self.password)
            print("✅ Successfully connected and authenticated")
            return True
        
        except imaplib.IMAP4.error as e:
            print(f"❌ IMAP authentication failed: {e}")
            print("\n💡 Tips:")
            print("   • For Gmail: Enable 2FA and create App Password")
            print("   • For Outlook: Use regular password or App Password")
            print("   • For Yahoo: Create App Password in Account Security")
            return False
        
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def fetch_emails(self, folder: str = 'INBOX', 
                     max_results: int = 50,
                     unread_only: bool = False,
                     since_date: Optional[str] = None) -> List[Email]:
        """
        Fetch emails from specified folder
        
        Args:
            folder: Folder name ('INBOX', 'Sent', 'Drafts', etc.)
            max_results: Maximum number of emails to fetch
            unread_only: Only fetch unread emails
            since_date: Fetch emails since date (format: 'DD-Mon-YYYY' e.g. '01-Jan-2024')
        
        Returns:
            List of Email objects
        """
        if not self.mail:
            if not self.connect():
                return []
        
        try:
            # Select folder
            self.mail.select(folder, readonly=True)
            
            # Build search criteria
            criteria = []
            if unread_only:
                criteria.append('UNSEEN')
            if since_date:
                criteria.append(f'SINCE {since_date}')
            
            search_query = ' '.join(criteria) if criteria else 'ALL'
            
            # Search for emails
            _, message_numbers = self.mail.search(None, search_query)
            email_ids = message_numbers[0].split()
            
            if not email_ids:
                print(f"No emails found in {folder}")
                return []
            
            # Limit results
            email_ids = email_ids[-max_results:]  # Get most recent
            
            print(f"📧 Found {len(email_ids)} emails, fetching...")
            
            emails = []
            for i, email_id in enumerate(email_ids, 1):
                email_obj = self._fetch_email_details(email_id)
                if email_obj:
                    emails.append(email_obj)
                
                # Progress indicator
                if i % 10 == 0:
                    print(f"   Processed {i}/{len(email_ids)} emails...")
            
            print(f"✅ Successfully fetched {len(emails)} emails")
            return emails
        
        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return []
    
    def _fetch_email_details(self, email_id: bytes) -> Optional[Email]:
        """Fetch full details of a single email"""
        try:
            # Fetch email
            _, msg_data = self.mail.fetch(email_id, '(RFC822)')
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Parse subject
            subject = self._decode_header(email_message.get('Subject', ''))
            
            # Parse sender
            from_str = email_message.get('From', '')
            sender = self._parse_email_address(from_str)
            
            # Parse recipients
            to_str = email_message.get('To', '')
            recipients = [self._parse_email_address(addr) 
                         for addr in to_str.split(',') if addr]
            
            # Parse date
            date_str = email_message.get('Date', '')
            received_at = self._parse_date(date_str)
            
            # Get message ID for threading
            message_id = email_message.get('Message-ID', email_id.decode())
            in_reply_to = email_message.get('In-Reply-To', '')
            thread_id = in_reply_to if in_reply_to else message_id
            
            # Extract body
            body_text = self._get_email_body(email_message)
            
            # Create Email object
            return Email(
                id=message_id,
                thread_id=thread_id,
                subject=subject,
                sender=sender,
                recipients=recipients,
                body_text=body_text,
                received_at=received_at,
                category=EmailCategory.WORK  # Will be classified later
            )
        
        except Exception as e:
            print(f"   ⚠️  Error parsing email {email_id}: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header (handles encoded subjects)"""
        if not header:
            return '(No Subject)'
        
        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
                except:
                    decoded_parts.append(part.decode('utf-8', errors='ignore'))
            else:
                decoded_parts.append(str(part))
        
        return ''.join(decoded_parts)
    
    def _parse_email_address(self, addr_str: str) -> EmailAddress:
        """Parse email address from string"""
        # Pattern: "Name" <email@example.com> or Name <email@example.com> or just email@example.com
        match = re.search(r'([^<]*)<([^>]+)>', addr_str)
        if match:
            name = match.group(1).strip(' "')
            email_addr = match.group(2).strip()
            return EmailAddress(name=name, email=email_addr)
        else:
            # Just email address
            return EmailAddress(name='', email=addr_str.strip())
    
    def _get_email_body(self, email_message) -> str:
        """Extract email body text"""
        body_text = ''
        
        if email_message.is_multipart():
            # Multipart email
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Skip attachments
                if 'attachment' in content_disposition:
                    continue
                
                try:
                    part_body = part.get_payload(decode=True)
                    if part_body:
                        if content_type == 'text/plain':
                            body_text += part_body.decode('utf-8', errors='ignore')
                        elif content_type == 'text/html' and not body_text:
                            # Fallback to HTML if no plain text
                            html = part_body.decode('utf-8', errors='ignore')
                            # Basic HTML stripping
                            body_text = re.sub('<[^<]+?>', '', html)
                except Exception as e:
                    pass
        else:
            # Single part email
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    body_text = payload.decode('utf-8', errors='ignore')
            except:
                body_text = str(email_message.get_payload())
        
        return body_text.strip()
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date from email header"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()
    
    def fetch_unread_emails(self, max_results: int = 50) -> List[Email]:
        """Fetch only unread emails"""
        return self.fetch_emails(
            folder='INBOX',
            max_results=max_results,
            unread_only=True
        )
    
    def fetch_sent_emails(self, max_results: int = 50) -> List[Email]:
        """Fetch sent emails"""
        # Try common sent folder names
        sent_folders = ['Sent', '[Gmail]/Sent Mail', 'Sent Items', 'Sent Messages']
        
        for folder in sent_folders:
            try:
                return self.fetch_emails(folder=folder, max_results=max_results)
            except:
                continue
        
        print("⚠️  Could not find sent folder")
        return []
    
    def list_folders(self) -> List[str]:
        """List all available folders"""
        if not self.mail:
            if not self.connect():
                return []
        
        try:
            _, folders = self.mail.list()
            folder_names = []
            for folder in folders:
                # Parse folder name from IMAP response
                parts = folder.decode().split('"')
                if len(parts) >= 3:
                    folder_names.append(parts[-2])
            return folder_names
        except Exception as e:
            print(f"❌ Error listing folders: {e}")
            return []
    
    def disconnect(self):
        """Close IMAP connection"""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                print("✅ Disconnected from IMAP server")
            except:
                pass
    
    def __del__(self):
        """Cleanup on deletion"""
        self.disconnect()


def get_provider_help():
    """Display help for setting up different email providers"""
    print("\n" + "="*70)
    print("  Email Provider Setup Guide")
    print("="*70)
    
    print("\n📧 GMAIL")
    print("   1. Go to: https://myaccount.google.com/security")
    print("   2. Enable 2-Step Verification")
    print("   3. Go to 'App passwords'")
    print("   4. Generate password for 'Mail'")
    print("   5. Use: email=your@gmail.com, password=<app-password>")
    
    print("\n📨 OUTLOOK / HOTMAIL / LIVE")
    print("   1. Go to: https://account.microsoft.com/security")
    print("   2. Click 'Advanced security options'")
    print("   3. Enable 'App passwords'")
    print("   4. Generate new app password")
    print("   5. Use: email=your@outlook.com, password=<app-password>")
    
    print("\n📬 YAHOO")
    print("   1. Go to: https://login.yahoo.com/account/security")
    print("   2. Click 'Generate app password'")
    print("   3. Select 'Other App'")
    print("   4. Name it 'Email Triage'")
    print("   5. Use: email=your@yahoo.com, password=<app-password>")
    
    print("\n☁️  ICLOUD")
    print("   1. Go to: https://appleid.apple.com/account/manage")
    print("   2. Under Security, generate App-Specific Password")
    print("   3. Use: email=your@icloud.com, password=<app-password>")
    
    print("\n🔧 CUSTOM / WORK EMAIL")
    print("   Contact your IT department for:")
    print("   • IMAP server address (e.g., mail.yourcompany.com)")
    print("   • IMAP port (usually 993 for SSL)")
    print("   • Your email and password")
    print("\n")
