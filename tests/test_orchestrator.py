"""
Tests for GADS Orchestrator
"""

import pytest
from pathlib import Path
from gads.orchestrator.session import Session, SessionManager, ProjectState, Message
from gads.orchestrator.router import AgentRouter, TaskType


class TestProjectState:
    """Tests for ProjectState model."""
    
    def test_project_creation(self):
        """Test creating a project state."""
        project = ProjectState(
            name="Test Game",
            description="A test project",
        )
        
        assert project.name == "Test Game"
        assert project.godot_version == "4.2"
        assert project.current_phase == "design"


class TestSession:
    """Tests for Session model."""
    
    def test_session_creation(self):
        """Test creating a session."""
        project = ProjectState(name="Test Game")
        session = Session(project=project)
        
        assert session.id is not None
        assert session.project.name == "Test Game"
        assert len(session.history) == 0
    
    def test_add_message(self):
        """Test adding messages to session."""
        project = ProjectState(name="Test Game")
        session = Session(project=project)
        
        session.add_message("human", "Create a platformer")
        session.add_message("agent", "I'll design a platformer.", agent_name="architect")
        
        assert len(session.history) == 2
        assert session.history[0].role == "human"
        assert session.history[1].agent_name == "architect"


class TestAgentRouter:
    """Tests for AgentRouter."""
    
    def test_task_classification(self):
        """Test classifying user input to task types."""
        router = AgentRouter()
        project = ProjectState(name="Test")
        session = Session(project=project)
        
        task = router.classify_request("I want to make a game about dragons", session)
        assert task == TaskType.GAME_CONCEPT
        
        task = router.classify_request("Implement the jump mechanic", session)
        assert task == TaskType.IMPLEMENT_FEATURE
        
        task = router.classify_request("Fix this bug in my script", session)
        assert task == TaskType.DEBUG
