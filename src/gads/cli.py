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

from .orchestrator import Orchestrator, TaskType, RoutingDecision, PipelineRegistry, PipelineStatus, PipelineEvent
from .agents import TokenUsage
from .utils import load_settings, setup_logging, get_logger
from .tools import GodotTool, BlenderMCPTool

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
    agent: str = typer.Option(None, "--agent", "-a", help="Force specific agent (architect, designer, developer_2d, developer_3d, qa)"),
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
    """Check connectivity to required services (Ollama)."""
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
    
    async def check_blender() -> tuple[bool, str]:
        """Check Blender availability."""
        tool = BlenderMCPTool(blender_path=settings.blender_path)
        try:
            result = await tool.health_check()
            if result["available"]:
                return True, f"Version {result.get('blender_version', 'unknown')}"
            return False, result.get("error", "Not available")
        finally:
            await tool.close()
    
    async def run_checks():
        """Run all health checks."""
        ollama_ok, ollama_msg, ollama_models = await check_ollama()
        blender_ok, blender_msg = await check_blender()
        return (
            (ollama_ok, ollama_msg, ollama_models),
            (blender_ok, blender_msg),
        )
    
    # Run checks
    with console.status("[bold cyan]Checking services...[/]", spinner="dots"):
        ollama_result, blender_result = asyncio.run(run_checks())
    
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
    
    # Blender (optional)
    blender_ok, blender_msg = blender_result
    status_icon = "[green]✓[/]" if blender_ok else "[yellow]○[/]"
    table.add_row(
        "Blender",
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
            console.print(f"[red]✗ Session not found:[/] {session_id}")
            raise typer.Exit(1)
    else:
        session = orchestrator.session_manager.current
        if session is None:
            sessions = orchestrator.list_sessions()
            if sessions:
                session = orchestrator.get_session(sessions[0]["id"])
            else:
                console.print("[red]✗ No sessions found.[/]")
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
        
        console.print(f"[green]✓[/] Project created: {project_path}")
        
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
            console.print(f"[green]✓[/] Saved {scripts_saved} script(s) to scripts/")
        
        # Add icon
        tool.add_icon(project_path)
        console.print(f"[green]✓[/] Added project icon")
        
        # Validate
        validation = tool.validate_project(project_path)
        if validation["valid"]:
            console.print(f"[green]✓[/] Project validation passed")
        else:
            console.print(f"[yellow]⚠[/] Validation warnings: {validation['warnings']}")
        
        # Summary
        console.print(f"\n[bold green]✓ Export complete![/]")
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
        console.print(f"\n[red]✗ Export failed:[/] {e}")
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
    
    # Track totals for summary
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    step_outputs: dict[str, str] = {}
    current_spinner = None
    
    def handle_progress(event: str, data: dict) -> None:
        """Handle progress events from pipeline execution."""
        nonlocal total_input_tokens, total_output_tokens, total_cost, current_spinner
        
        if event == PipelineEvent.STEP_START:
            # Stop any existing spinner before printing
            if current_spinner:
                current_spinner.stop()
                current_spinner = None
            
            step_num = data["step_index"]
            total = data["total_steps"]
            step_name = data["step"]
            agent = data["agent"]
            
            console.print(f"\n[bold cyan]Step {step_num}/{total}:[/] {step_name} [dim]({agent})[/]")
            # Don't start spinner here - wait for LLM_CALL_START
            
        elif event == PipelineEvent.LLM_CALL_START:
            # Start spinner right before LLM call
            current_spinner = console.status("  [dim]→ Calling LLM...[/]", spinner="dots")
            current_spinner.start()
            
        elif event == PipelineEvent.STEP_COMPLETE:
            # Stop spinner before output
            if current_spinner:
                current_spinner.stop()
                current_spinner = None
            
            usage: TokenUsage | None = data.get("usage")
            model = data.get("model", "unknown")
            step_name = data["step"]
            
            if usage:
                cost = usage.estimate_cost(model)
                total_input_tokens += usage.input_tokens
                total_output_tokens += usage.output_tokens
                total_cost += cost
                
                console.print(
                    f"  [green]✓[/] Complete "
                    f"[dim]({usage.input_tokens:,} in / {usage.output_tokens:,} out, ${cost:.4f})[/]"
                )
            else:
                console.print(f"  [green]✓[/] Complete")
            
            # Store output for final display
            if data.get("output_preview"):
                step_outputs[step_name] = data["output_preview"]
                
        elif event == PipelineEvent.STEP_SKIPPED:
            # Stop spinner if running
            if current_spinner:
                current_spinner.stop()
                current_spinner = None
            console.print(f"  [yellow]○[/] Skipped: {data['step']} (condition not met)")
            
        elif event == PipelineEvent.APPROVAL_NEEDED:
            # Stop spinner BEFORE prompting for approval
            if current_spinner:
                current_spinner.stop()
                current_spinner = None
            console.print(f"  [yellow]⚠ Approval required for {data['step']}[/]")
            
        elif event == PipelineEvent.APPROVAL_GRANTED:
            console.print(f"  [green]✓[/] Approved")
            # Spinner will be started by LLM_CALL_START event
            
        elif event == PipelineEvent.APPROVAL_DENIED:
            console.print(f"  [red]✗[/] Denied")
            
        elif event == PipelineEvent.PIPELINE_FAILED:
            if current_spinner:
                current_spinner.stop()
                current_spinner = None
            console.print(f"\n  [red]✗ Failed at {data['step']}:[/] {data['error']}")
            if data.get("completed_steps"):
                console.print(f"  [dim]Completed before failure: {', '.join(data['completed_steps'])}[/]")
    
    # Run the pipeline with progress callback
    try:
        result = asyncio.run(
            orchestrator.run_pipeline(
                pipeline,
                session=session,
                initial_input=prompt,
                progress_callback=handle_progress,
            )
        )
        
        # Ensure spinner is stopped
        if current_spinner:
            current_spinner.stop()
        
        # Summary
        console.print(f"\n{'=' * 60}")
        
        if result.status == PipelineStatus.COMPLETED:
            console.print(f"[green]✓ Pipeline completed successfully[/]")
            console.print(f"  Steps: {len(result.completed_steps)}/{len(pipeline.steps)}")
            if total_cost > 0:
                console.print(
                    f"  Tokens: {total_input_tokens:,} in / {total_output_tokens:,} out"
                )
                console.print(f"  Estimated cost: ${total_cost:.4f}")
        elif result.status == PipelineStatus.CANCELLED:
            console.print(f"[yellow]○ Pipeline cancelled[/]")
            console.print(f"  Reason: {result.error}")
            if result.completed_steps:
                console.print(f"  Completed: {', '.join(result.completed_steps)}")
        else:
            console.print(f"[red]✗ Pipeline failed[/]")
            console.print(f"  Error: {result.error}")
            if result.completed_steps:
                console.print(f"  Completed: {', '.join(result.completed_steps)}")
            raise typer.Exit(1)
        
        console.print(f"{'=' * 60}")
        
        # Show outputs on request or verbose mode
        if step_outputs:
            console.print(f"\n[dim]Tip: Use[/] gads status [dim]to see full outputs[/]")
        
    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Pipeline execution failed")
        if current_spinner:
            current_spinner.stop()
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


# ============================================================================
# Blender Subcommands (simplified - primitives only)
# ============================================================================

blender_app = typer.Typer(
    name="blender",
    help="Create placeholder 3D assets using Blender",
)
app.add_typer(blender_app, name="blender")


@blender_app.command("check")
def blender_check() -> None:
    """Check Blender availability."""
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
        console.print(f"[green]✓ Blender found[/]")
        console.print(f"[dim]Version:[/] {result.get('blender_version', 'unknown')}")
        console.print(f"[dim]Mode:[/] {result.get('mode', 'subprocess')}")
        console.print("\n[green]✓ Ready to create placeholder assets![/]")
    else:
        console.print(f"[red]✗ Cannot find Blender:[/] {result.get('error', 'Unknown error')}")
        console.print(f"\n[dim]Make sure Blender is installed and in your PATH:[/]")
        console.print(f"  1. Install Blender from https://www.blender.org/download/")
        console.print(f"  2. Add Blender to your system PATH")
        console.print(f"  3. Or set BLENDER_PATH in .env")
        raise typer.Exit(1)


@blender_app.command("create")
def blender_create(
    primitive: str = typer.Argument(..., help="Primitive type (cube, sphere, cylinder, plane, cone, torus, monkey)"),
    name: str = typer.Option(None, "--name", "-n", help="Name for the object"),
    output: str = typer.Option(None, "--output", "-o", help="Export directly to GLB file"),
    scale: float = typer.Option(1.0, "--scale", "-s", help="Uniform scale"),
) -> None:
    """Create a primitive mesh and optionally export to GLB."""
    settings = load_settings()
    tool = BlenderMCPTool(blender_path=settings.blender_path)
    
    async def run_create():
        try:
            if output:
                return await tool.create_and_export_primitive(
                    primitive_type=primitive,
                    output_path=output,
                    name=name,
                    scale=(scale, scale, scale),
                )
            else:
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
            console.print(f"[green]✓ Created and exported:[/] {result}")
        else:
            console.print(f"[green]✓ Created:[/] {result}")
            console.print(f"[dim]Scale:[/] {scale}")
            console.print(f"\n[dim]Use --output to export to GLB[/]")
        
    except ValueError as e:
        console.print(f"[red]✗ Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


@blender_app.command("export")
def blender_export(
    output: str = typer.Argument(..., help="Output file path"),
    blend_file: str = typer.Option(None, "--file", "-f", help="Path to .blend file to export"),
    format: str = typer.Option("glb", "--format", help="Export format (glb, gltf, fbx, obj)"),
) -> None:
    """Export a .blend file to GLB/FBX/OBJ."""
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
        
        console.print(f"[green]✓ Exported to:[/] {output_path}")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


@blender_app.command("to-project")
def blender_to_project(
    primitive: str = typer.Argument(..., help="Primitive type (cube, sphere, cylinder, plane, cone, torus, monkey)"),
    name: str = typer.Option("placeholder", "--name", "-n", help="Name for the model file"),
    scale: float = typer.Option(1.0, "--scale", "-s", help="Uniform scale"),
    project_path: str = typer.Option(None, "--project", "-p", help="Path to Godot project"),
    session_id: str = typer.Option(None, "--session", help="Session ID to get project from"),
) -> None:
    """Create a primitive and export directly to a Godot project."""
    logger = get_logger(__name__)
    settings = load_settings()
    
    # Determine project path
    godot_project = None
    if project_path:
        godot_project = Path(project_path)
        if not (godot_project / "project.godot").exists():
            console.print(f"[red]✗ Not a valid Godot project:[/] {project_path}")
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
            console.print("[red]✗ No session found.[/]")
            console.print("[dim]Use --project to specify a Godot project path directly[/]")
            raise typer.Exit(1)
        
        # Look for exported project
        safe_name = session.project.name.lower().replace(" ", "_")
        godot_project = Path(settings.godot_projects_dir) / safe_name
        
        if not godot_project.exists():
            console.print(f"[yellow]Project not exported yet. Run:[/] gads export")
            raise typer.Exit(1)
    
    # Determine output path
    output_path = godot_project / "assets" / "models" / f"{name}.glb"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    tool = BlenderMCPTool(blender_path=settings.blender_path)
    
    async def run_create():
        try:
            return await tool.create_and_export_primitive(
                primitive_type=primitive,
                output_path=output_path,
                name=name,
                scale=(scale, scale, scale),
            )
        finally:
            await tool.close()
    
    try:
        console.print(f"\n[bold]Creating {primitive} for Godot Project[/]\n")
        console.print(f"[dim]Project:[/] {godot_project}")
        console.print(f"[dim]Model:[/] {name}.glb")
        console.print(f"[dim]Scale:[/] {scale}")
        console.print()
        
        with console.status("[bold cyan]Creating and exporting...[/]", spinner="dots"):
            result_path = asyncio.run(run_create())
        
        console.print(f"[green]✓ Created:[/] {result_path}")
        console.print(f"\n[dim]The model will be auto-imported when you open the project in Godot.[/]")
        
    except ValueError as e:
        console.print(f"[red]✗ Error:[/] {e}")
        raise typer.Exit(1)
    except Exception as e:
        logger.exception("Blender create failed")
        console.print(f"\n[red]✗ Error:[/] {e}")
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
