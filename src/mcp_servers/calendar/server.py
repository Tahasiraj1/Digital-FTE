"""Calendar FastMCP server — registers create_event and list_events tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_servers.calendar.tools.create_event import create_event
from mcp_servers.calendar.tools.list_events import list_events

mcp = FastMCP("fte-calendar-mcp")

mcp.tool()(create_event)
mcp.tool()(list_events)
