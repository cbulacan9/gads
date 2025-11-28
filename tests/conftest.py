"""
GADS Test Suite - Pytest Configuration

Shared fixtures and configuration for tests.
"""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory with agents.yaml."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    agents_yaml = config_dir / "agents.yaml"
    agents_yaml.write_text("""
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
""")
    
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    
    return tmp_path


@pytest.fixture
def tmp_sessions_dir(tmp_path: Path) -> Path:
    """Create a temporary sessions directory."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    return sessions_dir
