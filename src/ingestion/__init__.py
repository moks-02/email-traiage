"""Email ingestion components"""

from .mock_generator import MockEmailGenerator

# Optional real email ingestors
try:
    from .gmail_ingestor import GmailIngestor
except ImportError:
    GmailIngestor = None

try:
    from .outlook_ingestor import OutlookIngestor
except ImportError:
    OutlookIngestor = None

try:
    from .imap_ingestor import IMAPIngestor, get_provider_help
except ImportError:
    IMAPIngestor = None
    get_provider_help = None

__all__ = ['MockEmailGenerator', 'GmailIngestor', 'OutlookIngestor', 'IMAPIngestor', 'get_provider_help']
