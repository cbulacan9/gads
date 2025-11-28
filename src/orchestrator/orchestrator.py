"""
Main Orchestrator for GADS

Coordinates agents, sessions, and pipelines to execute game development tasks.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from agents import AgentFactory, AgentResponse
from utils import Settings, load_settings, get_logger
from .session import Session, SessionManager, ProjectState
from .router import AgentRouter, TaskType


logger = get_logger(__name__)


class Orchestrator:
    """
    Main orchestrator for GADS.
    
    Coordinates agent execution, session management, and task routing
    to build Godot games from natural language instructions.
    """
    
    def __init__(
        self,
        settings: Settings | None = None,
        config_dir: Path | None = None,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            settings: Application settings (loads from env if not provided)
            config_dir: Directory containing config files (defaults to ./config)
        """
        self.settings = settings or load_settings()
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        
        # Initialize components
        self._session_manager: SessionManager | None = None
        self._agent_factory: AgentFactory | None = None
        self._router: AgentRouter | None = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize all orchestrator components."""
        if self._initialized:
            return
        
        logger.info("Initializing GADS Orchestrator")
        
        # Set up session manager
        self._session_manager = SessionManager(self.settings.session_dir)
        
        # Set up agent factory
        api_keys = {}
        if self.settings.anthropic_api_key:
            api_keys["anthropic"] = self.settings.anthropic_api_key
        
        self._agent_factory = AgentFactory(
            config_path=self.config_dir / "agents.yaml",
            prompts_dir=Path("prompts"),
            api_keys=api_keys,
        )
        
        # Create all agents
        agents = self._agent_factory.create_all_agents()
        logger.info(f"Created {len(agents)} agents: {list(agents.keys())}")
        
        # Set up router with agents
        self._router = AgentRouter()
        self._router.register_agents(agents)
        
        self._initialized = True
        logger.info("Orchestrator initialized successfully")
    
    @property
    def session_manager(self) -> SessionManager:
        """Get the session manager."""
        if not self._session_manager:
            self.initialize()
        return self._session_manager
    
    @property
    def agent_factory(self) -> AgentFactory:
        """Get the agent factory."""
        if not self._agent_factory:
            self.initialize()
        return self._agent_factory
    
    @property
    def router(self) -> AgentRouter:
        """Get the agent router."""
        if not self._router:
            self.initialize()
        return self._router
    
    def create_project(self, name: str, description: str = "") -> Session:
        """
        Create a new game development session.
        
        Args:
            name: Project name
            description: Optional project description
            
        Returns:
            New session instance
        """
        self.initialize()
        
        session = self.session_manager.create_session(name, description)
        logger.info(f"Created new project session: {session.id} - {name}")
        
        return session
    
    def load_session(self, session_id: str) -> Session:
        """
        Load an existing session.
        
        Args:
            session_id: ID of session to load
            
        Returns:
            Loaded session instance
        """
        self.initialize()
        
        session = self.session_manager.load(session_id)
        logger.info(f"Loaded session: {session_id}")
        
        return session
    
    def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved sessions."""
        self.initialize()
        return self.session_manager.list_sessions()
    
    async def execute(
        self,
        user_input: str,
        session: Session | None = None,
        agent_name: str | None = None,
    ) -> AgentResponse:
        """
        Execute a task with the appropriate agent.
        
        Args:
            user_input: Natural language instruction
            session: Session to use (uses current if not provided)
            agent_name: Force specific agent (auto-routes if not provided)
            
        Returns:
            Agent response
        """
        self.initialize()
        
        # Get or create session
        if session is None:
            session = self.session_manager.current
            if session is None:
                raise ValueError("No active session. Create a project first.")
        
        # Record user message
        session.add_message("human", user_input)
        
        # Determine which agent to use
        if agent_name:
            if agent_name not in self.router.agents:
                raise ValueError(f"Unknown agent: {agent_name}")
            task_type = None
        else:
            task_type = self.router.classify_request(user_input, session)
            routing = self.router.route(task_type, session)
            agent_name = routing.agent_name
            logger.info(f"Routed to {agent_name} for task type: {task_type}")
        
        # Get agent and execute
        agent = self.router.agents[agent_name]
        
        # Build context from session
        context = {
            "project": session.project.model_dump(),
            "game_design_doc": session.project.game_design_doc,
            "technical_spec": session.project.technical_spec,
            "art_spec": session.project.art_spec,
        }
        
        # Get conversation history in LLM format
        history = [
            {"role": "user" if msg.role == "human" else "assistant", "content": msg.content}
            for msg in session.get_recent_history(10)
            if msg.role in ("human", "agent")
        ][:-1]  # Exclude the message we just added
        
        # Execute agent
        logger.info(f"Executing {agent_name} agent")
        response = await agent.execute(user_input, context, history)
        
        # Record agent response
        session.add_message(
            "agent",
            response.content,
            agent_name=agent_name,
            metadata={"artifacts": response.artifacts},
        )
        
        # Save session
        self.session_manager.save(session)
        
        return response
    
    def execute_sync(
        self,
        user_input: str,
        session: Session | None = None,
        agent_name: str | None = None,
    ) -> AgentResponse:
        """Synchronous wrapper for execute()."""
        return asyncio.run(self.execute(user_input, session, agent_name))
    
    async def new_project_flow(
        self,
        name: str,
        description: str = "",
        initial_prompt: str | None = None,
    ) -> tuple[Session, AgentResponse | None]:
        """
        Create a new project and optionally run initial architect consultation.
        
        Args:
            name: Project name
            description: Project description
            initial_prompt: Optional prompt to send to Architect
            
        Returns:
            Tuple of (session, architect_response or None)
        """
        self.initialize()
        
        # Create session
        session = self.create_project(name, description)
        
        # If initial prompt provided, consult architect
        response = None
        if initial_prompt:
            response = await self.execute(initial_prompt, session, agent_name="architect")
        
        return session, response
    
    def get_session_status(self, session: Session | None = None) -> dict[str, Any]:
        """
        Get status information for a session.
        
        Args:
            session: Session to check (uses current if not provided)
            
        Returns:
            Status dictionary
        """
        self.initialize()
        
        if session is None:
            session = self.session_manager.current
        
        if session is None:
            return {"active": False, "message": "No active session"}
        
        return {
            "active": True,
            "session_id": session.id,
            "project_name": session.project.name,
            "project_description": session.project.description,
            "current_phase": session.project.current_phase,
            "message_count": len(session.history),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "completed_tasks": session.project.completed_tasks,
            "pending_tasks": session.project.pending_tasks,
        }
