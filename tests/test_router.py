"""
Tests for GADS Agent Router
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from gads.orchestrator.router import (
    AgentRouter,
    TaskType,
    ProjectType,
    RoutingDecision,
    CLASSIFICATION_SYSTEM_PROMPT,
)
from gads.orchestrator.session import Session, ProjectState


@pytest.fixture
def session():
    """Create a test session."""
    project = ProjectState(name="Test Game", description="A test project")
    return Session(project=project)


@pytest.fixture
def session_3d():
    """Create a test session for a 3D project."""
    project = ProjectState(
        name="Test 3D Game",
        description="A 3D test project",
        game_design_doc={"project_type": "3d"},
    )
    return Session(project=project)


@pytest.fixture
def router():
    """Create a router instance."""
    return AgentRouter(
        ollama_base_url="http://localhost:11434",
        classifier_model="llama3.1:8b",
    )


class TestProjectType:
    """Tests for project type detection."""
    
    def test_default_to_2d(self, router, session):
        """Test that project type defaults to 2D."""
        assert router.get_project_type(session) == ProjectType.PROJECT_2D
    
    def test_detect_3d_from_design_doc(self, router, session_3d):
        """Test detecting 3D from game design doc."""
        assert router.get_project_type(session_3d) == ProjectType.PROJECT_3D
    
    def test_detect_3d_from_assets(self, router, session):
        """Test detecting 3D from 3D assets."""
        session.project.assets_3d = ["model.glb"]
        assert router.get_project_type(session) == ProjectType.PROJECT_3D


class TestKeywordFallback:
    """Tests for keyword-based fallback classification."""
    
    def test_game_concept(self, router, session):
        """Test classification of game concept requests."""
        result = router._keyword_fallback("I want to make a game about space", session)
        assert result == TaskType.GAME_CONCEPT
    
    def test_mechanic_design(self, router, session):
        """Test classification of mechanic design requests."""
        result = router._keyword_fallback("Design a double jump mechanic", session)
        assert result == TaskType.MECHANIC_DESIGN
    
    def test_implement_feature_2d(self, router, session):
        """Test classification routes to 2D developer for 2D project."""
        result = router._keyword_fallback("Implement the player movement", session)
        assert result == TaskType.IMPLEMENT_FEATURE_2D
    
    def test_implement_feature_3d(self, router, session_3d):
        """Test classification routes to 3D developer for 3D project."""
        result = router._keyword_fallback("Implement the player movement", session_3d)
        assert result == TaskType.IMPLEMENT_FEATURE_3D
    
    def test_explicit_3d_override(self, router, session):
        """Test that explicit 3D keywords override project type."""
        result = router._keyword_fallback("Create a CharacterBody3D script", session)
        assert result == TaskType.WRITE_SCRIPT_3D
    
    def test_visual_style(self, router, session):
        """Test classification of visual style requests."""
        result = router._keyword_fallback("Define the visual style for the game", session)
        assert result == TaskType.VISUAL_STYLE
    
    def test_debug(self, router, session):
        """Test classification of debug requests."""
        result = router._keyword_fallback("Fix the bug in player movement", session)
        assert result == TaskType.DEBUG_2D


class TestLLMClassification:
    """Tests for LLM-based classification."""
    
    @pytest.mark.asyncio
    async def test_successful_classification(self, router, session):
        """Test successful LLM classification."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "message": {"content": "mechanic_design"}
        })
        
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=mock_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            result = await router.classify_request(
                "Design a wall jump ability",
                session
            )
        
        assert result == TaskType.MECHANIC_DESIGN
    
    @pytest.mark.asyncio
    async def test_invalid_response_falls_back(self, router, session):
        """Test that invalid LLM response falls back to keywords."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "message": {"content": "invalid_task_type"}
        })
        
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=mock_response)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            result = await router.classify_request(
                "I want to make a game about pirates",
                session
            )
        
        # Should fall back to keyword detection → game_concept
        assert result == TaskType.GAME_CONCEPT
    
    @pytest.mark.asyncio
    async def test_api_error_falls_back(self, router, session):
        """Test that API errors fall back to keywords."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(side_effect=Exception("Connection error"))
            mock_session_class.return_value = mock_session
            
            result = await router.classify_request(
                "Design a stealth mechanic",
                session
            )
        
        # Should fall back to keyword detection → mechanic_design
        assert result == TaskType.MECHANIC_DESIGN


class TestRouting:
    """Tests for task routing."""
    
    def test_route_to_architect(self, router, session):
        """Test routing game concept to architect."""
        # Register a mock agent
        mock_agent = MagicMock()
        router.register_agent("architect", mock_agent)
        
        decision = router.route(TaskType.GAME_CONCEPT, session)
        
        assert decision.agent_name == "architect"
        assert decision.task_type == TaskType.GAME_CONCEPT
        assert decision.requires_human_approval is True
    
    def test_route_to_developer_2d(self, router, session):
        """Test routing 2D implementation to developer_2d."""
        mock_agent = MagicMock()
        router.register_agent("developer_2d", mock_agent)
        
        decision = router.route(TaskType.IMPLEMENT_FEATURE_2D, session)
        
        assert decision.agent_name == "developer_2d"
        assert decision.requires_human_approval is False
    
    def test_route_unknown_agent_raises(self, router, session):
        """Test that routing to unregistered agent raises."""
        with pytest.raises(ValueError, match="Agent not registered"):
            router.route(TaskType.GAME_CONCEPT, session)


class TestClassificationPrompt:
    """Tests for classification prompt content."""
    
    def test_prompt_contains_all_task_types(self):
        """Test that classification prompt mentions all task types."""
        for task_type in TaskType:
            assert task_type.value in CLASSIFICATION_SYSTEM_PROMPT
    
    def test_prompt_contains_2d_3d_guidance(self):
        """Test that prompt contains 2D/3D guidance."""
        assert "2D" in CLASSIFICATION_SYSTEM_PROMPT or "2d" in CLASSIFICATION_SYSTEM_PROMPT
        assert "3D" in CLASSIFICATION_SYSTEM_PROMPT or "3d" in CLASSIFICATION_SYSTEM_PROMPT
