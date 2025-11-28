"""
Agent Router for GADS

Routes tasks to appropriate agents based on LLM classification.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING, Any

import aiohttp
from pydantic import BaseModel

if TYPE_CHECKING:
    from ..agents.base import BaseAgent
    from .session import Session


logger = logging.getLogger(__name__)


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


# Classification prompt for the router LLM
CLASSIFICATION_SYSTEM_PROMPT = """You are a task classifier for a Godot game development system. Your job is to analyze user requests and classify them into the correct task type.

Available task types and when to use them:

ARCHITECT TASKS (high-level design, uses Claude):
- game_concept: New game ideas, "I want to make a game about...", initial concepts
- system_design: Overall system architecture, how components interact
- architecture: Technical structure, scene organization, autoloads
- creative_direction: Theme, tone, overall vision

DESIGNER TASKS (mechanics and levels):
- mechanic_design: Gameplay mechanics, abilities, controls, player actions
- level_design: Level layouts, environments, world design
- balancing: Difficulty tuning, number tweaking, progression curves

DEVELOPER TASKS - 2D (code for 2D games):
- implement_feature_2d: Implement/code features for 2D games
- create_scene_2d: Create 2D scenes, node hierarchies
- write_script_2d: Write GDScript for 2D (CharacterBody2D, Sprite2D, etc.)
- debug_2d: Fix bugs in 2D code

DEVELOPER TASKS - 3D (code for 3D games):
- implement_feature_3d: Implement/code features for 3D games
- create_scene_3d: Create 3D scenes, node hierarchies
- write_script_3d: Write GDScript for 3D (CharacterBody3D, MeshInstance3D, etc.)
- debug_3d: Fix bugs in 3D code

ART DIRECTOR TASKS (visuals, uses Claude):
- visual_style: Art direction, color palettes, aesthetic choices
- asset_spec: Asset specifications, dimensions, formats
- prompt_engineering: Creating prompts for Stable Diffusion or image generation

QA TASKS (testing and review):
- test: Write tests, test scenarios, verify functionality
- validate: Check implementation matches design
- review: Code review, quality checks

IMPORTANT RULES:
1. For developer tasks, choose 2D or 3D based on context clues:
   - Mentions of Sprite2D, CharacterBody2D, TileMap, Camera2D → use 2D variants
   - Mentions of MeshInstance3D, CharacterBody3D, Camera3D → use 3D variants
   - If project_type is provided, use that as default
   - If unclear, default to 2D

2. "Implement", "code", "create", "write" with code context → developer tasks
3. "Design" without code context → designer or architect tasks
4. Bug fixes, errors, debugging → debug tasks
5. New game ideas with no existing project → game_concept

Respond with ONLY the task type (e.g., "game_concept" or "implement_feature_2d"). No explanation."""


class AgentRouter:
    """Routes tasks to the appropriate agent using LLM-based classification."""
    
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
    
    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        classifier_model: str = "qwen2.5-coder:14b",
    ):
        """
        Initialize the router.
        
        Args:
            ollama_base_url: Base URL for Ollama API
            classifier_model: Model to use for classification (default: qwen2.5-coder:14b)
        """
        self.ollama_base_url = ollama_base_url
        self.classifier_model = classifier_model
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
    
    async def classify_request(self, user_input: str, session: Session) -> TaskType:
        """
        Classify a user request into a task type using LLM.
        
        Args:
            user_input: The user's request
            session: Current session for context
            
        Returns:
            The classified TaskType
        """
        # Build context for classifier
        project_type = self.get_project_type(session)
        context_parts = [
            f"Project: {session.project.name}",
            f"Project Type: {project_type.value}",
            f"Current Phase: {session.project.current_phase}",
        ]
        
        if session.project.description:
            context_parts.append(f"Description: {session.project.description}")
        
        # Include recent history for context
        recent_messages = session.get_recent_history(3)
        if recent_messages:
            history_summary = "\n".join(
                f"- {msg.role}: {msg.content[:100]}..." 
                if len(msg.content) > 100 else f"- {msg.role}: {msg.content}"
                for msg in recent_messages
            )
            context_parts.append(f"Recent conversation:\n{history_summary}")
        
        context_str = "\n".join(context_parts)
        
        # Build the classification prompt
        user_message = f"""Context:
{context_str}

User request to classify:
{user_input}

Task type:"""

        try:
            # Call Ollama for classification
            task_type_str = await self._call_classifier(user_message)
            task_type_str = task_type_str.strip().lower()
            
            # Validate and parse response
            try:
                task_type = TaskType(task_type_str)
                logger.info(f"LLM classified request as: {task_type.value}")
                return task_type
            except ValueError:
                logger.warning(
                    f"LLM returned invalid task type: '{task_type_str}'. "
                    f"Falling back to keyword classification."
                )
                return self._keyword_fallback(user_input, session)
                
        except Exception as e:
            logger.error(f"LLM classification failed: {e}. Falling back to keywords.")
            return self._keyword_fallback(user_input, session)
    
    async def _call_classifier(self, user_message: str) -> str:
        """Call Ollama for classification."""
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": self.classifier_model,
                    "messages": [
                        {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent classification
                        "num_predict": 50,   # Short response expected
                    },
                },
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama API error: {response.status}")
                data = await response.json()
                return data["message"]["content"]
    
    def _keyword_fallback(self, user_input: str, session: Session) -> TaskType:
        """
        Fallback keyword-based classification.
        
        Used when LLM classification fails or returns invalid results.
        """
        input_lower = user_input.lower()
        project_type = self.get_project_type(session)
        is_3d = project_type == ProjectType.PROJECT_3D
        
        # Architecture/Concept keywords
        if any(kw in input_lower for kw in ["concept", "idea", "game about", "design a game", "new game"]):
            return TaskType.GAME_CONCEPT
        if any(kw in input_lower for kw in ["architecture", "system design", "structure"]):
            return TaskType.ARCHITECTURE
        
        # Design keywords
        if any(kw in input_lower for kw in ["mechanic", "gameplay", "ability", "control"]):
            return TaskType.MECHANIC_DESIGN
        if any(kw in input_lower for kw in ["level", "map", "environment", "world"]):
            return TaskType.LEVEL_DESIGN
        if any(kw in input_lower for kw in ["balance", "difficulty", "tuning"]):
            return TaskType.BALANCING
        
        # Check explicit 3D/2D keywords BEFORE general development keywords
        # This ensures "CharacterBody3D script" routes to 3D, not 2D
        
        # Explicit 3D keywords override project type
        if any(kw in input_lower for kw in ["3d", "mesh", "camera3d", "characterbody3d"]):
            if any(kw in input_lower for kw in ["implement", "code", "feature"]):
                return TaskType.IMPLEMENT_FEATURE_3D
            if any(kw in input_lower for kw in ["scene", "node"]):
                return TaskType.CREATE_SCENE_3D
            if any(kw in input_lower for kw in ["script", "gdscript"]):
                return TaskType.WRITE_SCRIPT_3D
            if any(kw in input_lower for kw in ["bug", "fix", "debug"]):
                return TaskType.DEBUG_3D
            # Default to implement for 3D context
            return TaskType.IMPLEMENT_FEATURE_3D
        
        # Explicit 2D keywords
        if any(kw in input_lower for kw in ["2d", "sprite", "camera2d", "characterbody2d", "tilemap"]):
            if any(kw in input_lower for kw in ["implement", "code", "feature"]):
                return TaskType.IMPLEMENT_FEATURE_2D
            if any(kw in input_lower for kw in ["scene", "node"]):
                return TaskType.CREATE_SCENE_2D
            if any(kw in input_lower for kw in ["script", "gdscript"]):
                return TaskType.WRITE_SCRIPT_2D
            if any(kw in input_lower for kw in ["bug", "fix", "debug"]):
                return TaskType.DEBUG_2D
            # Default to implement for 2D context
            return TaskType.IMPLEMENT_FEATURE_2D
        
        # General development keywords (use project type as default)
        if any(kw in input_lower for kw in ["implement", "code", "create feature", "add feature"]):
            return TaskType.IMPLEMENT_FEATURE_3D if is_3d else TaskType.IMPLEMENT_FEATURE_2D
        if any(kw in input_lower for kw in ["scene", "node"]):
            return TaskType.CREATE_SCENE_3D if is_3d else TaskType.CREATE_SCENE_2D
        if any(kw in input_lower for kw in ["script", "gdscript"]):
            return TaskType.WRITE_SCRIPT_3D if is_3d else TaskType.WRITE_SCRIPT_2D
        if any(kw in input_lower for kw in ["bug", "fix", "debug", "error"]):
            return TaskType.DEBUG_3D if is_3d else TaskType.DEBUG_2D
        
        # Art keywords
        if any(kw in input_lower for kw in ["visual", "style", "art direction", "look and feel"]):
            return TaskType.VISUAL_STYLE
        if any(kw in input_lower for kw in ["asset", "sprite", "model", "texture"]):
            return TaskType.ASSET_SPEC
        if any(kw in input_lower for kw in ["prompt", "stable diffusion", "generate image"]):
            return TaskType.PROMPT_ENGINEERING
        
        # QA keywords
        if any(kw in input_lower for kw in ["test", "verify"]):
            return TaskType.TEST
        if any(kw in input_lower for kw in ["review", "check", "validate"]):
            return TaskType.REVIEW
        
        # Default to game concept for new/unclear requests
        return TaskType.GAME_CONCEPT
