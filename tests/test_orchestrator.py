"""
Tests for GADS Orchestrator Core
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from gads.orchestrator import (
    Orchestrator,
    Session,
    TaskType,
    Pipeline,
    PipelineStatus,
)
from gads.agents import AgentResponse


SAMPLE_AGENTS_CONFIG = """
architect:
  name: "architect"
  provider: "ollama"
  model: "llama3.1:8b"
  temperature: 0.7
  max_tokens: 4096

designer:
  name: "designer"
  provider: "ollama"
  model: "llama3.1:8b"
  temperature: 0.7
  max_tokens: 4096

developer_2d:
  name: "developer_2d"
  provider: "ollama"
  model: "llama3.1:8b"
  temperature: 0.3
  max_tokens: 8192

developer_3d:
  name: "developer_3d"
  provider: "ollama"
  model: "llama3.1:8b"
  temperature: 0.3
  max_tokens: 8192

art_director:
  name: "art_director"
  provider: "ollama"
  model: "llama3.1:8b"
  temperature: 0.8
  max_tokens: 4096

qa:
  name: "qa"
  provider: "ollama"
  model: "llama3.1:8b"
  temperature: 0.2
  max_tokens: 4096
"""


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary config directory."""
    config_path = tmp_path / "config"
    config_path.mkdir()
    
    agents_yaml = config_path / "agents.yaml"
    agents_yaml.write_text(SAMPLE_AGENTS_CONFIG)
    
    prompts_path = tmp_path / "prompts"
    prompts_path.mkdir()
    
    return tmp_path


@pytest.fixture
def settings(tmp_path):
    """Create test settings."""
    from gads.utils import Settings
    
    return Settings(
        session_dir=tmp_path / "sessions",
        anthropic_api_key="",
        ollama_host="http://localhost:11434",
    )


class TestOrchestratorInit:
    """Tests for Orchestrator initialization."""
    
    def test_init_with_config_dir(self, config_dir, settings):
        """Test orchestrator initialization with explicit config dir."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        
        assert orchestrator.settings == settings
        assert len(orchestrator.agents) == 6
        assert "architect" in orchestrator.agents
        assert "developer_2d" in orchestrator.agents
        assert "developer_3d" in orchestrator.agents
    
    def test_agents_registered_with_router(self, config_dir, settings):
        """Test that agents are registered with the router."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        
        assert len(orchestrator.router.agents) == 6
        assert orchestrator.router.agents["architect"] is orchestrator.agents["architect"]


class TestOrchestratorSession:
    """Tests for session management."""
    
    def test_new_project(self, config_dir, settings):
        """Test creating a new project."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        
        session = orchestrator.new_project("Test Game", "A test game project")
        
        assert session.project.name == "Test Game"
        assert session.project.description == "A test game project"
        assert orchestrator.session_manager.current == session
    
    def test_list_sessions(self, config_dir, settings):
        """Test listing sessions."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        
        orchestrator.new_project("Game 1")
        orchestrator.new_project("Game 2")
        
        sessions = orchestrator.list_sessions()
        
        assert len(sessions) == 2
    
    def test_get_session_by_id(self, config_dir, settings):
        """Test retrieving a session by ID."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        
        session = orchestrator.new_project("Test Game")
        session_id = session.id
        
        # Create a new session to change current
        orchestrator.new_project("Another Game")
        
        # Retrieve the first session
        retrieved = orchestrator.get_session(session_id)
        
        assert retrieved is not None
        assert retrieved.id == session_id
        assert retrieved.project.name == "Test Game"


class TestOrchestratorRun:
    """Tests for agent execution."""
    
    @pytest.mark.asyncio
    async def test_run_classifies_request(self, config_dir, settings):
        """Test that run() classifies requests correctly."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        session = orchestrator.new_project("Test Game")
        
        # Mock the agent execution
        mock_response = AgentResponse(
            content="Game concept response",
            agent_name="architect",
            model="llama3.1:8b",
        )
        
        with patch.object(
            orchestrator.agents["architect"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = await orchestrator.run(
                "I want to create a game about space exploration",
                session=session,
            )
        
        assert response.agent_name == "architect"
        assert response.content == "Game concept response"
    
    @pytest.mark.asyncio
    async def test_run_records_history(self, config_dir, settings):
        """Test that run() records messages in session history."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        session = orchestrator.new_project("Test Game")
        
        mock_response = AgentResponse(
            content="Test response",
            agent_name="architect",
            model="llama3.1:8b",
        )
        
        with patch.object(
            orchestrator.agents["architect"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            await orchestrator.run("Test input", session=session)
        
        # Should have 2 messages: human input and agent response
        assert len(session.history) == 2
        assert session.history[0].role == "human"
        assert session.history[0].content == "Test input"
        assert session.history[1].role == "agent"
        assert session.history[1].agent_name == "architect"
    
    @pytest.mark.asyncio
    async def test_run_with_explicit_task_type(self, config_dir, settings):
        """Test run() with explicit task type override."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        session = orchestrator.new_project("Test Game")
        
        mock_response = AgentResponse(
            content="Designer response",
            agent_name="designer",
            model="llama3.1:8b",
        )
        
        with patch.object(
            orchestrator.agents["designer"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = await orchestrator.run(
                "Some input",
                session=session,
                task_type=TaskType.MECHANIC_DESIGN,
            )
        
        assert response.agent_name == "designer"
    
    @pytest.mark.asyncio
    async def test_run_approval_rejected(self, config_dir, settings):
        """Test run() when approval is rejected."""
        # Custom approval callback that always rejects
        def reject_all(msg, decision):
            return False
        
        orchestrator = Orchestrator(
            settings=settings,
            config_dir=config_dir,
            approval_callback=reject_all,
        )
        session = orchestrator.new_project("Test Game")
        
        # GAME_CONCEPT requires approval
        response = await orchestrator.run(
            "Create a game concept",
            session=session,
            task_type=TaskType.GAME_CONCEPT,
        )
        
        assert response.agent_name == "system"
        assert "cancelled" in response.content.lower()


class TestOrchestratorPipeline:
    """Tests for pipeline execution."""
    
    @pytest.mark.asyncio
    async def test_run_pipeline_executes_steps(self, config_dir, settings):
        """Test that run_pipeline executes all steps."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        session = orchestrator.new_project("Test Game")
        
        # Create a simple pipeline
        pipeline = (
            Pipeline("test", "Test pipeline")
            .add_step("step1", "mechanic_design", output_key="design")
            .add_step("step2", "review", input_key="design", output_key="review")
        )
        
        # Mock agent executions
        mock_response1 = AgentResponse(
            content="Design output",
            agent_name="designer",
            model="llama3.1:8b",
        )
        mock_response2 = AgentResponse(
            content="Review output",
            agent_name="qa",
            model="llama3.1:8b",
        )
        
        with patch.object(
            orchestrator.agents["designer"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_response1,
        ), patch.object(
            orchestrator.agents["qa"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_response2,
        ):
            result = await orchestrator.run_pipeline(
                pipeline,
                session=session,
                initial_input="Design a jump mechanic",
            )
        
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.completed_steps) == 2
        assert "design" in result.outputs
        assert "review" in result.outputs
    
    @pytest.mark.asyncio
    async def test_run_pipeline_handles_failure(self, config_dir, settings):
        """Test that run_pipeline handles step failures."""
        orchestrator = Orchestrator(settings=settings, config_dir=config_dir)
        session = orchestrator.new_project("Test Game")
        
        pipeline = (
            Pipeline("test", "Test pipeline")
            .add_step("step1", "mechanic_design", output_key="design")
        )
        
        # Mock agent to raise exception
        with patch.object(
            orchestrator.agents["designer"],
            "execute",
            new_callable=AsyncMock,
            side_effect=Exception("Agent error"),
        ):
            result = await orchestrator.run_pipeline(
                pipeline,
                session=session,
                initial_input="Test",
            )
        
        assert result.status == PipelineStatus.FAILED
        assert "Agent error" in result.error
