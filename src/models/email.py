"""Email data models"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class EmailCategory(Enum):
    URGENT = "urgent"
    WORK = "work"
    PERSONAL = "personal"
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    SPAM = "spam"
    SOCIAL = "social"


class Priority(Enum):
    CRITICAL = 5  # Respond within 1 hour
    HIGH = 4      # Respond same day
    MEDIUM = 3    # Respond within 2 days
    LOW = 2       # Respond within a week
    MINIMAL = 1   # No response needed


@dataclass
class EmailAddress:
    email: str
    name: Optional[str] = None
    domain: Optional[str] = None
    
    def __post_init__(self):
        if not self.domain and '@' in self.email:
            self.domain = self.email.split('@')[1]
    
    def to_dict(self):
        return {
            'email': self.email,
            'name': self.name,
            'domain': self.domain
        }


@dataclass
class Attachment:
    filename: str
    content_type: str
    size_bytes: int
    attachment_id: str
    
    def to_dict(self):
        return {
            'filename': self.filename,
            'content_type': self.content_type,
            'size_bytes': self.size_bytes,
            'attachment_id': self.attachment_id
        }


@dataclass
class Email:
    """Core email message model"""
    id: str
    thread_id: str
    subject: str
    sender: EmailAddress
    recipients: List[EmailAddress]
    cc: List[EmailAddress] = field(default_factory=list)
    bcc: List[EmailAddress] = field(default_factory=list)
    body_text: str = ""
    body_html: str = ""
    received_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    
    # Extracted metadata
    attachments: List[Attachment] = field(default_factory=list)
    in_reply_to: Optional[str] = None
    references: List[str] = field(default_factory=list)
    
    # Classification results
    category: Optional[EmailCategory] = None
    priority_score: float = 0.0
    priority_level: Optional[Priority] = None
    
    # AI-generated fields
    summary: Optional[str] = None
    key_entities: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    detected_intent: Optional[str] = None
    sentiment_score: float = 0.0
    
    # Response tracking
    requires_response: bool = False
    response_deadline: Optional[datetime] = None
    draft_response: Optional[str] = None
    has_been_read: bool = False
    
    # Raw source
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'thread_id': self.thread_id,
            'subject': self.subject,
            'sender': self.sender.to_dict(),
            'recipients': [r.to_dict() for r in self.recipients],
            'cc': [c.to_dict() for c in self.cc],
            'bcc': [b.to_dict() for b in self.bcc],
            'body_text': self.body_text,
            'body_html': self.body_html,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'attachments': [a.to_dict() for a in self.attachments],
            'in_reply_to': self.in_reply_to,
            'references': self.references,
            'category': self.category.value if self.category else None,
            'priority_score': self.priority_score,
            'priority_level': self.priority_level.name if self.priority_level else None,
            'summary': self.summary,
            'key_entities': self.key_entities,
            'action_items': self.action_items,
            'detected_intent': self.detected_intent,
            'sentiment_score': self.sentiment_score,
            'requires_response': self.requires_response,
            'response_deadline': self.response_deadline.isoformat() if self.response_deadline else None,
            'draft_response': self.draft_response,
            'has_been_read': self.has_been_read
        }
