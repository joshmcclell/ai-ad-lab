"""
TikTok OAuth 2.0 helper (authorization-code flow with PKCE-free client secret).

Run `python scripts/auth_tiktok.py` once to authorize your own account. It
opens a browser, you approve, and the access/refresh tokens are saved to
tokens.json (gitignored). Access tokens last 24h; refresh tokens ~365 days.

Docs: https://developers.tiktok.com/doc/oauth-user-access-token-management
"""
from __future__ import annotations

import json
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

from .config import ROOT, env

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.upload,video.publish"
TOKENS_PATH = ROOT / "tokens.json"


def _save(tokens: dict) -> None:
    tokens["obtained_at"] = int(time.time())
    TOKENS_PATH.write_text(json.dumps(tokens, indent=2))


def _load() -> dict:
    if not TOKENS_PATH.exists():
        raise RuntimeError("No tokens.json. Run: python scripts/auth_tiktok.py")
    return json.loads(TOKENS_PATH.read_text())


def authorize() -> dict:
    """Interactive one-time authorization. Returns and persists tokens."""
    client_key = env("TIKTOK_CLIENT_KEY", required=True)
    client_secret = env("TIKTOK_CLIENT_SECRET", required=True)
    redirect_uri = env("TIKTOK_REDIRECT_URI", required=True)

    state = "ai-ad-lab"
    params = {
        "client_key": client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    print("Opening browser to authorize TikTok...")
    webbrowser.open(AUTH_URL + "?" + urllib.parse.urlencode(params))

    # Tiny local server to catch the ?code=... callback.
    code_holder: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.urlparse(self.path).query
            parsed = urllib.parse.parse_qs(q)
            code_holder.update({k: v[0] for k, v in parsed.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authorized. You can close this tab.</h2>")

        def log_message(self, *_):  # silence
            return

    parsed_redirect = urllib.parse.urlparse(redirect_uri)
    server = HTTPServer((parsed_redirect.hostname, parsed_redirect.port or 80), Handler)
    server.handle_request()  # blocks until one request

    if "code" not in code_holder:
        raise RuntimeError(f"Authorization failed: {code_holder}")

    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code_holder["code"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    resp.raise_for_status()
    tokens = resp.json()
    if "access_token" not in tokens:
        raise RuntimeError(f"Token exchange failed: {tokens}")
    _save(tokens)
    print(f"Authorized as open_id={tokens.get('open_id')}. Saved tokens.json.")
    return tokens


def _refresh(tokens: dict) -> dict:
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": env("TIKTOK_CLIENT_KEY", required=True),
            "client_secret": env("TIKTOK_CLIENT_SECRET", required=True),
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    new = resp.json()
    _save(new)
    return new


def access_token() -> str:
    """Return a valid access token, refreshing if it is near expiry."""
    tokens = _load()
    age = int(time.time()) - tokens.get("obtained_at", 0)
    # Access tokens last ~86400s; refresh 5 min early.
    if age > tokens.get("expires_in", 86400) - 300:
        tokens = _refresh(tokens)
    return tokens["access_token"]
