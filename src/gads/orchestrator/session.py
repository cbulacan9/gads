"""
Session Management for GADS

Handles conversation history, project state, and persistence.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


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
    
    # Project-level settings (set once at creation)
    project_type: str = "2d"  # "2d" or "3d"
    art_style: str = ""       # e.g., "pixel-art", "low-poly", "realistic"
    
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
    
    # Track how many messages have been truncated
    truncated_message_count: int = 0
    
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
    
    def truncate_history(self, max_messages: int) -> int:
        """
        Truncate history to keep only the most recent messages.
        
        Args:
            max_messages: Maximum number of messages to retain
            
        Returns:
            Number of messages removed
        """
        if len(self.history) <= max_messages:
            return 0
        
        remove_count = len(self.history) - max_messages
        self.history = self.history[-max_messages:]
        self.truncated_message_count += remove_count
        
        return remove_count


class SessionManager:
    """Manages session persistence and retrieval."""
    
    def __init__(self, session_dir: Path, max_history: int = 100):
        """
        Initialize the session manager.
        
        Args:
            session_dir: Directory for storing session files
            max_history: Maximum messages to retain in history (default 100)
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.max_history = max_history
        self._current_session: Session | None = None
    
    @property
    def current(self) -> Session | None:
        """Get the current active session."""
        return self._current_session
    
    def create_session(
        self,
        project_name: str,
        description: str = "",
        project_type: str = "2d",
        art_style: str = "",
    ) -> Session:
        """Create a new development session.
        
        Args:
            project_name: Name of the project
            description: Project description
            project_type: "2d" or "3d" (default: "2d")
            art_style: Art style hint (e.g., "pixel-art", "low-poly")
        """
        project = ProjectState(
            name=project_name,
            description=description,
            project_type=project_type,
            art_style=art_style,
        )
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
        """
        Save a session to disk.
        
        Automatically truncates history if it exceeds max_history,
        logging a warning when truncation occurs.
        """
        session = session or self._current_session
        if not session:
            raise ValueError("No session to save")
        
        # Truncate history if needed
        removed = session.truncate_history(self.max_history)
        if removed > 0:
            logger.warning(
                f"Session {session.id}: Truncated {removed} old messages. "
                f"Total truncated: {session.truncated_message_count}. "
                f"Consider increasing max_session_history or implementing "
                f"a different persistence strategy for long-running sessions."
            )
        
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
                "message_count": len(data.get("history", [])),
                "truncated_count": data.get("truncated_message_count", 0),
            })
        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)
