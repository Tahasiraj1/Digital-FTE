"""Calendar MCP server entrypoint."""

from mcp_servers.calendar.server import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
