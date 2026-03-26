"""
DesktopCommanderPy - Main entry point.

Run this file to start the MCP server:
    python main.py            # stdio transport (default, for Claude Desktop)
    python main.py --http     # HTTP/SSE transport (for remote clients)
    python main.py --port 8080 --http

The server reads security_config.yaml on startup and enforces all
sandbox rules for the lifetime of the session.
"""

import argparse
import logging
import sys
from pathlib import Path


def _setup_logging(level: str = "INFO") -> None:
    """Configure root logger with a clean format."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DesktopCommanderPy MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--http", action="store_true",
        help="Use HTTP/SSE transport instead of stdio (default).",
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Port for HTTP transport (default: 8080).",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="Host for HTTP transport (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO).",
    )
    parser.add_argument(
        "--config", type=str,
        default=str(Path(__file__).parent / "config" / "security_config.yaml"),
        help="Path to security_config.yaml.",
    )
    args = parser.parse_args()

    _setup_logging(args.log_level)
    logger = logging.getLogger("desktopcommanderpy")

    # Import here so logging is configured first
    from core.server import get_server

    mcp = get_server()

    if args.http:
        logger.info("Starting DesktopCommanderPy on http://%s:%d (SSE)", args.host, args.port)
        # show_banner=False: FastMCP prints an ASCII banner to stdout by default.
        # In HTTP/SSE mode this is harmless, but we suppress it for clean logs.
        mcp.run(transport="sse", host=args.host, port=args.port, show_banner=False)
    else:
        logger.info("Starting DesktopCommanderPy on stdio")
        # CRITICAL: show_banner=False is mandatory for stdio transport.
        # Claude Desktop communicates via JSON-RPC over stdout. Any non-JSON
        # output (including FastMCP's ASCII banner) will corrupt the channel,
        # causing Claude Desktop to hang or fail to connect entirely.
        # DO NOT remove this flag.
        mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
