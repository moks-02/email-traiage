"""Rule-based email classification"""

import re
from typing import Tuple, Set
from ..models import Email, EmailCategory


class RuleBasedClassifier:
    """Fast, deterministic email classification using rules"""
    
    def __init__(self):
        self.rules = {
            EmailCategory.SPAM: [
                lambda e: any(word in e.subject.lower() for word in 
                    ['viagra', 'casino', 'lottery', 'prince', 'inheritance', 'bitcoin wallet']),
                lambda e: e.sender.domain in ['suspicious.com', 'spam-domain.net']
            ],
            EmailCategory.NEWSLETTER: [
                lambda e: any(word in e.subject.lower() for word in 
                    ['newsletter', 'digest', 'weekly update', 'monthly summary']),
                lambda e: 'unsubscribe' in e.body_text.lower(),
                lambda e: e.sender.name and 'noreply' in e.sender.email.lower()
            ],
            EmailCategory.PROMOTIONAL: [
                lambda e: any(word in e.subject.lower() for word in 
                    ['sale', 'discount', 'offer', 'deal', 'promo', '% off', '50%']),
                lambda e: re.search(r'\d+%\s+off', e.body_text, re.IGNORECASE) is not None,
                lambda e: any(emoji in e.subject for emoji in ['🎉', '💰', '🛍️'])
            ],
            EmailCategory.URGENT: [
                lambda e: any(word in e.subject.lower() for word in 
                    ['urgent', 'asap', 'immediate', 'critical', 'emergency']),
                lambda e: '!!!' in e.subject or '!!!' in e.body_text,
                lambda e: 'URGENT' in e.subject or 'IMMEDIATE ACTION' in e.subject
            ],
            EmailCategory.SOCIAL: [
                lambda e: e.sender.domain in ['facebook.com', 'twitter.com', 'linkedin.com', 
                                               'instagram.com', 'tiktok.com'],
                lambda e: any(phrase in e.subject.lower() for phrase in 
                    ['tagged you', 'mentioned you', 'sent you a message', 'friend request'])
            ]
        }
        
        # Domain-based classification (user-configurable)
        self.work_domains: Set[str] = set()
        self.personal_contacts: Set[str] = set()
    
    def classify(self, email: Email) -> Tuple[EmailCategory, float]:
        """
        Returns (category, confidence)
        Confidence: 0.0 to 1.0
        """
        # Check rules in priority order
        for category, rule_list in self.rules.items():
            matches = sum(1 for rule in rule_list if self._safe_eval(rule, email))
            if matches > 0:
                confidence = min(matches / len(rule_list), 1.0)
                return category, confidence
        
        # Domain-based work/personal classification
        if email.sender.domain in self.work_domains:
            return EmailCategory.WORK, 0.8
        
        if email.sender.email in self.personal_contacts:
            return EmailCategory.PERSONAL, 0.8
        
        # Default to work if uncertain
        return EmailCategory.WORK, 0.3
    
    def _safe_eval(self, rule_func, email: Email) -> bool:
        """Safely evaluate rule function"""
        try:
            return rule_func(email)
        except Exception:
            return False
    
    def add_work_domain(self, domain: str):
        """Configure work domain for classification"""
        self.work_domains.add(domain.lower())
    
    def add_personal_contact(self, email: str):
        """Add personal contact"""
        self.personal_contacts.add(email.lower())
    
    def configure_from_dict(self, config: dict):
        """Configure classifier from dictionary"""
        if 'work_domains' in config:
            for domain in config['work_domains']:
                self.add_work_domain(domain)
        
        if 'personal_contacts' in config:
            for contact in config['personal_contacts']:
                self.add_personal_contact(contact)
