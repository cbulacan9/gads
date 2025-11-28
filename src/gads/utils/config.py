"""
Configuration Management for GADS

Loads and validates configuration from environment variables and files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Anthropic (for Architect and Art Director)
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    
    # Ollama (for Designer, Developers, QA, and Router)
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API URL")
    ollama_model: str = Field(default="qwen2.5-coder:14b", description="Default Ollama model")
    
    # Stable Diffusion
    sd_api_url: str = Field(default="http://localhost:7860", description="SD A1111 API URL")
    sd_api_key: str = Field(default="", description="SD API key if required")
    
    # Blender MCP
    blender_mcp_host: str = Field(default="localhost", description="Blender MCP host")
    blender_mcp_port: int = Field(default=9876, description="Blender MCP port")
    
    # Godot
    godot_executable: str = Field(default="godot", description="Path to Godot executable")
    godot_projects_dir: Path = Field(default=Path("./projects"), description="Projects directory")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path | None = Field(default=None, description="Log file path")
    
    # Session
    session_dir: Path = Field(default=Path("./sessions"), description="Session storage directory")
    max_session_history: int = Field(default=100, description="Max messages to keep in history")


def load_settings(env_file: str | None = None) -> Settings:
    """Load settings from environment and optional env file."""
    if env_file:
        return Settings(_env_file=env_file)
    return Settings()
