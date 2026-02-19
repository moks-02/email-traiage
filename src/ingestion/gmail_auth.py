"""
Gmail OAuth Web Flow
Handles browser-based OAuth authentication with Google,
stores tokens in MongoDB, and provides credentials to GmailIngestor.
"""

import os
import json
from typing import Optional, Tuple

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
]

# The redirect URI must match what's registered in Google Cloud Console
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/gmail/callback")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")


def _get_client_config() -> Optional[dict]:
    """Load client config from credentials.json or environment variables."""
    # Prefer env vars (useful for production / no file on disk)
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if client_id and client_secret:
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        }

    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE) as f:
            return json.load(f)

    return None


def get_auth_url() -> Tuple[str, str]:
    """
    Create and return the Google OAuth authorization URL and state token.

    Returns:
        (auth_url, state) tuple
    Raises:
        RuntimeError if Google libraries aren't installed or credentials missing.
    """
    if not GMAIL_AVAILABLE:
        raise RuntimeError(
            "Google auth libraries not installed. "
            "Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        )

    config = _get_client_config()
    if not config:
        raise RuntimeError(
            "Google credentials not found. Either:\n"
            "  • Place credentials.json in the project root, OR\n"
            "  • Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
        )

    flow = Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",   # Request refresh token
        include_granted_scopes="true",
        prompt="consent",        # Force consent screen so we always get refresh_token
    )
    return auth_url, state


def exchange_code_for_tokens(code: str, state: str) -> dict:
    """
    Exchange an authorization code for OAuth tokens.

    Args:
        code:  The authorization code from the Google callback.
        state: The state value returned by Google (for CSRF protection).

    Returns:
        A dict with the serialized credentials (can be stored in MongoDB).
    """
    if not GMAIL_AVAILABLE:
        raise RuntimeError("Google auth libraries not installed.")

    config = _get_client_config()
    if not config:
        raise RuntimeError("Google credentials not found.")

    flow = Flow.from_client_config(
        config,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI,
    )

    flow.fetch_token(code=code)
    creds = flow.credentials

    # Fetch the authenticated user's email address from Google
    user_email = ""
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"}
        )
        with urllib.request.urlopen(req) as resp:
            import json as _json
            user_email = _json.loads(resp.read()).get("email", "")
    except Exception as e:
        print(f"⚠️ Could not fetch Gmail user email: {e}")

    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "user_email": user_email,
    }


def credentials_from_dict(token_data: dict) -> Optional[Credentials]:
    """
    Reconstruct a Credentials object from a stored dict.
    Refreshes automatically if expired.
    """
    if not GMAIL_AVAILABLE or not token_data:
        return None

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", SCOPES),
    )

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"⚠️ Failed to refresh Google token: {e}")
            return None

    return creds
