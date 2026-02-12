"""Multi-factor priority scoring system"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict
from dateutil import parser

from ..models import Email, EmailThread, EmailCategory, Priority


class PriorityScorer:
    """
    Calculate email priority using weighted factors:
    - Sender importance (0-30 points)
    - Keywords urgency (0-25 points)  
    - Deadline proximity (0-25 points)
    - Thread context (0-10 points)
    - Recency (0-10 points)
    
    Total: 0-100 scale
    """
    
    def __init__(self):
        # Configurable weights
        self.weights = {
            'sender_importance': 0.30,
            'keyword_urgency': 0.25,
            'deadline_proximity': 0.25,
            'thread_context': 0.10,
            'recency': 0.10
        }
        
        # Sender VIP list (email -> importance score)
        self.vip_senders: Dict[str, float] = {}
        
        # Work domains for scoring
        self.work_domains = {'company.com', 'organization.org'}
        
        # Urgent keywords with weights
        self.urgent_keywords = {
            'critical': 10,
            'urgent': 10,
            'asap': 9,
            'immediate': 9,
            'emergency': 10,
            'deadline': 8,
            'today': 7,
            'now': 7,
            'important': 6,
            'please review': 5,
            'action required': 8,
            'time sensitive': 8
        }
    
    def calculate_priority(self, email: Email, thread: Optional[EmailThread] = None) -> float:
        """
        Calculate priority score (0-100)
        """
        scores = {
            'sender': self._score_sender_importance(email),
            'keywords': self._score_keyword_urgency(email),
            'deadline': self._score_deadline_proximity(email),
            'thread': self._score_thread_context(email, thread),
            'recency': self._score_recency(email)
        }
        
        # Weighted sum
        total_score = (
            scores['sender'] * self.weights['sender_importance'] +
            scores['keywords'] * self.weights['keyword_urgency'] +
            scores['deadline'] * self.weights['deadline_proximity'] +
            scores['thread'] * self.weights['thread_context'] +
            scores['recency'] * self.weights['recency']
        )
        
        # Boost for explicit urgency flags
        if email.category == EmailCategory.URGENT:
            total_score = min(total_score * 1.2, 100)
        
        return round(total_score, 2)
    
    def _score_sender_importance(self, email: Email) -> float:
        """Score based on sender (0-100)"""
        sender_email = email.sender.email.lower()
        
        # Check VIP list
        if sender_email in self.vip_senders:
            return self.vip_senders[sender_email]
        
        # Domain-based scoring
        domain = email.sender.domain
        
        # Internal company emails
        if domain in self.work_domains:
            return 60
        
        # External but known contacts
        return 40
    
    def _score_keyword_urgency(self, email: Email) -> float:
        """Score based on urgent keywords (0-100)"""
        text = (email.subject + " " + email.body_text).lower()
        
        max_score = 0
        for keyword, score in self.urgent_keywords.items():
            if keyword in text:
                max_score = max(max_score, score)
        
        # Normalize to 0-100
        return max_score * 10
    
    def _score_deadline_proximity(self, email: Email) -> float:
        """Score based on deadline proximity (0-100)"""
        # Extract deadline from email
        deadline = self._extract_deadline(email)
        
        if not deadline:
            return 30  # Default moderate score
        
        time_until_deadline = (deadline - datetime.now()).total_seconds() / 3600  # hours
        
        if time_until_deadline < 0:
            return 100  # Past deadline - critical
        elif time_until_deadline < 4:
            return 95  # < 4 hours
        elif time_until_deadline < 24:
            return 80  # < 1 day
        elif time_until_deadline < 48:
            return 60  # < 2 days
        elif time_until_deadline < 168:
            return 40  # < 1 week
        else:
            return 20  # > 1 week
    
    def _score_thread_context(self, email: Email, thread: Optional[EmailThread]) -> float:
        """Score based on thread activity (0-100)"""
        if not thread or thread.message_count <= 1:
            return 50  # New thread, moderate importance
        
        # Active threads (many messages) are higher priority
        activity_score = min(thread.message_count * 2, 50)
        
        # Recent activity boost
        if thread.last_message_at:
            hours_since_last = (datetime.now() - thread.last_message_at).total_seconds() / 3600
            if hours_since_last < 2:
                activity_score += 30
            elif hours_since_last < 24:
                activity_score += 20
        
        return min(activity_score, 100)
    
    def _score_recency(self, email: Email) -> float:
        """Score based on how recent the email is (0-100)"""
        age_hours = (datetime.now() - email.received_at).total_seconds() / 3600
        
        if age_hours < 1:
            return 100
        elif age_hours < 4:
            return 80
        elif age_hours < 24:
            return 60
        elif age_hours < 72:
            return 40
        else:
            return 20
    
    def _extract_deadline(self, email: Email) -> Optional[datetime]:
        """Extract deadline from email text using pattern matching"""
        text = email.subject + " " + email.body_text
        
        # Pattern matching for common deadline phrases
        patterns = [
            r'deadline:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'due:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'by\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?)',
            r'before\s+(\d{1,2}:\d{2}\s*[ap]m)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return parser.parse(match.group(1))
                except Exception:
                    pass
        
        return None
    
    def assign_priority_level(self, score: float) -> Priority:
        """Convert score to priority level"""
        if score >= 85:
            return Priority.CRITICAL
        elif score >= 70:
            return Priority.HIGH
        elif score >= 50:
            return Priority.MEDIUM
        elif score >= 30:
            return Priority.LOW
        else:
            return Priority.MINIMAL
    
    def add_vip_sender(self, email: str, importance: float):
        """Add VIP sender with importance score (0-100)"""
        self.vip_senders[email.lower()] = importance
    
    def add_work_domain(self, domain: str):
        """Add work domain"""
        self.work_domains.add(domain.lower())
