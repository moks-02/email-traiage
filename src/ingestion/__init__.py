"""Email ingestion components"""

from .mock_generator import MockEmailGenerator

# Optional real email ingestors
try:
    from .gmail_ingestor import GmailIngestor
except ImportError:
    GmailIngestor = None

try:
    from .gmail_auth import get_auth_url, exchange_code_for_tokens, credentials_from_dict
except ImportError:
    get_auth_url = None
    exchange_code_for_tokens = None
    credentials_from_dict = None

try:
    from .outlook_ingestor import OutlookIngestor
except ImportError:
    OutlookIngestor = None

try:
    from .imap_ingestor import IMAPIngestor, get_provider_help
except ImportError:
    IMAPIngestor = None
    get_provider_help = None

__all__ = [
    'MockEmailGenerator',
    'GmailIngestor',
    'get_auth_url', 'exchange_code_for_tokens', 'credentials_from_dict',
    'OutlookIngestor',
    'IMAPIngestor', 'get_provider_help'
]
