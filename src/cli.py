"""
GADS CLI

Command-line interface for the Godot Agentic Development System.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from orchestrator import Orchestrator
from utils import load_settings, setup_logging, get_logger

app = typer.Typer(
    name="gads",
    help="Godot Agentic Development System - Multi-agent AI framework for game development",
)
console = Console()

# Global orchestrator instance
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        settings = load_settings()
        setup_logging(settings.log_level, settings.log_file)
        _orchestrator = Orchestrator(settings=settings)
    return _orchestrator


@app.command()
def new_project(
    name: str = typer.Argument(..., help="Name for the new game project"),
    description: str = typer.Option("", "--description", "-d", help="Project description"),
    prompt: str = typer.Option("", "--prompt", "-p", help="Initial prompt for the Architect agent"),
) -> None:
    """Create a new game project with AI-assisted design."""
    logger = get_logger(__name__)
    orchestrator = get_orchestrator()
    
    console.print(f"\n[bold green]Creating new project:[/] {name}")
    if description:
        console.print(f"[dim]Description:[/] {description}")
    
    try:
        # Create project and optionally run architect
        if prompt:
            console.print(f"\n[bold blue]Consulting Architect agent...[/]\n")
            session, response = asyncio.run(
                orchestrator.new_project_flow(name, description, prompt)
            )
            
            if response:
                # Display response
                console.print(Panel(
                    Markdown(response.content),
                    title=f"[bold cyan]{response.agent_name}[/]",
                    border_style="cyan",
                ))
                
                # Show suggested next agent if any
                if response.suggested_next_agent:
                    console.print(f"\n[dim]Suggested next: {response.suggested_next_agent}[/]")
        else:
            session = orchestrator.create_project(name, description)
        
        console.print(f"\n[green]✓[/] Project created successfully!")
        console.print(f"[dim]Session ID:[/] {session.id}")
        console.print(f"\n[dim]Use [bold]gads iterate \"your instruction\"[/] to continue development[/]")
        
    except Exception as e:
        logger.exception("Failed to create project")
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def iterate(
    instruction: str = typer.Argument(..., help="What to do or change in the project"),
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID to continue"),
    agent: str = typer.Option(None, "--agent", "-a", help="Force specific agent (architect, designer, developer_2d, developer_3d, art_director, qa)"),
) -> None:
    """Iterate on an existing project with a natural language instruction."""
    logger = get_logger(__name__)
    orchestrator = get_orchestrator()
    
    try:
        # Load session if specified
        session = None
        if session_id:
            console.print(f"[dim]Loading session:[/] {session_id}")
            session = orchestrator.load_session(session_id)
        else:
            # Try to use current session or most recent
            orchestrator.initialize()
            session = orchestrator.session_manager.current
            
            if session is None:
                # Load most recent session
                sessions = orchestrator.list_sessions()
                if sessions:
                    session = orchestrator.load_session(sessions[0]["id"])
                    console.print(f"[dim]Resuming session:[/] {session.project.name}")
                else:
                    console.print("[red]✗ No sessions found.[/] Create a project first with [bold]gads new-project[/]")
                    raise typer.Exit(1)
        
        console.print(f"\n[bold blue]Processing:[/] {instruction}\n")
        
        # Show which agent will handle this
        if agent:
            console.print(f"[dim]Using agent:[/] {agent}")
        
        # Execute
        with console.status("[bold cyan]Thinking...[/]", spinner="dots"):
            response = asyncio.run(
                orchestrator.execute(instruction, session, agent_name=agent)
            )
        
        # Display response
        console.print(Panel(
            Markdown(response.content),
            title=f"[bold cyan]{response.agent_name}[/]",
            border_style="cyan",
        ))
        
        # Show artifacts if any
        if response.artifacts:
            if response.artifacts.get("gdscript_blocks"):
                console.print(f"\n[dim]Generated {len(response.artifacts['gdscript_blocks'])} code block(s)[/]")
            if response.artifacts.get("has_architecture"):
                console.print("[dim]Contains architecture design[/]")
            if response.artifacts.get("has_game_concept"):
                console.print("[dim]Contains game concept[/]")
        
        # Show suggested next agent
        if response.suggested_next_agent:
            console.print(f"\n[dim]Suggested next: [bold]{response.suggested_next_agent}[/][/]")
        
    except ValueError as e:
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        logger.exception("Failed to execute iteration")
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def status(
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID to check"),
) -> None:
    """Show the status of the current session and project."""
    orchestrator = get_orchestrator()
    
    try:
        # Load specific session if provided
        session = None
        if session_id:
            session = orchestrator.load_session(session_id)
        
        status_info = orchestrator.get_session_status(session)
        
        if not status_info["active"]:
            console.print("\n[yellow]No active session[/]")
            console.print("Create a new project with [bold]gads new-project \"Project Name\"[/]")
            return
        
        # Build status display
        console.print(f"\n[bold]GADS Project Status[/]\n")
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="dim")
        table.add_column("Value")
        
        table.add_row("Project", f"[bold]{status_info['project_name']}[/]")
        if status_info["project_description"]:
            table.add_row("Description", status_info["project_description"])
        table.add_row("Session ID", status_info["session_id"])
        table.add_row("Phase", status_info["current_phase"])
        table.add_row("Messages", str(status_info["message_count"]))
        table.add_row("Created", status_info["created_at"])
        table.add_row("Updated", status_info["updated_at"])
        
        console.print(table)
        
        if status_info["completed_tasks"]:
            console.print(f"\n[green]Completed:[/] {', '.join(status_info['completed_tasks'])}")
        
        if status_info["pending_tasks"]:
            console.print(f"[yellow]Pending:[/] {', '.join(status_info['pending_tasks'])}")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def sessions() -> None:
    """List all saved sessions."""
    orchestrator = get_orchestrator()
    
    try:
        session_list = orchestrator.list_sessions()
        
        if not session_list:
            console.print("\n[yellow]No saved sessions found[/]")
            console.print("Create a new project with [bold]gads new-project \"Project Name\"[/]")
            return
        
        console.print(f"\n[bold]Saved Sessions[/] ({len(session_list)} total)\n")
        
        table = Table()
        table.add_column("Project", style="bold")
        table.add_column("Session ID", style="dim")
        table.add_column("Updated", style="dim")
        
        for sess in session_list:
            table.add_row(
                sess["project_name"],
                sess["id"][:8] + "...",
                sess["updated_at"][:19].replace("T", " "),
            )
        
        console.print(table)
        console.print(f"\n[dim]Use [bold]gads iterate -s <session_id>[/] to continue a session[/]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def agents() -> None:
    """List available agents and their roles."""
    orchestrator = get_orchestrator()
    orchestrator.initialize()
    
    agent_info = {
        "architect": ("Claude Opus 4.5", "High-level game design, system architecture, creative direction"),
        "designer": ("Ollama", "Game mechanics, level design, balancing"),
        "developer_2d": ("Ollama", "GDScript for 2D games, scenes, physics"),
        "developer_3d": ("Ollama", "GDScript for 3D games, cameras, lighting"),
        "art_director": ("Claude Opus 4.5", "Visual style, asset specs, SD prompts"),
        "qa": ("Ollama", "Testing, validation, code review"),
    }
    
    console.print(f"\n[bold]Available Agents[/]\n")
    
    table = Table()
    table.add_column("Agent", style="bold cyan")
    table.add_column("Model", style="dim")
    table.add_column("Role")
    
    for name in orchestrator.agent_factory.available_agents:
        model, role = agent_info.get(name, ("Unknown", "Unknown"))
        table.add_row(name, model, role)
    
    console.print(table)
    console.print(f"\n[dim]Use [bold]gads iterate -a <agent>[/] to force a specific agent[/]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
