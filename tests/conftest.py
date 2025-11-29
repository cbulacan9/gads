"""
GADS Test Suite - Pytest Configuration

Shared fixtures and configuration for tests.
"""

import pytest
from pathlib import Path


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end (requires running Ollama)"
    )


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests that require Ollama",
    )


def pytest_collection_modifyitems(config, items):
    """Skip e2e tests unless --run-e2e is specified."""
    if config.getoption("--run-e2e"):
        # --run-e2e given: do not skip e2e tests
        return
    
    skip_e2e = pytest.mark.skip(reason="Need --run-e2e option to run")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory with agents.yaml.
    
    Note: Unit tests use a mock model name since they don't actually call Ollama.
    For real LLM calls, use the e2e tests which auto-detect available models.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    # Use a placeholder model for unit tests (mocked, never actually called)
    agents_yaml = config_dir / "agents.yaml"
    agents_yaml.write_text("""
architect:
  name: "architect"
  provider: "ollama"
  model: "qwen2.5-coder:14b"
  temperature: 0.7
  max_tokens: 4096

designer:
  name: "designer"
  provider: "ollama"
  model: "qwen2.5-coder:14b"
  temperature: 0.7
  max_tokens: 4096

developer_2d:
  name: "developer_2d"
  provider: "ollama"
  model: "qwen2.5-coder:14b"
  temperature: 0.3
  max_tokens: 8192

developer_3d:
  name: "developer_3d"
  provider: "ollama"
  model: "qwen2.5-coder:14b"
  temperature: 0.3
  max_tokens: 8192

art_director:
  name: "art_director"
  provider: "ollama"
  model: "qwen2.5-coder:14b"
  temperature: 0.8
  max_tokens: 4096

qa:
  name: "qa"
  provider: "ollama"
  model: "qwen2.5-coder:14b"
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
