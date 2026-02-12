"""Triage agent orchestrating classification"""

from typing import Optional
from ..models import Email, EmailCategory
from .rule_classifier import RuleBasedClassifier


class TriageAgent:
    """Orchestrates email classification using rule-based approach"""
    
    def __init__(self, rule_classifier: Optional[RuleBasedClassifier] = None):
        self.rule_classifier = rule_classifier or RuleBasedClassifier()
    
    def classify_email(self, email: Email) -> Email:
        """
        Classify email using rule-based approach
        """
        # Rule-based classification
        category, confidence = self.rule_classifier.classify(email)
        
        email.category = category
        
        # Set detected intent based on category
        email.detected_intent = self._infer_intent(email)
        
        # Determine if response is required
        email.requires_response = self._requires_response(email)
        
        return email
    
    def _infer_intent(self, email: Email) -> Optional[str]:
        """Infer intent from email content"""
        text = (email.subject + " " + email.body_text).lower()
        
        if any(word in text for word in ['meeting', 'schedule', 'call', 'zoom', 'teams']):
            return 'schedule_meeting'
        elif '?' in text or 'question' in text:
            return 'request_info'
        elif any(word in text for word in ['unsubscribe', 'remove me', 'opt out']):
            return 'unsubscribe'
        elif any(word in text for word in ['update', 'status', 'progress']):
            return 'status_update'
        elif any(word in text for word in ['review', 'feedback', 'approve']):
            return 'review_request'
        
        return None
    
    def _requires_response(self, email: Email) -> bool:
        """Determine if email requires a response"""
        # Newsletters and promotional emails don't need responses
        if email.category in [EmailCategory.NEWSLETTER, EmailCategory.PROMOTIONAL, EmailCategory.SPAM]:
            return False
        
        text = email.body_text.lower()
        
        # Check for response-requesting phrases
        expecting_phrases = [
            'please let me know',
            'can you',
            'could you',
            'would you',
            'please confirm',
            'please review',
            'please send',
            'waiting for',
            'looking forward to hearing',
            'please respond',
            'please reply',
            'asap'
        ]
        
        # Questions indicate expecting response
        if '?' in email.body_text:
            return True
        
        return any(phrase in text for phrase in expecting_phrases)
