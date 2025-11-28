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
    
    # Developer tasks (2D)
    IMPLEMENT_FEATURE_2D = "implement_feature_2d"
    CREATE_SCENE_2D = "create_scene_2d"
    WRITE_SCRIPT_2D = "write_script_2d"
    DEBUG_2D = "debug_2d"
    
    # Developer tasks (3D)
    IMPLEMENT_FEATURE_3D = "implement_feature_3d"
    CREATE_SCENE_3D = "create_scene_3d"
    WRITE_SCRIPT_3D = "write_script_3d"
    DEBUG_3D = "debug_3d"
    
    # Art Director tasks
    VISUAL_STYLE = "visual_style"
    ASSET_SPEC = "asset_spec"
    PROMPT_ENGINEERING = "prompt_engineering"
    
    # QA tasks
    TEST = "test"
    VALIDATE = "validate"
    REVIEW = "review"


class ProjectType(str, Enum):
    """Type of Godot project (2D or 3D)."""
    
    PROJECT_2D = "2d"
    PROJECT_3D = "3d"


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
        
        TaskType.IMPLEMENT_FEATURE_2D: "developer_2d",
        TaskType.CREATE_SCENE_2D: "developer_2d",
        TaskType.WRITE_SCRIPT_2D: "developer_2d",
        TaskType.DEBUG_2D: "developer_2d",
        
        TaskType.IMPLEMENT_FEATURE_3D: "developer_3d",
        TaskType.CREATE_SCENE_3D: "developer_3d",
        TaskType.WRITE_SCRIPT_3D: "developer_3d",
        TaskType.DEBUG_3D: "developer_3d",
        
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
    
    def register_agents(self, agents: dict[str, BaseAgent]) -> None:
        """Register multiple agents with the router."""
        self.agents.update(agents)
    
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
    
    def get_project_type(self, session: Session) -> ProjectType:
        """
        Determine the project type from session context.
        
        Checks session project state for explicit type or infers from content.
        """
        project = session.project
        
        # Check explicit project type in design doc
        if project.game_design_doc:
            doc_type = project.game_design_doc.get("project_type", "").lower()
            if "3d" in doc_type:
                return ProjectType.PROJECT_3D
            if "2d" in doc_type:
                return ProjectType.PROJECT_2D
        
        # Check technical spec
        if project.technical_spec:
            spec_type = project.technical_spec.get("rendering", "").lower()
            if "3d" in spec_type or "forward+" in spec_type:
                return ProjectType.PROJECT_3D
        
        # Check for 3D assets
        if project.assets_3d:
            return ProjectType.PROJECT_3D
        
        # Default to 2D
        return ProjectType.PROJECT_2D
    
    def classify_request(self, user_input: str, session: Session) -> TaskType:
        """
        Classify a user request into a task type.
        
        This is a keyword-based classifier that considers project type
        for developer task routing.
        """
        input_lower = user_input.lower()
        project_type = self.get_project_type(session)
        is_3d = project_type == ProjectType.PROJECT_3D
        
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
        
        # Development keywords - route to appropriate developer based on project type
        if any(kw in input_lower for kw in ["implement", "code", "create feature"]):
            return TaskType.IMPLEMENT_FEATURE_3D if is_3d else TaskType.IMPLEMENT_FEATURE_2D
        if any(kw in input_lower for kw in ["scene", "node"]):
            return TaskType.CREATE_SCENE_3D if is_3d else TaskType.CREATE_SCENE_2D
        if any(kw in input_lower for kw in ["script", "gdscript"]):
            return TaskType.WRITE_SCRIPT_3D if is_3d else TaskType.WRITE_SCRIPT_2D
        if any(kw in input_lower for kw in ["bug", "fix", "debug", "error"]):
            return TaskType.DEBUG_3D if is_3d else TaskType.DEBUG_2D
        
        # Explicit 2D/3D mentions override project type
        if any(kw in input_lower for kw in ["3d", "mesh", "camera3d", "characterbody3d"]):
            if any(kw in input_lower for kw in ["implement", "code", "feature"]):
                return TaskType.IMPLEMENT_FEATURE_3D
            if any(kw in input_lower for kw in ["scene", "node"]):
                return TaskType.CREATE_SCENE_3D
            if any(kw in input_lower for kw in ["script"]):
                return TaskType.WRITE_SCRIPT_3D
        
        if any(kw in input_lower for kw in ["2d", "sprite", "camera2d", "characterbody2d", "tilemap"]):
            if any(kw in input_lower for kw in ["implement", "code", "feature"]):
                return TaskType.IMPLEMENT_FEATURE_2D
            if any(kw in input_lower for kw in ["scene", "node"]):
                return TaskType.CREATE_SCENE_2D
            if any(kw in input_lower for kw in ["script"]):
                return TaskType.WRITE_SCRIPT_2D
        
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
