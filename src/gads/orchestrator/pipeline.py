"""
Pipeline Module for GADS

Defines multi-agent pipelines for complex workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .router import AgentRouter, TaskType
    from .session import Session


class PipelineStatus(str, Enum):
    """Status of a pipeline execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineStep:
    """A single step in a pipeline."""
    
    name: str
    task_type: str  # TaskType as string
    input_key: str | None = None  # Key to read input from context
    output_key: str | None = None  # Key to store output in context
    condition: Callable[[dict[str, Any]], bool] | None = None  # Optional condition
    
    def should_execute(self, context: dict[str, Any]) -> bool:
        """Check if this step should execute based on condition."""
        if self.condition is None:
            return True
        return self.condition(context)


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    
    status: PipelineStatus
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    completed_steps: list[str] = field(default_factory=list)
    current_step: str | None = None


class Pipeline:
    """
    A multi-step pipeline that orchestrates multiple agents.
    
    Pipelines define workflows where output from one agent
    becomes input to the next.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: list[PipelineStep] = []
    
    def add_step(
        self,
        name: str,
        task_type: str,
        input_key: str | None = None,
        output_key: str | None = None,
        condition: Callable[[dict[str, Any]], bool] | None = None,
    ) -> Pipeline:
        """Add a step to the pipeline. Returns self for chaining."""
        step = PipelineStep(
            name=name,
            task_type=task_type,
            input_key=input_key,
            output_key=output_key,
            condition=condition,
        )
        self.steps.append(step)
        return self
    
    async def execute(
        self,
        router: AgentRouter,
        session: Session,
        initial_context: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """
        Execute the pipeline.
        
        This is a placeholder - full implementation will handle
        agent invocation, context passing, and error handling.
        """
        context = initial_context or {}
        result = PipelineResult(status=PipelineStatus.RUNNING)
        
        for step in self.steps:
            result.current_step = step.name
            
            if not step.should_execute(context):
                continue
            
            try:
                # TODO: Implement actual agent invocation
                # decision = router.route(TaskType(step.task_type), session, context)
                # agent = router.agents[decision.agent_name]
                # output = await agent.execute(...)
                
                result.completed_steps.append(step.name)
                
            except Exception as e:
                result.status = PipelineStatus.FAILED
                result.error = str(e)
                return result
        
        result.status = PipelineStatus.COMPLETED
        result.current_step = None
        result.outputs = context
        return result


# Pre-defined pipelines

def create_new_game_pipeline() -> Pipeline:
    """Pipeline for creating a new game from concept."""
    return (
        Pipeline("new_game", "Create a new game from concept")
        .add_step("concept", "game_concept", output_key="concept")
        .add_step("architecture", "architecture", input_key="concept", output_key="architecture")
        .add_step("visual_style", "visual_style", input_key="concept", output_key="art_style")
        .add_step("initial_mechanics", "mechanic_design", input_key="concept", output_key="mechanics")
    )


def create_feature_pipeline() -> Pipeline:
    """Pipeline for implementing a new feature."""
    return (
        Pipeline("new_feature", "Implement a new game feature")
        .add_step("design", "mechanic_design", output_key="design")
        .add_step("implement", "implement_feature", input_key="design", output_key="code")
        .add_step("test", "test", input_key="code", output_key="test_results")
    )


def create_asset_pipeline() -> Pipeline:
    """Pipeline for creating game assets."""
    return (
        Pipeline("new_asset", "Create a new game asset")
        .add_step("spec", "asset_spec", output_key="spec")
        .add_step("prompt", "prompt_engineering", input_key="spec", output_key="prompts")
        # Asset generation steps would follow
    )
