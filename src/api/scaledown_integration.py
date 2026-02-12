"""
ScaleDown AI API Integration Module
Connects to your custom ScaleDown AI API for enhanced email processing
"""

import requests
from typing import Dict, Any, Optional, List
from ..models import Email, EmailThread


class ScaleDownAPIClient:
    """Client for ScaleDown AI API integration"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.scaledown.ai/v1"):
        """
        Initialize ScaleDown AI API client
        
        Args:
            api_key: Your ScaleDown AI API key
            base_url: Base URL for the API (default: https://api.scaledown.ai/v1)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def compress_thread(self, thread: EmailThread) -> Dict[str, Any]:
        """
        Compress email thread using ScaleDown AI API
        
        Args:
            thread: EmailThread object to compress
            
        Returns:
            Dict with compressed summary and extracted information
        """
        # Prepare thread data for API
        thread_data = {
            "thread_id": thread.thread_id,
            "subject": thread.subject,
            "message_count": thread.message_count,
            "messages": [
                {
                    "id": msg.id,
                    "sender": msg.sender.email,
                    "timestamp": msg.received_at.isoformat(),
                    "content": msg.body_text
                }
                for msg in thread.messages
            ]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/compress/thread",
                json=thread_data,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"ScaleDown API Error: {e}")
            return {
                "error": str(e),
                "fallback": True
            }
    
    def classify_email(self, email: Email) -> Dict[str, Any]:
        """
        Classify email using ScaleDown AI API
        
        Args:
            email: Email object to classify
            
        Returns:
            Dict with classification results
        """
        email_data = {
            "email_id": email.id,
            "subject": email.subject,
            "sender": email.sender.email,
            "body": email.body_text,
            "received_at": email.received_at.isoformat()
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/classify/email",
                json=email_data,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"ScaleDown API Error: {e}")
            return {
                "error": str(e),
                "fallback": True
            }
    
    def extract_entities(self, text: str) -> List[str]:
        """
        Extract entities (people, dates, organizations) from text
        
        Args:
            text: Text to analyze
            
        Returns:
            List of extracted entities
        """
        try:
            response = requests.post(
                f"{self.base_url}/extract/entities",
                json={"text": text},
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            return result.get("entities", [])
        
        except requests.exceptions.RequestException as e:
            print(f"ScaleDown API Error: {e}")
            return []
    
    def generate_response(self, email: Email, context: Optional[str] = None) -> str:
        """
        Generate email response using ScaleDown AI API
        
        Args:
            email: Email to respond to
            context: Optional additional context
            
        Returns:
            Generated response text
        """
        request_data = {
            "email_id": email.id,
            "subject": email.subject,
            "sender": email.sender.email,
            "body": email.body_text,
            "context": context
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/generate/response",
                json=request_data,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        
        except requests.exceptions.RequestException as e:
            print(f"ScaleDown API Error: {e}")
            return ""
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of email text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with sentiment analysis results
        """
        try:
            response = requests.post(
                f"{self.base_url}/analyze/sentiment",
                json={"text": text},
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"ScaleDown API Error: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "error": str(e)
            }
    
    def batch_process(self, emails: List[Email]) -> List[Dict[str, Any]]:
        """
        Process multiple emails in batch for efficiency
        
        Args:
            emails: List of Email objects
            
        Returns:
            List of processing results
        """
        batch_data = {
            "emails": [
                {
                    "id": email.id,
                    "subject": email.subject,
                    "sender": email.sender.email,
                    "body": email.body_text[:500]  # Limit for batch processing
                }
                for email in emails
            ]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/batch/process",
                json=batch_data,
                headers=self.headers,
                timeout=60
            )
            response.raise_for_status()
            return response.json().get("results", [])
        
        except requests.exceptions.RequestException as e:
            print(f"ScaleDown API Error: {e}")
            return []
    
    def health_check(self) -> bool:
        """
        Check if ScaleDown AI API is available
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        
        except requests.exceptions.RequestException:
            return False


class HybridCompressor:
    """
    Hybrid compressor that uses both ScaleDown AI API and local processing
    Falls back to local if API is unavailable
    """
    
    def __init__(self, api_client: Optional[ScaleDownAPIClient] = None, 
                 local_compressor=None):
        self.api_client = api_client
        self.local_compressor = local_compressor
        self.use_api = api_client is not None and api_client.health_check()
    
    def compress_thread(self, thread: EmailThread) -> EmailThread:
        """
        Compress thread using API first, fall back to local if needed
        """
        if self.use_api and self.api_client:
            print("Using ScaleDown AI API for compression...")
            result = self.api_client.compress_thread(thread)
            
            if not result.get('fallback'):
                # Use API results
                thread.compressed_summary = result.get('summary', '')
                thread.key_decisions = result.get('decisions', [])
                thread.unresolved_questions = result.get('questions', [])
                thread.action_items_by_person = result.get('action_items', {})
                thread.original_token_count = result.get('original_tokens', 0)
                thread.compressed_token_count = result.get('compressed_tokens', 0)
                thread.compression_ratio = result.get('compression_ratio', 0)
                return thread
        
        # Fallback to local compression
        if self.local_compressor:
            print("Falling back to local compression...")
            return self.local_compressor.compress_thread(thread)
        
        return thread
