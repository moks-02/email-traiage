"""
Gmail Email Ingestor
Connects to Gmail API to fetch real emails
"""

import base64
import re
from typing import List, Optional
from datetime import datetime
from email.utils import parsedate_to_datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("⚠️ Gmail libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

from ..models import Email, EmailAddress, EmailCategory


class GmailIngestor:
    """Ingests emails from Gmail"""
    
    # Gmail API scopes
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, credentials_path: str = 'credentials.json', 
                 token_path: str = 'token.json'):
        """
        Initialize Gmail ingestor
        
        Args:
            credentials_path: Path to OAuth credentials file
            token_path: Path to store/load token
        """
        if not GMAIL_AVAILABLE:
            raise ImportError("Gmail libraries not installed")
        
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API
        
        Returns:
            True if authentication successful
        """
        creds = None
        
        # Load existing token
        try:
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        except Exception as e:
            print(f"Error loading token: {e}")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    print(f"❌ Credentials file not found: {self.credentials_path}")
                    print("📋 Setup instructions:")
                    print("   1. Go to https://console.cloud.google.com/")
                    print("   2. Create a project and enable Gmail API")
                    print("   3. Create OAuth credentials (Desktop app)")
                    print("   4. Download as credentials.json")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        # Build service
        self.service = build('gmail', 'v1', credentials=creds)
        return True
    
    def fetch_emails(self, max_results: int = 50, 
                     query: str = '',
                     label_ids: List[str] = None) -> List[Email]:
        """
        Fetch emails from Gmail
        
        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query (e.g., 'is:unread', 'from:boss@company.com')
            label_ids: Filter by label IDs (e.g., ['INBOX', 'UNREAD'])
        
        Returns:
            List of Email objects
        """
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            # List messages
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query,
                labelIds=label_ids or ['INBOX']
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                print('No messages found.')
                return []
            
            emails = []
            for msg in messages:
                email = self._fetch_email_details(msg['id'])
                if email:
                    emails.append(email)
            
            print(f"✅ Fetched {len(emails)} emails from Gmail")
            return emails
        
        except HttpError as error:
            print(f'Gmail API error: {error}')
            return []
    
    def _fetch_email_details(self, message_id: str) -> Optional[Email]:
        """Fetch full details of a single email"""
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {h['name']: h['value'] 
                      for h in message['payload']['headers']}
            
            # Parse sender
            sender_str = headers.get('From', '')
            sender = self._parse_email_address(sender_str)
            
            # Parse recipients
            to_str = headers.get('To', '')
            recipients = [self._parse_email_address(addr) 
                         for addr in to_str.split(',') if addr]
            
            # Get subject
            subject = headers.get('Subject', '(No Subject)')
            
            # Get body
            body_text = self._get_email_body(message['payload'])
            
            # Get date
            date_str = headers.get('Date', '')
            received_at = self._parse_date(date_str)
            
            # Get thread ID
            thread_id = message.get('threadId', '')
            
            # Get labels (for initial categorization hint)
            labels = message.get('labelIds', [])
            
            # Create Email object
            email = Email(
                id=message_id,
                thread_id=thread_id,
                subject=subject,
                sender=sender,
                recipients=recipients,
                body_text=body_text,
                received_at=received_at,
                category=self._guess_category_from_labels(labels)
            )
            
            return email
        
        except HttpError as error:
            print(f'Error fetching message {message_id}: {error}')
            return None
    
    def _parse_email_address(self, addr_str: str) -> EmailAddress:
        """Parse email address from string like 'Name <email@example.com>'"""
        match = re.match(r'(.+?)\s*<(.+?)>', addr_str.strip())
        if match:
            name, email = match.groups()
            return EmailAddress(name=name.strip('"'), email=email.strip())
        else:
            # Just email address
            return EmailAddress(name='', email=addr_str.strip())
    
    def _get_email_body(self, payload: dict) -> str:
        """Extract email body from payload"""
        body_text = ''
        
        # Check for direct body
        if 'body' in payload and payload['body'].get('data'):
            body_text = base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8', errors='ignore')
        
        # Check for parts (multipart)
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if part['body'].get('data'):
                        body_text += base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html' and not body_text:
                    # Fallback to HTML if no plain text
                    if part['body'].get('data'):
                        html = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8', errors='ignore')
                        # Strip HTML tags (basic)
                        body_text = re.sub('<[^<]+?>', '', html)
        
        return body_text.strip()
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date from email header"""
        try:
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()
    
    def _guess_category_from_labels(self, labels: List[str]) -> EmailCategory:
        """Make initial category guess from Gmail labels"""
        labels_lower = [l.lower() for l in labels]
        
        if 'important' in labels_lower or 'starred' in labels_lower:
            return EmailCategory.URGENT
        elif 'category_promotions' in labels_lower:
            return EmailCategory.PROMOTIONAL
        elif 'category_social' in labels_lower:
            return EmailCategory.SOCIAL
        elif 'spam' in labels_lower:
            return EmailCategory.SPAM
        else:
            return EmailCategory.WORK
    
    def fetch_unread_emails(self, max_results: int = 50) -> List[Email]:
        """Fetch only unread emails"""
        return self.fetch_emails(
            max_results=max_results,
            label_ids=['INBOX', 'UNREAD']
        )
    
    def fetch_emails_by_sender(self, sender_email: str, 
                               max_results: int = 50) -> List[Email]:
        """Fetch emails from specific sender"""
        return self.fetch_emails(
            max_results=max_results,
            query=f'from:{sender_email}'
        )
    
    def fetch_today_emails(self, max_results: int = 100) -> List[Email]:
        """Fetch today's emails"""
        return self.fetch_emails(
            max_results=max_results,
            query='newer_than:1d'
        )


import os
