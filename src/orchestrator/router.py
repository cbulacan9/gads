"""
Agent Router for GADS

Routes tasks to appropriate agents based on task type and context.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from ..agents.base import BaseAgent
    from .session import Session


class TaskType(str, Enum):
    """Types of tasks that can be routed to agents."""
    
    # Architect tasks
    GAME_CONCEPT = "game_concept"
    SYSTEM_DESIGN = "system_design"
    ARCHITECTURE = "architecture"
    CREATIVE_DIRECTION = "creative_direction"
    
    # Designer tasks
    MECHANIC_DESIGN = "mechanic_design"
    LEVEL_DESIGN = "level_design"
    BALANCING = "balancing"
    
    # Developer tasks
    IMPLEMENT_FEATURE = "implement_feature"
    CREATE_SCENE = "create_scene"
    WRITE_SCRIPT = "write_script"
    DEBUG = "debug"
    
    # Art Director tasks
    VISUAL_STYLE = "visual_style"
    ASSET_SPEC = "asset_spec"
    PROMPT_ENGINEERING = "prompt_engineering"
    
    # QA tasks
    TEST = "test"
    VALIDATE = "validate"
    REVIEW = "review"


class RoutingDecision(BaseModel):
    """Result of routing a task."""
    
    agent_name: str
    task_type: TaskType
    priority: int = 0
    context: dict[str, Any] = {}
    requires_human_approval: bool = False


class AgentRouter:
    """Routes tasks to the appropriate agent."""
    
    # Mapping of task types to agent names
    TASK_AGENT_MAP: dict[TaskType, str] = {
        TaskType.GAME_CONCEPT: "architect",
        TaskType.SYSTEM_DESIGN: "architect",
        TaskType.ARCHITECTURE: "architect",
        TaskType.CREATIVE_DIRECTION: "architect",
        
        TaskType.MECHANIC_DESIGN: "designer",
        TaskType.LEVEL_DESIGN: "designer",
        TaskType.BALANCING: "designer",
        
        TaskType.IMPLEMENT_FEATURE: "developer",
        TaskType.CREATE_SCENE: "developer",
        TaskType.WRITE_SCRIPT: "developer",
        TaskType.DEBUG: "developer",
        
        TaskType.VISUAL_STYLE: "art_director",
        TaskType.ASSET_SPEC: "art_director",
        TaskType.PROMPT_ENGINEERING: "art_director",
        
        TaskType.TEST: "qa",
        TaskType.VALIDATE: "qa",
        TaskType.REVIEW: "qa",
    }
    
    # Tasks that require human approval before execution
    APPROVAL_REQUIRED: set[TaskType] = {
        TaskType.GAME_CONCEPT,
        TaskType.ARCHITECTURE,
        TaskType.VISUAL_STYLE,
    }
    
    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
    
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register an agent with the router."""
        self.agents[name] = agent
    
    def route(
        self,
        task_type: TaskType,
        session: Session,
        context: dict[str, Any] | None = None,
    ) -> RoutingDecision:
        """Route a task to the appropriate agent."""
        agent_name = self.TASK_AGENT_MAP.get(task_type)
        
        if not agent_name:
            raise ValueError(f"Unknown task type: {task_type}")
        
        if agent_name not in self.agents:
            raise ValueError(f"Agent not registered: {agent_name}")
        
        return RoutingDecision(
            agent_name=agent_name,
            task_type=task_type,
            context=context or {},
            requires_human_approval=task_type in self.APPROVAL_REQUIRED,
        )
    
    def classify_request(self, user_input: str, session: Session) -> TaskType:
        """
        Classify a user request into a task type.
        
        This is a simple keyword-based classifier. In production,
        this could use an LLM for more nuanced classification.
        """
        input_lower = user_input.lower()
        
        # Architecture/Concept keywords
        if any(kw in input_lower for kw in ["concept", "idea", "game about", "design a game"]):
            return TaskType.GAME_CONCEPT
        if any(kw in input_lower for kw in ["architecture", "system design", "structure"]):
            return TaskType.ARCHITECTURE
        
        # Design keywords
        if any(kw in input_lower for kw in ["mechanic", "gameplay", "ability"]):
            return TaskType.MECHANIC_DESIGN
        if any(kw in input_lower for kw in ["level", "map", "environment"]):
            return TaskType.LEVEL_DESIGN
        if any(kw in input_lower for kw in ["balance", "difficulty", "tuning"]):
            return TaskType.BALANCING
        
        # Development keywords
        if any(kw in input_lower for kw in ["implement", "code", "create feature"]):
            return TaskType.IMPLEMENT_FEATURE
        if any(kw in input_lower for kw in ["scene", "node"]):
            return TaskType.CREATE_SCENE
        if any(kw in input_lower for kw in ["script", "gdscript"]):
            return TaskType.WRITE_SCRIPT
        if any(kw in input_lower for kw in ["bug", "fix", "debug", "error"]):
            return TaskType.DEBUG
        
        # Art keywords
        if any(kw in input_lower for kw in ["visual", "style", "art direction"]):
            return TaskType.VISUAL_STYLE
        if any(kw in input_lower for kw in ["asset", "sprite", "model", "texture"]):
            return TaskType.ASSET_SPEC
        
        # QA keywords
        if any(kw in input_lower for kw in ["test", "verify"]):
            return TaskType.TEST
        if any(kw in input_lower for kw in ["review", "check"]):
            return TaskType.REVIEW
        
        # Default to game concept for new projects
        return TaskType.GAME_CONCEPT
