"""Core data models for Email Triage Assistant"""

from .email import Email, EmailAddress, Attachment, EmailCategory, Priority
from .thread import EmailThread

__all__ = [
    'Email',
    'EmailAddress',
    'Attachment',
    'EmailCategory',
    'Priority',
    'EmailThread'
]
