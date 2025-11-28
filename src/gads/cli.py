"""
GADS CLI

Command-line interface for the Godot Agentic Development System.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Confirm

from .orchestrator import Orchestrator, TaskType, RoutingDecision
from .utils import load_settings, setup_logging, get_logger
from .tools import GodotTool, StableDiffusionTool, BlenderMCPTool

app = typer.Typer(
    name="gads",
    help="Godot Agentic Development System - Multi-agent AI framework for game development",
)
console = Console()

# Global orchestrator instance (lazy loaded)
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        settings = load_settings()
        setup_logging(settings.log_level, settings.log_file)
        _orchestrator = Orchestrator(settings=settings)
    return _orchestrator


def interactive_approval(message: str, decision: RoutingDecision) -> bool:
    """Prompt user for approval."""
    console.print(f"\n[yellow]⚠ {message}[/]")
    console.print(f"[dim]Agent: {decision.agent_name} | Task: {decision.task_type.value}[/]")
    return Confirm.ask("Proceed?", default=True)


# Map agent names to their primary task types for --agent flag
AGENT_TASK_MAP = {
    "architect": TaskType.GAME_CONCEPT,
    "designer": TaskType.MECHANIC_DESIGN,
    "developer_2d": TaskType.IMPLEMENT_FEATURE_2D,
    "developer_3d": TaskType.IMPLEMENT_FEATURE_3D,
    "art_director": TaskType.VISUAL_STYLE,
    "qa": TaskType.REVIEW,
}


@app.command()
def new_project(
    name: str = typer.Argument(..., help="Name for the new game project"),
    description: str = typer.Option("", "--description", "-d", help="Project description"),
    prompt: str = typer.Option("", "--prompt", "-p", help="Initial prompt for the Architect agent"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip approval prompts"),
) -> None:
    """Create a new game project with AI-assisted design."""
    logger = get_logger(__name__)
    
    # Set up approval callback
    if yes:
        orchestrator = get_orchestrator()
    else:
        settings = load_settings()
        setup_logging(settings.log_level, settings.log_file)
        global _orchestrator
        _orchestrator = Orchestrator(settings=settings, approval_callback=interactive_approval)
        orchestrator = _orchestrator
    
    console.print(f"\n[bold green]Creating new project:[/] {name}")
    if description:
        console.print(f"[dim]Description:[/] {description}")
    
    try:
        # Create the session
        session = orchestrator.new_project(name, description)
        console.print(f"[green]✓[/] Project created")
        console.print(f"[dim]Session ID:[/] {session.id}")
        
        # Optionally run architect with initial prompt
        if prompt:
            console.print(f"\n[bold blue]Consulting Architect agent...[/]\n")
            
            with console.status("[bold cyan]Thinking...[/]", spinner="dots"):
                response = asyncio.run(
                    orchestrator.run(
                        prompt,
                        session=session,
                        task_type=TaskType.GAME_CONCEPT,
                    )
                )
            
            # Display response
            console.print(Panel(
                Markdown(response.content),
                title=f"[bold cyan]{response.agent_name}[/]",
                border_style="cyan",
            ))
            
            _show_artifacts(response.artifacts)
        
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
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip approval prompts"),
) -> None:
    """Iterate on an existing project with a natural language instruction."""
    logger = get_logger(__name__)
    
    # Validate agent if specified
    if agent and agent not in AGENT_TASK_MAP:
        console.print(f"[red]✗ Unknown agent:[/] {agent}")
        console.print(f"[dim]Available agents:[/] {', '.join(AGENT_TASK_MAP.keys())}")
        raise typer.Exit(1)
    
    # Set up approval callback
    if yes:
        orchestrator = get_orchestrator()
    else:
        settings = load_settings()
        setup_logging(settings.log_level, settings.log_file)
        global _orchestrator
        _orchestrator = Orchestrator(settings=settings, approval_callback=interactive_approval)
        orchestrator = _orchestrator
    
    try:
        # Resolve session
        session = None
        if session_id:
            console.print(f"[dim]Loading session:[/] {session_id}")
            session = orchestrator.get_session(session_id)
            if session is None:
                console.print(f"[red]✗ Session not found:[/] {session_id}")
                raise typer.Exit(1)
        else:
            # Try current session or most recent
            session = orchestrator.session_manager.current
            
            if session is None:
                # Load most recent session
                sessions = orchestrator.list_sessions()
                if sessions:
                    session = orchestrator.get_session(sessions[0]["id"])
                    console.print(f"[dim]Resuming:[/] {session.project.name}")
                else:
                    console.print("[red]✗ No sessions found.[/]")
                    console.print("Create a project first with [bold]gads new-project \"Project Name\"[/]")
                    raise typer.Exit(1)
        
        console.print(f"\n[bold blue]Processing:[/] {instruction}")
        
        # Determine task type
        task_type = None
        if agent:
            task_type = AGENT_TASK_MAP[agent]
            console.print(f"[dim]Using agent:[/] {agent}")
        
        # Execute
        with console.status("[bold cyan]Thinking...[/]", spinner="dots"):
            response = asyncio.run(
                orchestrator.run(
                    instruction,
                    session=session,
                    task_type=task_type,
                )
            )
        
        # Display response
        console.print()
        console.print(Panel(
            Markdown(response.content),
            title=f"[bold cyan]{response.agent_name}[/]",
            border_style="cyan",
        ))
        
        _show_artifacts(response.artifacts)
        
    except typer.Exit:
        raise
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
        # Resolve session
        session = None
        if session_id:
            session = orchestrator.get_session(session_id)
            if session is None:
                console.print(f"[red]✗ Session not found:[/] {session_id}")
                raise typer.Exit(1)
        else:
            session = orchestrator.session_manager.current
            if session is None:
                # Try most recent
                sessions = orchestrator.list_sessions()
                if sessions:
                    session = orchestrator.get_session(sessions[0]["id"])
        
        if session is None:
            console.print("\n[yellow]No active session[/]")
            console.print("Create a new project with [bold]gads new-project \"Project Name\"[/]")
            return
        
        # Build status display
        console.print(f"\n[bold]GADS Project Status[/]\n")
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="dim")
        table.add_column("Value")
        
        table.add_row("Project", f"[bold]{session.project.name}[/]")
        if session.project.description:
            table.add_row("Description", session.project.description)
        table.add_row("Session ID", session.id)
        table.add_row("Phase", session.project.current_phase)
        table.add_row("Messages", str(len(session.history)))
        if session.truncated_message_count > 0:
            table.add_row("Truncated", f"[yellow]{session.truncated_message_count}[/]")
        table.add_row("Created", str(session.created_at)[:19])
        table.add_row("Updated", str(session.updated_at)[:19])
        
        console.print(table)
        
        # Show tasks
        if session.project.completed_tasks:
            console.print(f"\n[green]Completed:[/] {', '.join(session.project.completed_tasks)}")
        
        if session.project.pending_tasks:
            console.print(f"[yellow]Pending:[/] {', '.join(session.project.pending_tasks)}")
        
        # Show recent history
        if session.history:
            console.print(f"\n[bold]Recent Activity[/]")
            for msg in session.get_recent_history(5):
                role_style = "green" if msg.role == "human" else "cyan"
                agent_info = f" ({msg.agent_name})" if msg.agent_name else ""
                content_preview = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
                content_preview = content_preview.replace("\n", " ")
                console.print(f"  [{role_style}]{msg.role}{agent_info}:[/] {content_preview}")
        
    except typer.Exit:
        raise
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
        table.add_column("Messages", justify="right")
        table.add_column("Updated", style="dim")
        
        for sess in session_list:
            table.add_row(
                sess["project_name"],
                sess["id"][:8] + "...",
                str(sess.get("message_count", "?")),
                sess["updated_at"][:19].replace("T", " "),
            )
        
        console.print(table)
        console.print(f"\n[dim]Use [bold]gads iterate -s <session_id>[/] to continue a session[/]")
        console.print(f"[dim]Use [bold]gads status -s <session_id>[/] to view session details[/]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


@app.command()
def agents() -> None:
    """List available agents and their roles."""
    orchestrator = get_orchestrator()
    
    agent_info = {
        "architect": ("Claude Opus", "High-level game design, system architecture, creative direction"),
        "designer": ("Ollama", "Game mechanics, level design, balancing"),
        "developer_2d": ("Ollama", "GDScript for 2D games, scenes, physics"),
        "developer_3d": ("Ollama", "GDScript for 3D games, cameras, lighting"),
        "art_director": ("Claude Opus", "Visual style, asset specs, Stable Diffusion prompts"),
        "qa": ("Ollama", "Testing, validation, code review"),
    }
    
    console.print(f"\n[bold]Available Agents[/]\n")
    
    table = Table()
    table.add_column("Agent", style="bold cyan")
    table.add_column("Model", style="dim")
    table.add_column("Role")
    
    for name in orchestrator.factory.available_agents:
        model, role = agent_info.get(name, ("Unknown", "Unknown"))
        table.add_row(name, model, role)
    
    console.print(table)
    console.print(f"\n[dim]Use [bold]gads iterate -a <agent> \"instruction\"[/] to use a specific agent[/]")


@app.command()
def check() -> None:
    """Check connectivity to all external services (Ollama, SD, Blender)."""
    import aiohttp
    
    settings = load_settings()
    
    console.print("\n[bold]GADS Service Health Check[/]\n")
    
    async def check_ollama() -> tuple[bool, str, list[str]]:
        """Check Ollama connectivity."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{settings.ollama_host}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status != 200:
                        return False, f"API returned status {resp.status}", []
                    
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    
                    if not models:
                        return False, "No models installed. Run: ollama pull llama3.2:3b", []
                    
                    return True, f"Running with {len(models)} model(s)", models
        except asyncio.TimeoutError:
            return False, "Connection timeout. Is Ollama running?", []
        except aiohttp.ClientConnectorError:
            return False, "Cannot connect. Try: ollama serve", []
        except Exception as e:
            return False, f"Error: {e}", []
    
    async def check_sd() -> tuple[bool, str]:
        """Check Stable Diffusion connectivity."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{settings.sd_api_url}/sdapi/v1/sd-models",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return True, f"Running with {len(data)} model(s)"
                    return False, f"API returned status {resp.status}"
        except asyncio.TimeoutError:
            return False, "Connection timeout"
        except aiohttp.ClientConnectorError:
            return False, "Cannot connect (optional)"
        except Exception as e:
            return False, f"Error: {e}"
    
    async def check_blender() -> tuple[bool, str]:
        """Check Blender MCP connectivity."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{settings.blender_mcp_host}:{settings.blender_mcp_port}/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        return True, "Running"
                    return False, f"API returned status {resp.status}"
        except asyncio.TimeoutError:
            return False, "Connection timeout"
        except aiohttp.ClientConnectorError:
            return False, "Cannot connect (optional)"
        except Exception as e:
            return False, f"Error: {e}"
    
    async def run_checks():
        """Run all health checks."""
        ollama_ok, ollama_msg, ollama_models = await check_ollama()
        sd_ok, sd_msg = await check_sd()
        blender_ok, blender_msg = await check_blender()
        return (
            (ollama_ok, ollama_msg, ollama_models),
            (sd_ok, sd_msg),
            (blender_ok, blender_msg),
        )
    
    # Run checks
    with console.status("[bold cyan]Checking services...[/]", spinner="dots"):
        ollama_result, sd_result, blender_result = asyncio.run(run_checks())
    
    # Display results
    table = Table(show_header=True)
    table.add_column("Service", style="bold")
    table.add_column("Status")
    table.add_column("Details")
    table.add_column("Required")
    
    # Ollama (required)
    ollama_ok, ollama_msg, ollama_models = ollama_result
    status_icon = "[green]✓[/]" if ollama_ok else "[red]✗[/]"
    models_str = ", ".join(ollama_models[:3]) if ollama_models else "-"
    if len(ollama_models) > 3:
        models_str += f" (+{len(ollama_models) - 3})"
    table.add_row(
        "Ollama",
        f"{status_icon} {ollama_msg}",
        models_str,
        "[red]Yes[/]",
    )
    
    # Stable Diffusion (optional)
    sd_ok, sd_msg = sd_result
    status_icon = "[green]✓[/]" if sd_ok else "[yellow]○[/]"
    table.add_row(
        "Stable Diffusion",
        f"{status_icon} {sd_msg}",
        "-",
        "[dim]No[/]",
    )
    
    # Blender MCP (optional)
    blender_ok, blender_msg = blender_result
    status_icon = "[green]✓[/]" if blender_ok else "[yellow]○[/]"
    table.add_row(
        "Blender MCP",
        f"{status_icon} {blender_msg}",
        "-",
        "[dim]No[/]",
    )
    
    console.print(table)
    
    # Summary
    if ollama_ok:
        console.print("\n[green]✓ Ready to run GADS[/]")
        console.print("\n[dim]Run end-to-end tests with:[/]")
        console.print("  pytest tests/test_e2e_ollama.py -v --run-e2e")
    else:
        console.print("\n[red]✗ Ollama is required but not available[/]")
        console.print("\n[dim]To start Ollama:[/]")
        console.print("  1. Install from https://ollama.ai")
        console.print("  2. Run: [bold]ollama serve[/]")
        console.print("  3. Pull a model: [bold]ollama pull llama3.2:3b[/]")
        console.print("     (or any other model you prefer)")
        raise typer.Exit(1)


def _show_artifacts(artifacts: dict) -> None:
    """Display artifact information."""
    if not artifacts:
        return
    
    parts = []
    if artifacts.get("gdscript_blocks"):
        parts.append(f"{len(artifacts['gdscript_blocks'])} code block(s)")
    if artifacts.get("has_architecture"):
        parts.append("architecture design")
    if artifacts.get("has_game_concept"):
        parts.append("game concept")
    if artifacts.get("has_sd_prompts"):
        parts.append("SD prompts")
    if artifacts.get("has_color_palette"):
        parts.append("color palette")
    
    if parts:
        console.print(f"\n[dim]Contains: {', '.join(parts)}[/]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
