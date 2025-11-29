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

from .orchestrator import Orchestrator, TaskType, RoutingDecision, PipelineRegistry, PipelineStatus
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
    is_2d: bool = typer.Option(True, "--2d", help="Create a 2D project (default)"),
    is_3d: bool = typer.Option(False, "--3d", help="Create a 3D project"),
    style: str = typer.Option("", "--style", "-s", help="Art style (e.g., 'pixel-art', 'low-poly')"),
    prompt: str = typer.Option("", "--prompt", "-p", help="Initial prompt for the Architect agent"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip approval prompts"),
) -> None:
    """Create a new game project with AI-assisted design."""
    logger = get_logger(__name__)
    
    # Determine project type (--3d overrides --2d)
    project_type = "3d" if is_3d else "2d"
    
    # Set up approval callback
    if yes:
        orchestrator = get_orchestrator()
    else:
        settings = load_settings()
        setup_logging(settings.log_level, settings.log_file)
        global _orchestrator
        _orchestrator = Orchestrator(settings=settings, approval_callback=interactive_approval)
        orchestrator = _orchestrator
    
    console.print(f"\n[bold green]Creating new project:[/] {name} ({project_type.upper()})")
    if description:
        console.print(f"[dim]Description:[/] {description}")
    if style:
        console.print(f"[dim]Art style:[/] {style}")
    
    try:
        # Create the session
        session = orchestrator.new_project(name, description, project_type=project_type, art_style=style)
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


# ============================================================================
# Pipeline Subcommands
# ============================================================================

pipeline_app = typer.Typer(
    name="pipeline",
    help="Run multi-agent pipelines for complex workflows",
)
app.add_typer(pipeline_app, name="pipeline")


@app.command()
def export(
    output: str = typer.Option(None, "--output", "-o", help="Output directory for Godot project"),
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID to export"),
    open_godot: bool = typer.Option(False, "--open", help="Open project in Godot after export"),
) -> None:
    """Export a session to a Godot project."""
    from .tools import GodotTool
    
    logger = get_logger(__name__)
    orchestrator = get_orchestrator()
    
    # Resolve session
    session = None
    if session_id:
        session = orchestrator.get_session(session_id)
        if session is None:
            console.print(f"[red]\u2717 Session not found:[/] {session_id}")
            raise typer.Exit(1)
    else:
        session = orchestrator.session_manager.current
        if session is None:
            sessions = orchestrator.list_sessions()
            if sessions:
                session = orchestrator.get_session(sessions[0]["id"])
            else:
                console.print("[red]\u2717 No sessions found.[/]")
                console.print("Create a project first with [bold]gads new-project[/]")
                raise typer.Exit(1)
    
    console.print(f"\n[bold]Exporting:[/] {session.project.name}")
    console.print(f"[dim]Session:[/] {session.id[:8]}...")
    console.print(f"[dim]Type:[/] {session.project.project_type.upper()}")
    if session.project.art_style:
        console.print(f"[dim]Style:[/] {session.project.art_style}")
    
    # Initialize GodotTool
    projects_dir = output if output else orchestrator.settings.godot_projects_dir
    tool = GodotTool(projects_dir=projects_dir)
    
    try:
        # Create project
        with console.status("[bold cyan]Creating Godot project...[/]", spinner="dots"):
            project_path = tool.create_project(
                name=session.project.name,
                project_type=session.project.project_type,
                description=session.project.description,
                art_style=session.project.art_style,
            )
        
        console.print(f"[green]\u2713[/] Project created: {project_path}")
        
        # Extract and save scripts from session history
        scripts_saved = 0
        for msg in session.history:
            if msg.role == "agent" and msg.metadata.get("artifacts"):
                artifacts = msg.metadata["artifacts"]
                gdscript_blocks = artifacts.get("gdscript_blocks", [])
                
                for i, block in enumerate(gdscript_blocks):
                    # Try to extract class/script name from content
                    script_name = _extract_script_name(block, i)
                    extends = _extract_extends(block)
                    
                    tool.create_script(
                        project_path,
                        script_name=script_name,
                        extends=extends,
                        content=block,
                    )
                    scripts_saved += 1
        
        if scripts_saved > 0:
            console.print(f"[green]\u2713[/] Saved {scripts_saved} script(s) to scripts/")
        
        # Add icon
        tool.add_icon(project_path)
        console.print(f"[green]\u2713[/] Added project icon")
        
        # Validate
        validation = tool.validate_project(project_path)
        if validation["valid"]:
            console.print(f"[green]\u2713[/] Project validation passed")
        else:
            console.print(f"[yellow]\u26a0[/] Validation warnings: {validation['warnings']}")
        
        # Summary
        console.print(f"\n[bold green]\u2713 Export complete![/]")
        console.print(f"\n[dim]Project location:[/]")
        console.print(f"  {project_path}")
        console.print(f"\n[dim]To open in Godot:[/]")
        console.print(f"  godot --path \"{project_path}\"")
        
        # Optionally open in Godot
        if open_godot:
            console.print(f"\n[cyan]Opening in Godot...[/]")
            tool.run_project(project_path)
        
    except Exception as e:
        logger.exception("Export failed")
        console.print(f"\n[red]\u2717 Export failed:[/] {e}")
        raise typer.Exit(1)


def _extract_script_name(content: str, index: int) -> str:
    """Try to extract a meaningful script name from GDScript content."""
    lines = content.strip().split("\n")
    
    # Look for class_name
    for line in lines[:10]:
        if line.startswith("class_name "):
            name = line.replace("class_name ", "").strip()
            return name.lower()
    
    # Look for extends to guess name
    for line in lines[:5]:
        if line.startswith("extends "):
            base = line.replace("extends ", "").strip()
            if "CharacterBody" in base:
                return "player"
            elif "Area" in base:
                return "trigger"
            elif "RigidBody" in base:
                return "physics_object"
    
    # Fallback
    return f"script_{index}"


def _extract_extends(content: str) -> str:
    """Extract the extends clause from GDScript content."""
    for line in content.strip().split("\n")[:5]:
        if line.startswith("extends "):
            return line.replace("extends ", "").strip()
    return "Node"


@pipeline_app.command("list")
def pipeline_list() -> None:
    """List all available pipelines."""
    from pathlib import Path
    
    # Find templates directory
    templates_dir = Path.cwd() / "templates"
    registry = PipelineRegistry(templates_dir=templates_dir)
    
    pipelines = registry.list()
    
    if not pipelines:
        console.print("\n[yellow]No pipelines available[/]")
        return
    
    console.print(f"\n[bold]Available Pipelines[/] ({len(pipelines)} total)\n")
    
    table = Table()
    table.add_column("Name", style="bold cyan")
    table.add_column("Description")
    
    for p in pipelines:
        table.add_row(p["name"], p["description"])
    
    console.print(table)
    console.print(f"\n[dim]Run a pipeline with:[/] gads pipeline run <name> \"your prompt\"")


@pipeline_app.command("run")
def pipeline_run(
    name: str = typer.Argument(..., help="Name of the pipeline to run"),
    prompt: str = typer.Argument(..., help="Initial prompt for the pipeline"),
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID to continue"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip approval prompts"),
) -> None:
    """Run a multi-agent pipeline."""
    from pathlib import Path
    
    logger = get_logger(__name__)
    
    # Find templates directory
    templates_dir = Path.cwd() / "templates"
    registry = PipelineRegistry(templates_dir=templates_dir)
    
    # Get pipeline
    pipeline = registry.get(name)
    if pipeline is None:
        console.print(f"\n[red]✗ Pipeline not found:[/] {name}")
        console.print(f"\n[dim]Available pipelines:[/] {', '.join(registry.names())}")
        raise typer.Exit(1)
    
    # Set up orchestrator
    if yes:
        orchestrator = get_orchestrator()
    else:
        settings = load_settings()
        setup_logging(settings.log_level, settings.log_file)
        global _orchestrator
        _orchestrator = Orchestrator(settings=settings, approval_callback=interactive_approval)
        orchestrator = _orchestrator
    
    # Resolve session
    session = None
    if session_id:
        session = orchestrator.get_session(session_id)
        if session is None:
            console.print(f"[red]✗ Session not found:[/] {session_id}")
            raise typer.Exit(1)
        console.print(f"[dim]Resuming session:[/] {session.project.name}")
    else:
        # Try current session or create new
        session = orchestrator.session_manager.current
        if session is None:
            sessions = orchestrator.list_sessions()
            if sessions:
                session = orchestrator.get_session(sessions[0]["id"])
                console.print(f"[dim]Using recent session:[/] {session.project.name}")
            else:
                # Create new session for this pipeline
                session = orchestrator.new_project(f"Pipeline: {name}", f"Created for {name} pipeline")
                console.print(f"[dim]Created new session:[/] {session.id[:8]}...")
    
    # Display pipeline info
    console.print(f"\n[bold]Pipeline:[/] {pipeline.name}")
    console.print(f"[dim]{pipeline.description}[/]")
    console.print(f"[dim]Steps:[/] {len(pipeline.steps)}")
    console.print()
    
    # Run the pipeline
    try:
        with console.status(f"[bold cyan]Running pipeline...[/]", spinner="dots"):
            result = asyncio.run(
                orchestrator.run_pipeline(
                    pipeline,
                    session=session,
                    initial_input=prompt,
                )
            )
        
        # Display results
        console.print(f"\n{'=' * 60}")
        console.print(f"[bold]Pipeline: {pipeline.name}[/]")
        console.print(f"{'=' * 60}\n")
        
        # Show each step's output
        for i, step in enumerate(pipeline.steps, 1):
            step_name = step.name
            output_key = step.output_key
            
            console.print(f"[bold]Step {i}/{len(pipeline.steps)}: {step_name}[/]")
            console.print("-" * 60)
            
            if output_key and output_key in result.outputs:
                output = result.outputs[output_key]
                console.print(Panel(
                    Markdown(str(output)),
                    border_style="cyan",
                ))
            else:
                console.print("[dim]No output captured[/]")
            
            console.print()
        
        # Summary
        console.print(f"{'=' * 60}")
        if result.status == PipelineStatus.COMPLETED:
            console.print(f"[green]✓ Pipeline completed successfully ({len(result.completed_steps)}/{len(pipeline.steps)} steps)[/]")
        elif result.status == PipelineStatus.CANCELLED:
            console.print(f"[yellow]○ Pipeline cancelled: {result.error}[/]")
        else:
            console.print(f"[red]✗ Pipeline failed: {result.error}[/]")
            raise typer.Exit(1)
        console.print(f"{'=' * 60}")
        
    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Pipeline execution failed")
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


# ============================================================================
# Art Generation Subcommands
# ============================================================================

art_app = typer.Typer(
    name="art",
    help="Generate art assets using Stable Diffusion",
)
app.add_typer(art_app, name="art")


@art_app.command("check")
def art_check() -> None:
    """Check Stable Diffusion API connectivity."""
    from .tools.stable_diffusion import StableDiffusionTool
    
    settings = load_settings()
    tool = StableDiffusionTool(api_url=settings.sd_api_url)
    
    console.print("\n[bold]Stable Diffusion API Check[/]\n")
    
    async def run_check():
        try:
            result = await tool.health_check()
            
            if result["available"]:
                console.print(f"[green]\u2713 Connected to:[/] {result['api_url']}")
                console.print(f"[dim]Current model:[/] {result.get('model', 'unknown')}")
                
                # Get models and samplers
                try:
                    models = await tool.get_models()
                    samplers = await tool.get_samplers()
                    console.print(f"[dim]Available models:[/] {len(models)}")
                    console.print(f"[dim]Available samplers:[/] {len(samplers)}")
                except Exception:
                    pass
                
                console.print("\n[green]\u2713 Ready to generate art![/]")
                return True
            else:
                console.print(f"[red]\u2717 Cannot connect:[/] {result.get('error', 'Unknown error')}")
                console.print(f"\n[dim]Make sure Stable Diffusion WebUI is running with --api flag:[/]")
                console.print(f"  ./webui.sh --api")
                console.print(f"  (or webui-user.bat --api on Windows)")
                return False
        finally:
            await tool.close()
    
    success = asyncio.run(run_check())
    if not success:
        raise typer.Exit(1)


@art_app.command("presets")
def art_presets() -> None:
    """List available art generation presets."""
    from .tools.stable_diffusion import ArtPreset, PRESET_CONFIGS
    
    console.print("\n[bold]Available Art Presets[/]\n")
    
    table = Table()
    table.add_column("Preset", style="bold cyan")
    table.add_column("Size")
    table.add_column("Steps")
    table.add_column("Best For")
    
    preset_descriptions = {
        ArtPreset.PIXEL_ART: "Retro pixel art sprites and tiles",
        ArtPreset.LOW_POLY: "Low-poly 3D style renders",
        ArtPreset.CONCEPT_ART: "Detailed concept art and illustrations",
        ArtPreset.UI_ICON: "Simple game UI icons",
        ArtPreset.SPRITE: "2D game character sprites",
        ArtPreset.TEXTURE: "Seamless tileable textures",
        ArtPreset.CHARACTER: "Character design sheets",
        ArtPreset.ENVIRONMENT: "Environment and background art",
        ArtPreset.CUSTOM: "Custom settings (no modifications)",
    }
    
    for preset in ArtPreset:
        config = PRESET_CONFIGS.get(preset, {})
        size = f"{config.get('width', 512)}x{config.get('height', 512)}"
        steps = str(config.get('steps', 20))
        desc = preset_descriptions.get(preset, "")
        table.add_row(preset.value, size, steps, desc)
    
    console.print(table)
    console.print("\n[dim]Use presets with:[/] gads art generate --preset <name> \"your prompt\"")


@art_app.command("generate")
def art_generate(
    prompt: str = typer.Argument(..., help="Description of the image to generate"),
    preset: str = typer.Option("concept_art", "--preset", "-p", help="Art style preset"),
    output: str = typer.Option(None, "--output", "-o", help="Output directory (default: ./generated)"),
    name: str = typer.Option("image", "--name", "-n", help="Base name for output files"),
    width: int = typer.Option(None, "--width", "-W", help="Override width"),
    height: int = typer.Option(None, "--height", "-H", help="Override height"),
    steps: int = typer.Option(None, "--steps", help="Override sampling steps"),
    seed: int = typer.Option(-1, "--seed", help="Random seed (-1 for random)"),
    batch: int = typer.Option(1, "--batch", "-b", help="Number of images to generate"),
    negative: str = typer.Option(None, "--negative", help="Additional negative prompt"),
) -> None:
    """Generate an image using Stable Diffusion."""
    from .tools.stable_diffusion import StableDiffusionTool, ArtPreset
    
    logger = get_logger(__name__)
    settings = load_settings()
    
    # Validate preset
    try:
        art_preset = ArtPreset(preset)
    except ValueError:
        console.print(f"[red]\u2717 Unknown preset:[/] {preset}")
        console.print(f"[dim]Available presets:[/] {', '.join(p.value for p in ArtPreset)}")
        raise typer.Exit(1)
    
    tool = StableDiffusionTool(api_url=settings.sd_api_url)
    
    # Build overrides
    overrides = {"batch_size": batch, "seed": seed}
    if width:
        overrides["width"] = width
    if height:
        overrides["height"] = height
    if steps:
        overrides["steps"] = steps
    
    # Build config
    config = tool.apply_preset(prompt, art_preset, **overrides)
    
    # Add extra negative prompt if provided
    if negative:
        config.negative_prompt = f"{config.negative_prompt}, {negative}"
    
    console.print(f"\n[bold]Generating Art[/]\n")
    console.print(f"[dim]Preset:[/] {preset}")
    console.print(f"[dim]Size:[/] {config.width}x{config.height}")
    console.print(f"[dim]Steps:[/] {config.steps}")
    console.print(f"[dim]Batch:[/] {batch}")
    console.print(f"\n[dim]Prompt:[/] {config.prompt[:100]}{'...' if len(config.prompt) > 100 else ''}")
    console.print()
    
    async def run_generation():
        try:
            result = await tool.generate(config)
            
            if not result.success:
                console.print(f"[red]\u2717 Generation failed:[/] {result.error}")
                return None
            
            # Save images
            output_dir = Path(output) if output else Path("./generated")
            saved_paths = await tool.save_images(result, output_dir, name)
            
            return result, saved_paths
        finally:
            await tool.close()
    
    try:
        with console.status("[bold cyan]Generating...[/]", spinner="dots"):
            gen_result = asyncio.run(run_generation())
        
        if gen_result is None:
            raise typer.Exit(1)
        
        result, saved_paths = gen_result
        
        console.print(f"[green]\u2713 Generated {len(saved_paths)} image(s)![/]\n")
        
        for path in saved_paths:
            console.print(f"  [dim]Saved:[/] {path}")
        
        if result.seeds:
            console.print(f"\n[dim]Seeds:[/] {', '.join(str(s) for s in result.seeds)}")
        
    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Art generation failed")
        console.print(f"\n[red]\u2717 Error:[/] {e}")
        raise typer.Exit(1)


@art_app.command("to-project")
def art_to_project(
    prompt: str = typer.Argument(..., help="Description of the image to generate"),
    preset: str = typer.Option("concept_art", "--preset", help="Art style preset"),
    asset_type: str = typer.Option("sprites", "--type", "-t", help="Asset type (sprites, textures, concept_art, ui)"),
    name: str = typer.Option("asset", "--name", "-n", help="Base name for output files"),
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID to get project from"),
    project_path: str = typer.Option(None, "--project", "-p", help="Direct path to Godot project"),
    batch: int = typer.Option(1, "--batch", "-b", help="Number of images to generate"),
) -> None:
    """Generate art and save directly to a Godot project."""
    from .tools.stable_diffusion import StableDiffusionTool, ArtPreset
    
    logger = get_logger(__name__)
    settings = load_settings()
    
    # Validate preset
    try:
        art_preset = ArtPreset(preset)
    except ValueError:
        console.print(f"[red]\u2717 Unknown preset:[/] {preset}")
        raise typer.Exit(1)
    
    # Determine project path
    godot_project = None
    if project_path:
        godot_project = Path(project_path)
        if not (godot_project / "project.godot").exists():
            console.print(f"[red]\u2717 Not a valid Godot project:[/] {project_path}")
            raise typer.Exit(1)
    else:
        # Get from session
        orchestrator = get_orchestrator()
        session = None
        if session_id:
            session = orchestrator.get_session(session_id)
        else:
            session = orchestrator.session_manager.current
            if session is None:
                sessions = orchestrator.list_sessions()
                if sessions:
                    session = orchestrator.get_session(sessions[0]["id"])
        
        if session is None:
            console.print("[red]\u2717 No session found.[/]")
            console.print("[dim]Use --project to specify a Godot project path directly[/]")
            raise typer.Exit(1)
        
        # Look for exported project
        safe_name = session.project.name.lower().replace(" ", "_")
        godot_project = Path(settings.godot_projects_dir) / safe_name
        
        if not godot_project.exists():
            console.print(f"[yellow]Project not exported yet. Run:[/] gads export")
            raise typer.Exit(1)
    
    console.print(f"\n[bold]Generating Art to Project[/]\n")
    console.print(f"[dim]Project:[/] {godot_project}")
    console.print(f"[dim]Asset type:[/] {asset_type}")
    console.print(f"[dim]Preset:[/] {preset}")
    console.print()
    
    tool = StableDiffusionTool(api_url=settings.sd_api_url)
    
    async def run_generation():
        try:
            saved_paths = await tool.generate_to_godot_project(
                prompt=prompt,
                project_path=godot_project,
                preset=art_preset,
                asset_type=asset_type,
                name=name,
                batch_size=batch,
            )
            return saved_paths
        finally:
            await tool.close()
    
    try:
        with console.status("[bold cyan]Generating and saving...[/]", spinner="dots"):
            saved_paths = asyncio.run(run_generation())
        
        console.print(f"[green]\u2713 Generated {len(saved_paths)} asset(s)![/]\n")
        for path in saved_paths:
            console.print(f"  [dim]Saved:[/] {path}")
        
    except Exception as e:
        logger.exception("Art generation failed")
        console.print(f"\n[red]\u2717 Error:[/] {e}")
        raise typer.Exit(1)


# ============================================================================
# Blender MCP Subcommands
# ============================================================================

blender_app = typer.Typer(
    name="blender",
    help="Interact with Blender via MCP for 3D asset creation",
)
app.add_typer(blender_app, name="blender")


@blender_app.command("check")
def blender_check() -> None:
    """Check Blender availability."""
    from .tools.blender_mcp import BlenderMCPTool
    
    settings = load_settings()
    tool = BlenderMCPTool(blender_path=settings.blender_path)
    
    console.print("\n[bold]Blender Check[/]\n")
    
    async def run_check():
        try:
            result = await tool.health_check()
            return result
        finally:
            await tool.close()
    
    result = asyncio.run(run_check())
    
    if result["available"]:
        console.print(f"[green]\u2713 Blender found[/]")
        console.print(f"[dim]Version:[/] {result.get('blender_version', 'unknown')}")
        console.print(f"[dim]Mode:[/] {result.get('mode', 'subprocess')}")
        console.print("\n[green]\u2713 Ready to create 3D assets![/]")
    else:
        console.print(f"[red]\u2717 Cannot connect:[/] {result.get('error', 'Unknown error')}")
        console.print(f"\n[dim]Make sure Blender is installed and in your PATH:[/]")
        console.print(f"  1. Install Blender from https://www.blender.org/download/")
        console.print(f"  2. Add Blender to your system PATH")
        console.print(f"  3. Or specify the path in .env: GODOT_EXECUTABLE=blender")
        raise typer.Exit(1)


@blender_app.command("scene")
def blender_scene(
    blend_file: str = typer.Option(None, "--file", "-f", help="Path to .blend file to inspect"),
) -> None:
    """Show Blender scene info (from file or default scene)."""
    from .tools.blender_mcp import BlenderMCPTool
    
    settings = load_settings()
    tool = BlenderMCPTool(blender_path=settings.blender_path)
    
    async def run_scene_info():
        try:
            scene = await tool.get_scene_info()
            return scene
        finally:
            await tool.close()
    
    try:
        scene = asyncio.run(run_scene_info())
        
        console.print("\n[bold]Blender Scene Info[/]\n")
        console.print(f"[dim]Scene name:[/] {scene.name}")
        console.print(f"[dim]Object count:[/] {scene.object_count}")
        console.print(f"[dim]Materials:[/] {scene.materials_count}")
        
        if scene.objects:
            console.print(f"\n[bold]Objects:[/]")
            for obj in scene.objects[:20]:
                loc = obj.get('location', [0,0,0])
                console.print(f"  - {obj['name']} ({obj['type']}) at ({loc[0]:.1f}, {loc[1]:.1f}, {loc[2]:.1f})")
            if len(scene.objects) > 20:
                console.print(f"  ... and {len(scene.objects) - 20} more")
        else:
            console.print("\n[dim]No objects in scene[/]")
            
    except Exception as e:
        console.print(f"\n[red]\u2717 Error:[/] {e}")
        raise typer.Exit(1)


@blender_app.command("create")
def blender_create(
    primitive: str = typer.Argument(..., help="Primitive type (cube, sphere, cylinder, plane, cone, torus, monkey)"),
    name: str = typer.Option(None, "--name", "-n", help="Name for the object"),
    output: str = typer.Option(None, "--output", "-o", help="Export directly to GLB file"),
    scale: float = typer.Option(1.0, "--scale", "-s", help="Uniform scale"),
) -> None:
    """Create a primitive mesh and optionally export to GLB."""
    from .tools.blender_mcp import BlenderMCPTool
    
    settings = load_settings()
    tool = BlenderMCPTool(blender_path=settings.blender_path)
    
    async def run_create():
        try:
            if output:
                # Create and export in one step
                return await tool.create_and_export_primitive(
                    primitive_type=primitive,
                    output_path=output,
                    name=name,
                    scale=(scale, scale, scale),
                )
            else:
                # Just create (for inspection)
                obj_name = await tool.create_primitive(
                    primitive_type=primitive,
                    name=name,
                    scale=(scale, scale, scale),
                )
                return obj_name
        finally:
            await tool.close()
    
    try:
        with console.status("[bold cyan]Creating...[/]", spinner="dots"):
            result = asyncio.run(run_create())
        
        if output:
            console.print(f"[green]\u2713 Created and exported:[/] {result}")
        else:
            console.print(f"[green]\u2713 Created:[/] {result}")
            console.print(f"[dim]Scale:[/] {scale}")
            console.print(f"\n[dim]Use --output to export to GLB[/]")
        
    except ValueError as e:
        console.print(f"[red]\u2717 Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]\u2717 Error:[/] {e}")
        raise typer.Exit(1)


@blender_app.command("export")
def blender_export(
    output: str = typer.Argument(..., help="Output file path"),
    blend_file: str = typer.Option(None, "--file", "-f", help="Path to .blend file to export"),
    format: str = typer.Option("glb", "--format", help="Export format (glb, gltf, fbx, obj)"),
) -> None:
    """Export a .blend file to GLB/FBX/OBJ."""
    from .tools.blender_mcp import BlenderMCPTool
    
    settings = load_settings()
    tool = BlenderMCPTool(blender_path=settings.blender_path)
    
    async def run_export():
        try:
            if format.lower() in ["glb", "gltf"]:
                export_format = "GLB" if format.lower() == "glb" else "GLTF_SEPARATE"
                return await tool.export_gltf(output, blend_file, False, export_format)
            elif format.lower() == "fbx":
                return await tool.export_fbx(output, blend_file, False)
            elif format.lower() == "obj":
                return await tool.export_obj(output, blend_file, False)
            else:
                raise ValueError(f"Unsupported format: {format}. Use glb, gltf, fbx, or obj.")
        finally:
            await tool.close()
    
    try:
        with console.status("[bold cyan]Exporting...[/]", spinner="dots"):
            output_path = asyncio.run(run_export())
        
        console.print(f"[green]\u2713 Exported to:[/] {output_path}")
        
    except Exception as e:
        console.print(f"\n[red]\u2717 Error:[/] {e}")
        raise typer.Exit(1)


@blender_app.command("to-project")
def blender_to_project(
    name: str = typer.Argument("model", help="Name for the exported model"),
    blend_file: str = typer.Option(None, "--file", "-f", help="Path to .blend file to export"),
    session_id: str = typer.Option(None, "--session", "-s", help="Session ID to get project from"),
    project_path: str = typer.Option(None, "--project", help="Direct path to Godot project"),
) -> None:
    """Export a .blend file directly to a Godot project."""
    from .tools.blender_mcp import BlenderMCPTool
    
    logger = get_logger(__name__)
    settings = load_settings()
    
    # Determine project path
    godot_project = None
    if project_path:
        godot_project = Path(project_path)
        if not (godot_project / "project.godot").exists():
            console.print(f"[red]\u2717 Not a valid Godot project:[/] {project_path}")
            raise typer.Exit(1)
    else:
        # Get from session
        orchestrator = get_orchestrator()
        session = None
        if session_id:
            session = orchestrator.get_session(session_id)
        else:
            session = orchestrator.session_manager.current
            if session is None:
                sessions = orchestrator.list_sessions()
                if sessions:
                    session = orchestrator.get_session(sessions[0]["id"])
        
        if session is None:
            console.print("[red]\u2717 No session found.[/]")
            console.print("[dim]Use --project to specify a Godot project path directly[/]")
            raise typer.Exit(1)
        
        # Look for exported project
        safe_name = session.project.name.lower().replace(" ", "_")
        godot_project = Path(settings.godot_projects_dir) / safe_name
        
        if not godot_project.exists():
            console.print(f"[yellow]Project not exported yet. Run:[/] gads export")
            raise typer.Exit(1)
    
    tool = BlenderMCPTool(blender_path=settings.blender_path)
    
    async def run_export():
        try:
            return await tool.export_to_godot_project(
                project_path=godot_project,
                filename=name,
                blend_file=blend_file,
            )
        finally:
            await tool.close()
    
    try:
        console.print(f"\n[bold]Exporting to Godot Project[/]\n")
        console.print(f"[dim]Project:[/] {godot_project}")
        console.print(f"[dim]Model name:[/] {name}")
        if blend_file:
            console.print(f"[dim]Source:[/] {blend_file}")
        console.print()
        
        with console.status("[bold cyan]Exporting...[/]", spinner="dots"):
            output_path = asyncio.run(run_export())
        
        console.print(f"[green]\u2713 Exported to:[/] {output_path}")
        console.print(f"\n[dim]The model will be auto-imported when you open the project in Godot.[/]")
        
    except Exception as e:
        logger.exception("Blender export failed")
        console.print(f"\n[red]\u2717 Error:[/] {e}")
        raise typer.Exit(1)


@blender_app.command("clear")
def blender_clear() -> None:
    """Show info about clearing scenes (use Blender directly)."""
    console.print("\n[bold]Blender Clear Scene[/]\n")
    console.print("[dim]The GADS CLI uses Blender in batch/background mode.")
    console.print("To clear a scene, open your .blend file in Blender and clear it there.")
    console.print("\nAlternatively, use the 'create' command which starts fresh:[/]")
    console.print("  gads blender create cube --output my_model.glb")


@blender_app.command("create-to-project")
def blender_create_to_project(
    primitive: str = typer.Argument(..., help="Primitive type (cube, sphere, cylinder, plane, cone, torus, monkey)"),
    name: str = typer.Option(None, "--name", "-n", help="Name for the model file"),
    scale: float = typer.Option(1.0, "--scale", "-s", help="Uniform scale"),
    session_id: str = typer.Option(None, "--session", help="Session ID to get project from"),
    project_path: str = typer.Option(None, "--project", "-p", help="Direct path to Godot project"),
) -> None:
    """Create a primitive and export directly to a Godot project."""
    from .tools.blender_mcp import BlenderMCPTool
    
    logger = get_logger(__name__)
    settings = load_settings()
    
    # Determine project path
    godot_project = None
    if project_path:
        godot_project = Path(project_path)
        if not (godot_project / "project.godot").exists():
            console.print(f"[red]\u2717 Not a valid Godot project:[/] {project_path}")
            raise typer.Exit(1)
    else:
        # Get from session
        orchestrator = get_orchestrator()
        session = None
        if session_id:
            session = orchestrator.get_session(session_id)
        else:
            session = orchestrator.session_manager.current
            if session is None:
                sessions = orchestrator.list_sessions()
                if sessions:
                    session = orchestrator.get_session(sessions[0]["id"])
        
        if session is None:
            console.print("[red]\u2717 No session found.[/]")
            console.print("[dim]Use --project to specify a Godot project path directly[/]")
            raise typer.Exit(1)
        
        # Look for exported project
        safe_name = session.project.name.lower().replace(" ", "_")
        godot_project = Path(settings.godot_projects_dir) / safe_name
        
        if not godot_project.exists():
            # Try to find the most recent export
            projects_dir = Path(settings.godot_projects_dir)
            if projects_dir.exists():
                matches = list(projects_dir.glob(f"{safe_name}*"))
                if matches:
                    godot_project = max(matches, key=lambda p: p.stat().st_mtime)
                else:
                    console.print(f"[yellow]Project not exported yet. Run:[/] gads export")
                    raise typer.Exit(1)
            else:
                console.print(f"[yellow]Project not exported yet. Run:[/] gads export")
                raise typer.Exit(1)
    
    # Determine output path
    model_name = name or primitive
    output_path = godot_project / "assets" / "models" / f"{model_name}.glb"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    tool = BlenderMCPTool(blender_path=settings.blender_path)
    
    async def run_create():
        try:
            return await tool.create_and_export_primitive(
                primitive_type=primitive,
                output_path=output_path,
                name=model_name,
                scale=(scale, scale, scale),
            )
        finally:
            await tool.close()
    
    try:
        console.print(f"\n[bold]Creating {primitive} for Godot Project[/]\n")
        console.print(f"[dim]Project:[/] {godot_project}")
        console.print(f"[dim]Model:[/] {model_name}.glb")
        console.print(f"[dim]Scale:[/] {scale}")
        console.print()
        
        with console.status("[bold cyan]Creating and exporting...[/]", spinner="dots"):
            result_path = asyncio.run(run_create())
        
        console.print(f"[green]\u2713 Created:[/] {result_path}")
        console.print(f"\n[dim]The model will be auto-imported when you open the project in Godot.[/]")
        
    except ValueError as e:
        console.print(f"[red]\u2717 Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        logger.exception("Blender create failed")
        console.print(f"\n[red]\u2717 Error:[/] {e}")
        raise typer.Exit(1)


# ============================================================================
# Hyper3D Rodin Subcommands
# ============================================================================

rodin_app = typer.Typer(
    name="rodin",
    help="Generate 3D models using Hyper3D Rodin AI",
)
blender_app.add_typer(rodin_app, name="rodin")


@rodin_app.command("check")
def rodin_check() -> None:
    """Check if Hyper3D Rodin is enabled and available."""
    console.print("\n[bold]Hyper3D Rodin Status[/]\n")
    console.print("[dim]Hyper3D Rodin requires the Blender MCP addon running with Rodin enabled.[/]")
    console.print("\n[yellow]Note:[/] This feature requires Claude's MCP connection to Blender.")
    console.print("\nTo enable Hyper3D Rodin:")
    console.print("  1. Open Blender")
    console.print("  2. Press N to show the sidebar in 3D Viewport")
    console.print("  3. Find the BlenderMCP panel")
    console.print("  4. Check 'Use Hyper3D Rodin 3D model generation'")
    console.print("  5. Enter your Hyper3D API key if required")
    console.print("  6. Connect to Claude via the MCP server")
    console.print("\n[dim]Once enabled, use Claude to generate models:[/]")
    console.print('  "Generate a 3D model of a medieval sword"')


@rodin_app.command("info")
def rodin_info() -> None:
    """Show information about Hyper3D Rodin integration."""
    console.print("\n[bold]Hyper3D Rodin AI Model Generation[/]\n")
    
    console.print("[bold cyan]What is Hyper3D Rodin?[/]")
    console.print("Hyper3D Rodin is an AI service that generates 3D models from text")
    console.print("descriptions or reference images. Models are generated with textures")
    console.print("and can be imported directly into Blender.\n")
    
    console.print("[bold cyan]Generation Methods[/]")
    table = Table()
    table.add_column("Method", style="bold")
    table.add_column("Description")
    table.add_row("Text-to-3D", "Generate from a text description (English)")
    table.add_row("Image-to-3D", "Generate from one or more reference images")
    console.print(table)
    
    console.print("\n[bold cyan]Available Modes[/]")
    table2 = Table()
    table2.add_column("Mode", style="bold")
    table2.add_column("Description")
    table2.add_row("MAIN_SITE", "Direct Hyper3D API (requires API key)")
    table2.add_row("FAL_AI", "Via fal.ai service (alternative backend)")
    console.print(table2)
    
    console.print("\n[bold cyan]Usage with Claude[/]")
    console.print("Once enabled, ask Claude to generate models:")
    console.print('  "Create a 3D model of a treasure chest"')
    console.print('  "Generate a low-poly tree model"')
    console.print('  "Make a 3D character from this image" (with uploaded image)')
    
    console.print("\n[bold cyan]Bbox Condition[/]")
    console.print("Control model proportions with bbox_condition [Length, Width, Height]:")
    console.print("  [1, 1, 2] - Tall object (2x height)")
    console.print("  [2, 1, 1] - Long object (2x length)")
    console.print("  [1, 1, 1] - Default proportions")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
