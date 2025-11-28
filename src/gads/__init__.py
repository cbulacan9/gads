"""
GADS - Godot Agentic Development System

A multi-agent AI framework for automated Godot game development.
"""

__version__ = "0.2.0"
__author__ = "Christian"

from .orchestrator import (
    Orchestrator,
    Session,
    SessionManager,
    Pipeline,
    PipelineResult,
    TaskType,
)
from .agents import (
    AgentFactory,
    AgentResponse,
    BaseAgent,
)

__all__ = [
    "__version__",
    "Orchestrator",
    "Session",
    "SessionManager",
    "Pipeline",
    "PipelineResult",
    "TaskType",
    "AgentFactory",
    "AgentResponse",
    "BaseAgent",
]
