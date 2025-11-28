"""
GADS CLI

Command-line interface for the Godot Agentic Development System.
"""

from __future__ import annotations

import typer
from rich.console import Console

from .utils import Settings, load_settings, setup_logging, get_logger

app = typer.Typer(
    name="gads",
    help="Godot Agentic Development System - Multi-agent AI framework for game development",
)
console = Console()


@app.command()
def new_project(
    name: str = typer.Argument(..., help="Name for the new game project"),
    description: str = typer.Option("", "--description", "-d", help="Project description"),
) -> None:
    """Create a new game project with AI-assisted design."""
    settings = load_settings()
    setup_logging(settings.log_level, settings.log_file)
    logger = get_logger(__name__)
    
    console.print(f"[bold green]Creating new project:[/] {name}")
    logger.info(f"Creating project: {name}")
    
    # TODO: Implement project creation flow
    console.print("[yellow]Project creation not yet implemented[/]")


@app.command()
def iterate(
    instruction: str = typer.Argument(..., help="What to do or change in the project"),
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID to continue"),
) -> None:
    """Iterate on an existing project with a natural language instruction."""
    settings = load_settings()
    setup_logging(settings.log_level, settings.log_file)
    
    console.print(f"[bold blue]Instruction:[/] {instruction}")
    
    # TODO: Implement iteration flow
    console.print("[yellow]Iteration not yet implemented[/]")


@app.command()
def status() -> None:
    """Show the status of the current session and project."""
    console.print("[bold]GADS Status[/]")
    console.print("[yellow]Status not yet implemented[/]")


@app.command()
def sessions() -> None:
    """List all saved sessions."""
    settings = load_settings()
    
    console.print("[bold]Saved Sessions[/]")
    console.print("[yellow]Session listing not yet implemented[/]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
