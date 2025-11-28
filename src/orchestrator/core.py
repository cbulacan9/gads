"""
Orchestrator Core for GADS

Central coordinator that ties together agents, sessions, routing, and pipelines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..agents import AgentFactory, AgentResponse, BaseAgent
from ..utils import Settings, load_settings, get_logger
from .session import Session, SessionManager, Message
from .router import AgentRouter, TaskType, RoutingDecision
from .pipeline import Pipeline, PipelineResult, PipelineStatus

logger = get_logger(__name__)


class Orchestrator:
    """
    Central coordinator for the GADS system.
    
    Ties together agent creation, session management, request routing,
    and pipeline execution into a cohesive interface.
    """
    
    def __init__(
        self,
        settings: Settings | None = None,
        config_dir: Path | str | None = None,
        approval_callback: Callable[[str, RoutingDecision], bool] | None = None,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            settings: Application settings (loads from .env if not provided)
            config_dir: Directory containing config/ and prompts/ (auto-detected if not provided)
            approval_callback: Optional callback for human approval gates.
                               Receives (message, decision) and returns True to proceed.
        """
        self.settings = settings or load_settings()
        self.config_dir = self._resolve_config_dir(config_dir)
        self.approval_callback = approval_callback or self._default_approval
        
        # Initialize components
        self.session_manager = SessionManager(
            self.settings.session_dir,
            max_history=self.settings.max_session_history,
        )
        self.factory = self._create_factory()
        self.agents = self.factory.create_all_agents()
        self.router = self._create_router()
        
        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")
    
    def _resolve_config_dir(self, config_dir: Path | str | None) -> Path:
        """Resolve the configuration directory."""
        if config_dir:
            return Path(config_dir)
        
        # Try to find config dir relative to package
        # Walk up from this file to find project root
        current = Path(__file__).parent
        for _ in range(5):  # Max 5 levels up
            if (current / "config").exists():
                return current
            current = current.parent
        
        # Fallback to current working directory
        return Path.cwd()
    
    def _create_factory(self) -> AgentFactory:
        """Create and configure the agent factory."""
        config_path = self.config_dir / "config" / "agents.yaml"
        prompts_dir = self.config_dir / "prompts"
        
        api_keys = {}
        if self.settings.anthropic_api_key:
            api_keys["anthropic"] = self.settings.anthropic_api_key
        
        factory = AgentFactory(
            config_path=config_path,
            prompts_dir=prompts_dir,
            api_keys=api_keys,
        )
        
        return factory
    
    def _create_router(self) -> AgentRouter:
        """Create and configure the agent router."""
        router = AgentRouter()
        router.register_agents(self.agents)
        return router
    
    def _default_approval(self, message: str, decision: RoutingDecision) -> bool:
        """Default approval callback - always approves."""
        logger.debug(f"Auto-approving: {message}")
        return True
    
    def get_session(self, session_id: str | None = None) -> Session | None:
        """
        Get a session by ID or return the current session.
        
        Args:
            session_id: Session ID to load, or None for current session
            
        Returns:
            Session if found, None otherwise
        """
        if session_id:
            try:
                return self.session_manager.load(session_id)
            except FileNotFoundError:
                logger.warning(f"Session not found: {session_id}")
                return None
        return self.session_manager.current
    
    def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved sessions."""
        return self.session_manager.list_sessions()
    
    def new_project(
        self,
        name: str,
        description: str = "",
        run_architect: bool = True,
    ) -> Session:
        """
        Create a new project session.
        
        Args:
            name: Project name
            description: Project description
            run_architect: Whether to immediately run the architect agent
            
        Returns:
            The new session
        """
        session = self.session_manager.create_session(name, description)
        logger.info(f"Created new project: {name} (session: {session.id})")
        
        return session
    
    async def run(
        self,
        user_input: str,
        session: Session | None = None,
        session_id: str | None = None,
        task_type: TaskType | None = None,
        allow_chaining: bool = True,
        max_chain_depth: int = 3,
    ) -> AgentResponse:
        """
        Run a single agent interaction.
        
        Args:
            user_input: The user's request
            session: Session to use (creates new if not provided)
            session_id: Session ID to load (alternative to session)
            task_type: Override automatic task classification
            allow_chaining: Whether to follow suggested_next_agent
            max_chain_depth: Maximum number of chained agent calls
            
        Returns:
            The agent's response
        """
        # Resolve session
        if session is None:
            if session_id:
                session = self.session_manager.load(session_id)
            elif self.session_manager.current:
                session = self.session_manager.current
            else:
                session = self.session_manager.create_session("Untitled Project")
        
        # Record user input
        session.add_message("human", user_input)
        
        # Classify request if not provided
        if task_type is None:
            task_type = self.router.classify_request(user_input, session)
        
        logger.info(f"Classified request as: {task_type.value}")
        
        # Route to agent
        decision = self.router.route(task_type, session)
        
        # Check for approval if required
        if decision.requires_human_approval:
            approval_msg = f"Task '{task_type.value}' requires approval. Proceed with {decision.agent_name}?"
            if not self.approval_callback(approval_msg, decision):
                response = AgentResponse(
                    content="Task cancelled by user.",
                    agent_name="system",
                    model="",
                )
                session.add_message("system", response.content)
                self.session_manager.save(session)
                return response
        
        # Execute agent
        response = await self._execute_agent(decision, user_input, session)
        
        # Record response
        session.add_message(
            "agent",
            response.content,
            agent_name=response.agent_name,
            metadata={"artifacts": response.artifacts},
        )
        
        # Handle chaining
        if (
            allow_chaining
            and response.suggested_next_agent
            and max_chain_depth > 0
            and response.suggested_task
        ):
            logger.info(f"Chaining to {response.suggested_next_agent}: {response.suggested_task}")
            
            # Find the task type for the suggested agent
            next_task_type = self._infer_task_type_for_agent(
                response.suggested_next_agent, 
                response.suggested_task,
                session
            )
            
            if next_task_type:
                chain_response = await self.run(
                    response.suggested_task,
                    session=session,
                    task_type=next_task_type,
                    allow_chaining=True,
                    max_chain_depth=max_chain_depth - 1,
                )
                # Combine responses
                response = AgentResponse(
                    content=f"{response.content}\n\n---\n\n**{chain_response.agent_name}:**\n{chain_response.content}",
                    agent_name=response.agent_name,
                    model=response.model,
                    artifacts={**response.artifacts, **chain_response.artifacts},
                )
        
        # Save session
        self.session_manager.save(session)
        
        return response
    
    async def _execute_agent(
        self,
        decision: RoutingDecision,
        user_input: str,
        session: Session,
    ) -> AgentResponse:
        """Execute an agent based on a routing decision."""
        agent = self.agents.get(decision.agent_name)
        
        if not agent:
            raise ValueError(f"Agent not found: {decision.agent_name}")
        
        # Build context for agent
        context = self._build_agent_context(session, agent)
        context.update(decision.context)
        
        # Get conversation history in the format agents expect
        history = self._build_history_for_agent(session, agent)
        
        logger.debug(f"Executing {decision.agent_name} with context keys: {list(context.keys())}")
        
        response = await agent.execute(user_input, context, history)
        
        return response
    
    def _build_agent_context(self, session: Session, agent: BaseAgent) -> dict[str, Any]:
        """Build context dictionary for an agent."""
        context = {
            "project": {
                "name": session.project.name,
                "description": session.project.description,
                "godot_version": session.project.godot_version,
                "current_phase": session.project.current_phase,
            },
            "game_design_doc": session.project.game_design_doc,
            "technical_spec": session.project.technical_spec,
            "art_spec": session.project.art_spec,
        }
        
        # Add agent-specific context
        agent_context = session.get_agent_context(agent.name)
        if agent_context:
            context["agent_memory"] = agent_context
        
        return context
    
    def _build_history_for_agent(
        self,
        session: Session,
        agent: BaseAgent,
        max_messages: int = 10,
    ) -> list[dict[str, str]]:
        """Build conversation history in the format agents expect."""
        history = []
        
        for msg in session.get_recent_history(max_messages):
            if msg.role == "human":
                history.append({"role": "user", "content": msg.content})
            elif msg.role == "agent":
                history.append({"role": "assistant", "content": msg.content})
        
        return history
    
    def _infer_task_type_for_agent(
        self,
        agent_name: str,
        task_description: str,
        session: Session,
    ) -> TaskType | None:
        """Infer the task type for a given agent and task description."""
        # Map agent names to their primary task types
        agent_primary_tasks = {
            "architect": TaskType.ARCHITECTURE,
            "designer": TaskType.MECHANIC_DESIGN,
            "developer_2d": TaskType.IMPLEMENT_FEATURE_2D,
            "developer_3d": TaskType.IMPLEMENT_FEATURE_3D,
            "art_director": TaskType.VISUAL_STYLE,
            "qa": TaskType.REVIEW,
        }
        
        return agent_primary_tasks.get(agent_name)
    
    async def run_pipeline(
        self,
        pipeline: Pipeline,
        session: Session | None = None,
        initial_input: str = "",
        initial_context: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """
        Execute a multi-agent pipeline.
        
        Args:
            pipeline: The pipeline to execute
            session: Session to use (creates new if not provided)
            initial_input: Initial user input for the first step
            initial_context: Initial context values
            
        Returns:
            PipelineResult with outputs and status
        """
        # Resolve session
        if session is None:
            if self.session_manager.current:
                session = self.session_manager.current
            else:
                session = self.session_manager.create_session("Pipeline Execution")
        
        context = initial_context.copy() if initial_context else {}
        context["user_input"] = initial_input
        
        result = PipelineResult(status=PipelineStatus.RUNNING)
        
        logger.info(f"Starting pipeline: {pipeline.name} ({len(pipeline.steps)} steps)")
        
        for step in pipeline.steps:
            result.current_step = step.name
            
            # Check condition
            if not step.should_execute(context):
                logger.debug(f"Skipping step {step.name} (condition not met)")
                continue
            
            logger.info(f"Executing pipeline step: {step.name}")
            
            try:
                # Get input for this step
                if step.input_key and step.input_key in context:
                    step_input = context[step.input_key]
                else:
                    step_input = context.get("user_input", "")
                
                # Route and execute
                task_type = TaskType(step.task_type)
                decision = self.router.route(task_type, session, context)
                
                # Check for approval
                if decision.requires_human_approval:
                    approval_msg = f"Pipeline step '{step.name}' requires approval. Proceed?"
                    if not self.approval_callback(approval_msg, decision):
                        result.status = PipelineStatus.CANCELLED
                        result.error = f"Step '{step.name}' cancelled by user"
                        return result
                
                # Execute agent
                response = await self._execute_agent(decision, str(step_input), session)
                
                # Store output
                if step.output_key:
                    context[step.output_key] = response.content
                    if response.artifacts:
                        context[f"{step.output_key}_artifacts"] = response.artifacts
                
                # Record in session
                session.add_message(
                    "agent",
                    response.content,
                    agent_name=response.agent_name,
                    metadata={"pipeline_step": step.name, "artifacts": response.artifacts},
                )
                
                result.completed_steps.append(step.name)
                
            except Exception as e:
                logger.error(f"Pipeline step '{step.name}' failed: {e}")
                result.status = PipelineStatus.FAILED
                result.error = f"Step '{step.name}' failed: {str(e)}"
                self.session_manager.save(session)
                return result
        
        result.status = PipelineStatus.COMPLETED
        result.current_step = None
        result.outputs = context
        
        # Save session
        self.session_manager.save(session)
        
        logger.info(f"Pipeline '{pipeline.name}' completed successfully")
        
        return result
