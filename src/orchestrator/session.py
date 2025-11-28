"""
Session Management for GADS

Handles conversation history, project state, and persistence.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in the conversation history."""
    
    role: str  # "human", "agent", "system"
    agent_name: str | None = None
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectState(BaseModel):
    """Current state of the Godot project being developed."""
    
    name: str
    description: str = ""
    godot_version: str = "4.2"
    project_path: Path | None = None
    
    # Design documents
    game_design_doc: dict[str, Any] = Field(default_factory=dict)
    technical_spec: dict[str, Any] = Field(default_factory=dict)
    art_spec: dict[str, Any] = Field(default_factory=dict)
    
    # Asset tracking
    scenes: list[str] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list)
    assets_2d: list[str] = Field(default_factory=list)
    assets_3d: list[str] = Field(default_factory=list)
    
    # Status
    current_phase: str = "design"
    completed_tasks: list[str] = Field(default_factory=list)
    pending_tasks: list[str] = Field(default_factory=list)


class Session(BaseModel):
    """A development session with full state."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    project: ProjectState
    history: list[Message] = Field(default_factory=list)
    
    # Agent-specific memory/context
    agent_contexts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    
    def add_message(
        self,
        role: str,
        content: str,
        agent_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Add a message to the session history."""
        message = Message(
            role=role,
            agent_name=agent_name,
            content=content,
            metadata=metadata or {},
        )
        self.history.append(message)
        self.updated_at = datetime.now()
        return message
    
    def get_recent_history(self, n: int = 10) -> list[Message]:
        """Get the n most recent messages."""
        return self.history[-n:]
    
    def get_agent_context(self, agent_name: str) -> dict[str, Any]:
        """Get or create context for a specific agent."""
        if agent_name not in self.agent_contexts:
            self.agent_contexts[agent_name] = {}
        return self.agent_contexts[agent_name]


class SessionManager:
    """Manages session persistence and retrieval."""
    
    def __init__(self, session_dir: Path):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._current_session: Session | None = None
    
    @property
    def current(self) -> Session | None:
        """Get the current active session."""
        return self._current_session
    
    def create_session(self, project_name: str, description: str = "") -> Session:
        """Create a new development session."""
        project = ProjectState(name=project_name, description=description)
        session = Session(project=project)
        self._current_session = session
        self.save(session)
        return session
    
    def load(self, session_id: str) -> Session:
        """Load a session from disk."""
        path = self.session_dir / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        
        with open(path) as f:
            data = json.load(f)
        
        session = Session.model_validate(data)
        self._current_session = session
        return session
    
    def save(self, session: Session | None = None) -> None:
        """Save a session to disk."""
        session = session or self._current_session
        if not session:
            raise ValueError("No session to save")
        
        path = self.session_dir / f"{session.id}.json"
        with open(path, "w") as f:
            json.dump(session.model_dump(mode="json"), f, indent=2, default=str)
    
    def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved sessions."""
        sessions = []
        for path in self.session_dir.glob("*.json"):
            with open(path) as f:
                data = json.load(f)
            sessions.append({
                "id": data["id"],
                "project_name": data["project"]["name"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
            })
        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)
