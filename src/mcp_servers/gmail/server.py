"""Gmail FastMCP server — registers list_emails, read_email, send_reply tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_servers.gmail.tools.list_emails import list_emails
from mcp_servers.gmail.tools.read_email import read_email
from mcp_servers.gmail.tools.send_reply import send_reply

mcp = FastMCP("fte-gmail-mcp")

mcp.tool()(list_emails)
mcp.tool()(read_email)
mcp.tool()(send_reply)
