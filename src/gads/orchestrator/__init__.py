"""
GADS Orchestrator Module

Core orchestration logic for managing agent interactions and session state.
"""

from .session import Session, SessionManager, Message, ProjectState
from .router import AgentRouter, TaskType, RoutingDecision, ProjectType
from .pipeline import Pipeline, PipelineResult, PipelineStatus, PipelineStep
from .registry import PipelineRegistry
from .core import Orchestrator, PipelineEvent

__all__ = [
    # Core
    "Orchestrator",
    "PipelineEvent",
    # Session
    "Session",
    "SessionManager",
    "Message",
    "ProjectState",
    # Router
    "AgentRouter",
    "TaskType",
    "RoutingDecision",
    "ProjectType",
    # Pipeline
    "Pipeline",
    "PipelineResult",
    "PipelineStatus",
    "PipelineStep",
    "PipelineRegistry",
]
