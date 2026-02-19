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
                 token_path: str = 'token.json',
                 credentials=None):
        """
        Initialize Gmail ingestor.

        Args:
            credentials_path: Path to OAuth credentials JSON file (legacy desktop flow).
            token_path:        Path to store/load token (legacy desktop flow).
            credentials:       A google.oauth2.credentials.Credentials object.
                               When provided, no file-based auth is performed – the
                               ingestor uses these credentials directly (web OAuth flow).
        """
        if not GMAIL_AVAILABLE:
            raise ImportError("Gmail libraries not installed")
        
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

        # If pre-built credentials were supplied, build the service immediately.
        if credentials is not None:
            self.service = build('gmail', 'v1', credentials=credentials)
    
    def authenticate(self) -> bool:
        """
        Authenticate via the legacy desktop OAuth flow (opens a browser window
        on the machine running the server).  Prefer the web OAuth flow when
        running as a server – use GmailIngestor(credentials=...) instead.
        
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
                    print("   3. Create OAuth credentials (Web Application)")
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

    @classmethod
    def from_stored_token(cls, token_data: dict) -> "GmailIngestor":
        """
        Create a GmailIngestor from a token dict previously saved by the web
        OAuth flow (stored in MongoDB).

        Args:
            token_data: Dict returned by gmail_auth.exchange_code_for_tokens()

        Returns:
            Authenticated GmailIngestor instance.
        """
        from .gmail_auth import credentials_from_dict
        creds = credentials_from_dict(token_data)
        if creds is None:
            raise ValueError("Could not reconstruct valid credentials from stored token.")
        return cls(credentials=creds)
    
    # Gmail system label IDs that correspond to the tab categories
    GMAIL_CATEGORY_LABELS = [
        'CATEGORY_PERSONAL',
        'CATEGORY_SOCIAL',
        'CATEGORY_PROMOTIONS',
        'CATEGORY_UPDATES',
        'CATEGORY_FORUMS',
    ]

    def _list_message_ids(self, label_ids: List[str], max_results: int, q: str = '') -> List[str]:
        """Return deduplicated message IDs matching the given labels/query."""
        results = self.service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=q,
            labelIds=label_ids
        ).execute()
        return [m['id'] for m in results.get('messages', [])]

    def fetch_emails(self, max_results: int = 50,
                     query: str = '',
                     label_ids: List[str] = None) -> List[Email]:
        """
        Fetch emails from Gmail, respecting Gmail's own category tabs.

        When label_ids is None (the default) we pull from every Gmail tab
        (Personal, Social, Promotions, Updates, Forums) plus Spam so that
        Gmail's categorisation is preserved rather than re-derived.

        Args:
            max_results: Maximum emails per category bucket.
            query: Extra Gmail search query string.
            label_ids: Override — fetch only from these label IDs.

        Returns:
            List of Email objects.
        """
        if not self.service:
            if not self.authenticate():
                return []

        try:
            if label_ids is not None:
                # Caller-specified labels — original behaviour
                id_list = self._list_message_ids(label_ids, max_results, query)
            else:
                # Fetch from every Gmail category tab + Spam so we honour
                # Gmail's own bucketing.  Use a set to avoid duplicates
                # (an email can carry multiple labels, e.g. INBOX + CATEGORY_UPDATES).
                buckets = [
                    ['CATEGORY_PERSONAL'],
                    ['CATEGORY_SOCIAL'],
                    ['CATEGORY_PROMOTIONS'],
                    ['CATEGORY_UPDATES'],
                    ['CATEGORY_FORUMS'],
                    ['SPAM'],
                    # Catch anything in inbox not covered by a category tab
                    ['INBOX'],
                ]
                seen_ids: set = set()
                id_list: List[str] = []
                per_bucket = max(10, max_results // len(buckets))
                for bucket_labels in buckets:
                    for mid in self._list_message_ids(bucket_labels, per_bucket, query):
                        if mid not in seen_ids:
                            seen_ids.add(mid)
                            id_list.append(mid)

            if not id_list:
                print('No messages found.')
                return []

            emails = []
            for mid in id_list:
                email = self._fetch_email_details(mid)
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
            body_text, body_html = self._get_email_body(message['payload'])
            
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
                body_html=body_html,
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
    
    def _get_email_body(self, payload: dict) -> tuple[str, str]:
        """Extract email body text and HTML from payload"""
        body_text = ''
        body_html = ''
        
        # Check for direct body
        if 'body' in payload and payload['body'].get('data'):
            decoded = base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8', errors='ignore')
            
            if payload.get('mimeType') == 'text/html':
                body_html = decoded
                body_text = re.sub('<[^<]+?>', '', body_html)
            else:
                body_text = decoded
        
        # Check for parts (multipart)
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if part['body'].get('data'):
                        body_text += base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html':
                    if part['body'].get('data'):
                        body_html += base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8', errors='ignore')
        
        # If we have HTML but no text, create text from HTML
        if body_html and not body_text:
            body_text = re.sub('<[^<]+?>', '', body_html)
            
        return body_text.strip(), body_html.strip()
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date from email header"""
        try:
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()
    
    def _guess_category_from_labels(self, labels: List[str]) -> Optional[EmailCategory]:
        """
        Map Gmail system label IDs to our EmailCategory.

        Priority order: Spam > tab categories > Starred > None.
        Returning None means "let the AI classifier decide" — process-inbox
        will only re-classify emails whose category is None.
        """
        s = set(labels)  # Gmail label IDs are already uppercase strings

        if 'SPAM' in s:
            return EmailCategory.SPAM
        if 'CATEGORY_PROMOTIONS' in s:
            return EmailCategory.PROMOTIONAL
        if 'CATEGORY_SOCIAL' in s:
            return EmailCategory.SOCIAL
        if 'CATEGORY_UPDATES' in s:
            # Updates tab = receipts, notifications, newsletters
            return EmailCategory.NEWSLETTER
        if 'CATEGORY_FORUMS' in s:
            return EmailCategory.NEWSLETTER
        if 'CATEGORY_PERSONAL' in s:
            return EmailCategory.PERSONAL
        if 'STARRED' in s:
            return EmailCategory.URGENT
        # INBOX with no category tab → let our classifier decide
        return None
    
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
