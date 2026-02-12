"""Email thread data model"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from .email import Email, EmailAddress, EmailCategory, Priority


@dataclass
class EmailThread:
    """Email conversation thread with 50+ message support"""
    thread_id: str
    subject: str
    participants: List[EmailAddress]
    messages: List[Email]
    
    # Thread-level metadata
    message_count: int = 0
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    
    # Compression & summarization
    compressed_summary: Optional[str] = None
    compression_ratio: float = 0.0
    original_token_count: int = 0
    compressed_token_count: int = 0
    
    # Thread analysis
    key_decisions: List[str] = field(default_factory=list)
    unresolved_questions: List[str] = field(default_factory=list)
    action_items_by_person: Dict[str, List[str]] = field(default_factory=dict)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    
    # Classification
    category: Optional[EmailCategory] = None
    priority_level: Optional[Priority] = None
    
    def __post_init__(self):
        self.message_count = len(self.messages)
        if self.messages:
            self.messages.sort(key=lambda m: m.received_at)
            self.first_message_at = self.messages[0].received_at
            self.last_message_at = self.messages[-1].received_at
    
    def add_message(self, message: Email):
        """Add message and maintain thread integrity"""
        self.messages.append(message)
        self.message_count = len(self.messages)
        self.last_message_at = message.received_at
        if not self.first_message_at:
            self.first_message_at = message.received_at
    
    def get_total_text(self) -> str:
        """Get full thread text for processing"""
        return "\n\n---\n\n".join([
            f"From: {m.sender.email}\nDate: {m.received_at}\n\n{m.body_text}"
            for m in self.messages
        ])
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'thread_id': self.thread_id,
            'subject': self.subject,
            'participants': [p.to_dict() for p in self.participants],
            'message_count': self.message_count,
            'first_message_at': self.first_message_at.isoformat() if self.first_message_at else None,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'compressed_summary': self.compressed_summary,
            'compression_ratio': self.compression_ratio,
            'original_token_count': self.original_token_count,
            'compressed_token_count': self.compressed_token_count,
            'key_decisions': self.key_decisions,
            'unresolved_questions': self.unresolved_questions,
            'action_items_by_person': self.action_items_by_person,
            'timeline': self.timeline,
            'category': self.category.value if self.category else None,
            'priority_level': self.priority_level.name if self.priority_level else None,
            'messages': [m.to_dict() for m in self.messages]
        }
