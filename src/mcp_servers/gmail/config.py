"""Gmail MCP server configuration."""

from __future__ import annotations

import os
from pathlib import Path


class GmailConfig:
    token_path: Path
    client_id: str
    client_secret: str
    server_name: str = "fte-gmail-mcp"

    def __init__(self) -> None:
        default_token = Path.home() / ".config" / "fte" / "gmail_token.json"
        self.token_path = Path(os.environ.get("GMAIL_TOKEN_PATH", str(default_token)))
        self.client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")


config = GmailConfig()
