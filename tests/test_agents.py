"""
Tests for GADS Agents
"""

import pytest
from gads.agents.base import AgentConfig, AgentResponse, ModelProvider


class TestAgentConfig:
    """Tests for AgentConfig model."""
    
    def test_config_creation(self):
        """Test creating an agent configuration."""
        config = AgentConfig(
            name="test_agent",
            provider=ModelProvider.OLLAMA,
            model="llama3.1:8b",
        )
        
        assert config.name == "test_agent"
        assert config.provider == ModelProvider.OLLAMA
        assert config.model == "llama3.1:8b"
        assert config.temperature == 0.7  # default
    
    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = AgentConfig(
            name="custom_agent",
            provider=ModelProvider.ANTHROPIC,
            model="claude-opus-4-5-20251101",
            temperature=0.5,
            max_tokens=8192,
            api_key="test_key",
        )
        
        assert config.temperature == 0.5
        assert config.max_tokens == 8192
        assert config.api_key == "test_key"


class TestAgentResponse:
    """Tests for AgentResponse model."""
    
    def test_response_creation(self):
        """Test creating an agent response."""
        response = AgentResponse(
            content="Test response content",
            agent_name="test_agent",
            model="llama3.1:8b",
        )
        
        assert response.content == "Test response content"
        assert response.agent_name == "test_agent"
        assert response.artifacts == {}
    
    def test_response_with_artifacts(self):
        """Test response with artifacts."""
        response = AgentResponse(
            content="Response with code",
            agent_name="developer_2d",
            model="llama3.1:8b",
            artifacts={"gdscript_blocks": ["extends Node2D"]},
        )
        
        assert "gdscript_blocks" in response.artifacts
