"""
GADS Main Entry Point

Starts the orchestrator and handles top-level application flow.
"""

from __future__ import annotations

import asyncio

from .cli import main as cli_main


def main() -> None:
    """Main entry point for GADS."""
    cli_main()


if __name__ == "__main__":
    main()
