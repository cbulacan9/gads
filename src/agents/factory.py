"""
Agent Factory for GADS

Creates and manages agent instances from configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .base import AgentConfig, BaseAgent, ModelProvider
from .architect import ArchitectAgent
from .art_director import ArtDirectorAgent
from .designer import DesignerAgent
from .developer import DeveloperAgent
from .qa import QAAgent


# Registry mapping agent names to their classes
AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "architect": ArchitectAgent,
    "art_director": ArtDirectorAgent,
    "designer": DesignerAgent,
    "developer": DeveloperAgent,
    "qa": QAAgent,
}


class AgentFactory:
    """
    Factory for creating agent instances from configuration.
    
    Loads agent configurations from YAML and instantiates
    the appropriate agent classes with proper settings.
    """
    
    def __init__(
        self,
        config_path: Path | str | None = None,
        prompts_dir: Path | str | None = None,
        api_keys: dict[str, str] | None = None,
    ):
        """
        Initialize the agent factory.
        
        Args:
            config_path: Path to agents.yaml configuration file
            prompts_dir: Directory containing agent prompt files
            api_keys: Dict of API keys (e.g., {"anthropic": "sk-..."})
        """
        self.config_path = Path(config_path) if config_path else None
        self.prompts_dir = Path(prompts_dir) if prompts_dir else None
        self.api_keys = api_keys or {}
        self._raw_config: dict[str, Any] = {}
        self._agents: dict[str, BaseAgent] = {}
    
    def load_config(self, config_path: Path | str | None = None) -> dict[str, Any]:
        """
        Load agent configuration from YAML file.
        
        Args:
            config_path: Optional override for config path
            
        Returns:
            Dictionary of agent configurations
        """
        path = Path(config_path) if config_path else self.config_path
        
        if not path:
            raise ValueError("No configuration path provided")
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path) as f:
            self._raw_config = yaml.safe_load(f)
        
        return self._raw_config
    
    def create_agent(self, name: str, config_override: dict[str, Any] | None = None) -> BaseAgent:
        """
        Create a single agent instance.
        
        Args:
            name: Name of the agent to create
            config_override: Optional config values to override
            
        Returns:
            Configured agent instance
        """
        if not self._raw_config:
            self.load_config()
        
        if name not in self._raw_config:
            raise ValueError(f"Unknown agent: {name}. Available: {list(self._raw_config.keys())}")
        
        if name not in AGENT_CLASSES:
            raise ValueError(f"No agent class registered for: {name}")
        
        # Build configuration
        raw = self._raw_config[name].copy()
        if config_override:
            raw.update(config_override)
        
        # Resolve system prompt path
        if raw.get("system_prompt_path") and self.prompts_dir:
            prompt_path = self.prompts_dir / Path(raw["system_prompt_path"]).name
            if prompt_path.exists():
                raw["system_prompt_path"] = str(prompt_path)
        
        # Inject API key for Anthropic agents
        provider = raw.get("provider", "").lower()
        if provider == "anthropic" and "anthropic" in self.api_keys:
            raw["api_key"] = self.api_keys["anthropic"]
        
        # Convert provider string to enum
        raw["provider"] = ModelProvider(provider)
        
        # Create config and agent
        config = AgentConfig(**raw)
        agent_class = AGENT_CLASSES[name]
        agent = agent_class(config)
        
        self._agents[name] = agent
        return agent
    
    def create_all_agents(self) -> dict[str, BaseAgent]:
        """
        Create all agents defined in configuration.
        
        Returns:
            Dictionary mapping agent names to instances
        """
        if not self._raw_config:
            self.load_config()
        
        for name in self._raw_config:
            if name in AGENT_CLASSES:
                self.create_agent(name)
        
        return self._agents
    
    def get_agent(self, name: str) -> BaseAgent | None:
        """Get an already-created agent by name."""
        return self._agents.get(name)
    
    @property
    def agents(self) -> dict[str, BaseAgent]:
        """Get all created agents."""
        return self._agents
    
    @property
    def available_agents(self) -> list[str]:
        """Get list of agent names available in config."""
        if not self._raw_config:
            return []
        return [name for name in self._raw_config if name in AGENT_CLASSES]


def create_agents_from_config(
    config_path: Path | str,
    prompts_dir: Path | str | None = None,
    api_keys: dict[str, str] | None = None,
) -> dict[str, BaseAgent]:
    """
    Convenience function to create all agents from a config file.
    
    Args:
        config_path: Path to agents.yaml
        prompts_dir: Directory containing prompt files
        api_keys: API keys dictionary
        
    Returns:
        Dictionary of agent name -> agent instance
    """
    factory = AgentFactory(
        config_path=config_path,
        prompts_dir=prompts_dir,
        api_keys=api_keys,
    )
    return factory.create_all_agents()
