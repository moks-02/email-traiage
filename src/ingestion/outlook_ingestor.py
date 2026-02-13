"""
Outlook/Office 365 Email Ingestor
Connects to Microsoft Graph API to fetch real emails
"""

import requests
from typing import List, Optional
from datetime import datetime

try:
    from msal import PublicClientApplication, ConfidentialClientApplication
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False
    print("⚠️ Microsoft authentication library not installed. Run: pip install msal")

from ..models import Email, EmailAddress, EmailCategory


class OutlookIngestor:
    """Ingests emails from Outlook/Office 365"""
    
    # Microsoft Graph API endpoints
    GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
    AUTHORITY = 'https://login.microsoftonline.com/common'
    
    # Required scopes
    SCOPES = ['Mail.Read', 'Mail.ReadWrite', 'User.Read']
    
    def __init__(self, client_id: str, client_secret: Optional[str] = None):
        """
        Initialize Outlook ingestor
        
        Args:
            client_id: Azure AD application (client) ID
            client_secret: Client secret (for confidential apps)
        """
        if not MSAL_AVAILABLE:
            raise ImportError("Microsoft authentication library not installed")
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        
        # Initialize MSAL app
        if client_secret:
            # Confidential client (server app)
            self.app = ConfidentialClientApplication(
                client_id,
                authority=self.AUTHORITY,
                client_credential=client_secret
            )
        else:
            # Public client (desktop app)
            self.app = PublicClientApplication(
                client_id,
                authority=self.AUTHORITY
            )
    
    def authenticate(self) -> bool:
        """
        Authenticate with Microsoft Graph API
        
        Returns:
            True if authentication successful
        """
        # Try to get token from cache
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(self.SCOPES, account=accounts[0])
            if result and 'access_token' in result:
                self.access_token = result['access_token']
                return True
        
        # Interactive authentication
        result = self.app.acquire_token_interactive(scopes=self.SCOPES)
        
        if 'access_token' in result:
            self.access_token = result['access_token']
            print("✅ Successfully authenticated with Microsoft")
            return True
        else:
            error = result.get('error')
            error_desc = result.get('error_description')
            print(f"❌ Authentication failed: {error} - {error_desc}")
            print("\n📋 Setup instructions:")
            print("   1. Go to https://portal.azure.com/")
            print("   2. Register an application in Azure AD")
            print("   3. Add Mail.Read permissions")
            print("   4. Copy the Application (client) ID")
            return False
    
    def fetch_emails(self, max_results: int = 50,
                     folder: str = 'inbox',
                     filter_query: Optional[str] = None) -> List[Email]:
        """
        Fetch emails from Outlook
        
        Args:
            max_results: Maximum number of emails to fetch
            folder: Folder name ('inbox', 'sent', 'drafts', etc.)
            filter_query: OData filter query
        
        Returns:
            List of Email objects
        """
        if not self.access_token:
            if not self.authenticate():
                return []
        
        # Build URL
        url = f"{self.GRAPH_API_ENDPOINT}/me/mailFolders/{folder}/messages"
        
        # Add query parameters
        params = {
            '$top': max_results,
            '$orderby': 'receivedDateTime DESC'
        }
        
        if filter_query:
            params['$filter'] = filter_query
        
        # Set headers
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            messages = data.get('value', [])
            
            if not messages:
                print('No messages found.')
                return []
            
            emails = []
            for msg in messages:
                email = self._parse_outlook_message(msg)
                if email:
                    emails.append(email)
            
            print(f"✅ Fetched {len(emails)} emails from Outlook")
            return emails
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Outlook emails: {e}")
            return []
    
    def _parse_outlook_message(self, message: dict) -> Optional[Email]:
        """Parse Outlook message to Email object"""
        try:
            # Parse sender
            from_data = message.get('from', {}).get('emailAddress', {})
            sender = EmailAddress(
                name=from_data.get('name', ''),
                email=from_data.get('address', '')
            )
            
            # Parse recipients
            to_recipients = message.get('toRecipients', [])
            recipients = [
                EmailAddress(
                    name=r.get('emailAddress', {}).get('name', ''),
                    email=r.get('emailAddress', {}).get('address', '')
                )
                for r in to_recipients
            ]
            
            # Get other fields
            subject = message.get('subject', '(No Subject)')
            body_text = message.get('body', {}).get('content', '')
            
            # Strip HTML if needed
            if message.get('body', {}).get('contentType') == 'html':
                import re
                body_text = re.sub('<[^<]+?>', '', body_text)
            
            # Parse date
            received_str = message.get('receivedDateTime', '')
            received_at = datetime.fromisoformat(received_str.replace('Z', '+00:00'))
            
            # Get thread/conversation ID
            thread_id = message.get('conversationId', '')
            
            # Get categories/importance for initial categorization
            importance = message.get('importance', '').lower()
            categories = message.get('categories', [])
            is_read = message.get('isRead', False)
            
            # Create Email object
            email = Email(
                id=message.get('id', ''),
                thread_id=thread_id,
                subject=subject,
                sender=sender,
                recipients=recipients,
                body_text=body_text.strip(),
                received_at=received_at,
                category=self._guess_category_from_metadata(
                    importance, categories, is_read
                )
            )
            
            return email
        
        except Exception as e:
            print(f"Error parsing message: {e}")
            return None
    
    def _guess_category_from_metadata(self, importance: str, 
                                     categories: List[str],
                                     is_read: bool) -> EmailCategory:
        """Make initial category guess from Outlook metadata"""
        if importance == 'high':
            return EmailCategory.URGENT
        
        categories_lower = [c.lower() for c in categories]
        if 'newsletter' in categories_lower:
            return EmailCategory.NEWSLETTER
        elif 'promotional' in categories_lower or 'marketing' in categories_lower:
            return EmailCategory.PROMOTIONAL
        elif 'social' in categories_lower:
            return EmailCategory.SOCIAL
        elif 'personal' in categories_lower:
            return EmailCategory.PERSONAL
        
        return EmailCategory.WORK
    
    def fetch_unread_emails(self, max_results: int = 50) -> List[Email]:
        """Fetch only unread emails"""
        return self.fetch_emails(
            max_results=max_results,
            filter_query='isRead eq false'
        )
    
    def fetch_important_emails(self, max_results: int = 50) -> List[Email]:
        """Fetch important/flagged emails"""
        return self.fetch_emails(
            max_results=max_results,
            filter_query="importance eq 'high'"
        )
    
    def fetch_today_emails(self, max_results: int = 100) -> List[Email]:
        """Fetch today's emails"""
        today = datetime.now().date().isoformat()
        return self.fetch_emails(
            max_results=max_results,
            filter_query=f"receivedDateTime ge {today}T00:00:00Z"
        )
    
    def fetch_emails_by_sender(self, sender_email: str, 
                              max_results: int = 50) -> List[Email]:
        """Fetch emails from specific sender"""
        return self.fetch_emails(
            max_results=max_results,
            filter_query=f"from/emailAddress/address eq '{sender_email}'"
        )
