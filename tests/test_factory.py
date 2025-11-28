"""
Tests for GADS Agent Factory
"""

import pytest
from pathlib import Path

from gads.agents import (
    AgentFactory,
    create_agents_from_config,
    ArchitectAgent,
    Developer2DAgent,
    Developer3DAgent,
    ModelProvider,
)


SAMPLE_CONFIG = """
architect:
  name: "architect"
  provider: "anthropic"
  model: "claude-opus-4-5-20251101"
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
"""


class TestAgentFactory:
    """Tests for AgentFactory class."""
    
    @pytest.fixture
    def config_file(self, tmp_path):
        """Create a temporary config file."""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(SAMPLE_CONFIG)
        return config_path
    
    def test_load_config(self, config_file):
        """Test loading configuration from YAML."""
        factory = AgentFactory(config_path=config_file)
        config = factory.load_config()
        
        assert "architect" in config
        assert "developer_2d" in config
        assert "developer_3d" in config
        assert config["architect"]["model"] == "claude-opus-4-5-20251101"
    
    def test_create_single_agent_2d(self, config_file):
        """Test creating a 2D developer agent."""
        factory = AgentFactory(config_path=config_file)
        factory.load_config()
        
        agent = factory.create_agent("developer_2d")
        
        assert isinstance(agent, Developer2DAgent)
        assert agent.name == "developer_2d"
        assert agent.config.provider == ModelProvider.OLLAMA
        assert agent.config.model == "llama3.1:8b"
    
    def test_create_single_agent_3d(self, config_file):
        """Test creating a 3D developer agent."""
        factory = AgentFactory(config_path=config_file)
        factory.load_config()
        
        agent = factory.create_agent("developer_3d")
        
        assert isinstance(agent, Developer3DAgent)
        assert agent.name == "developer_3d"
        assert agent.config.provider == ModelProvider.OLLAMA
    
    def test_create_all_agents(self, config_file):
        """Test creating all agents from config."""
        factory = AgentFactory(config_path=config_file)
        agents = factory.create_all_agents()
        
        assert "architect" in agents
        assert "developer_2d" in agents
        assert "developer_3d" in agents
        assert isinstance(agents["architect"], ArchitectAgent)
        assert isinstance(agents["developer_2d"], Developer2DAgent)
        assert isinstance(agents["developer_3d"], Developer3DAgent)
    
    def test_api_key_injection(self, config_file):
        """Test that API keys are injected for Anthropic agents."""
        factory = AgentFactory(
            config_path=config_file,
            api_keys={"anthropic": "test-api-key"},
        )
        agents = factory.create_all_agents()
        
        assert agents["architect"].config.api_key == "test-api-key"
        assert agents["developer_2d"].config.api_key is None
        assert agents["developer_3d"].config.api_key is None
    
    def test_available_agents(self, config_file):
        """Test listing available agents."""
        factory = AgentFactory(config_path=config_file)
        factory.load_config()
        
        available = factory.available_agents
        
        assert "architect" in available
        assert "developer_2d" in available
        assert "developer_3d" in available
    
    def test_get_agent(self, config_file):
        """Test retrieving a created agent."""
        factory = AgentFactory(config_path=config_file)
        factory.create_all_agents()
        
        agent = factory.get_agent("developer_2d")
        assert agent is not None
        assert agent.name == "developer_2d"
        
        missing = factory.get_agent("nonexistent")
        assert missing is None
    
    def test_unknown_agent_error(self, config_file):
        """Test error when creating unknown agent."""
        factory = AgentFactory(config_path=config_file)
        factory.load_config()
        
        with pytest.raises(ValueError, match="Unknown agent"):
            factory.create_agent("nonexistent")
    
    def test_missing_config_error(self):
        """Test error when config file doesn't exist."""
        factory = AgentFactory(config_path=Path("/nonexistent/config.yaml"))
        
        with pytest.raises(FileNotFoundError):
            factory.load_config()


class TestCreateAgentsFromConfig:
    """Tests for convenience function."""
    
    def test_create_agents_convenience(self, tmp_path):
        """Test the convenience function."""
        config_path = tmp_path / "agents.yaml"
        config_path.write_text(SAMPLE_CONFIG)
        
        agents = create_agents_from_config(config_path)
        
        assert len(agents) == 3
        assert "architect" in agents
        assert "developer_2d" in agents
        assert "developer_3d" in agents
