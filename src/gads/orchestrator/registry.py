"""
Pipeline Registry for GADS

Discovers and manages pipeline templates (built-in and custom YAML).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .pipeline import Pipeline, PipelineStep
from .router import TaskType


logger = logging.getLogger(__name__)


# Built-in pipeline definitions
BUILTIN_PIPELINES: dict[str, dict[str, Any]] = {
    "new-game": {
        "name": "new-game",
        "description": "Create a complete game concept from a brief description",
        "steps": [
            {
                "name": "concept",
                "task_type": "game_concept",
                "output_key": "concept",
            },
            {
                "name": "architecture",
                "task_type": "architecture",
                "input_key": "concept",
                "output_key": "architecture",
            },
            {
                "name": "visual_style",
                "task_type": "visual_style",
                "input_key": "concept",
                "output_key": "art_style",
            },
            {
                "name": "mechanics",
                "task_type": "mechanic_design",
                "input_key": "concept",
                "output_key": "core_mechanics",
            },
        ],
    },
    "feature": {
        "name": "feature",
        "description": "Design, implement, and review a new feature",
        "steps": [
            {
                "name": "design",
                "task_type": "mechanic_design",
                "output_key": "design",
            },
            {
                "name": "implement",
                "task_type": "implement_feature_2d",
                "input_key": "design",
                "output_key": "code",
            },
            {
                "name": "review",
                "task_type": "review",
                "input_key": "code",
                "output_key": "review",
            },
        ],
    },
    "asset": {
        "name": "asset",
        "description": "Create specifications and prompts for game assets",
        "steps": [
            {
                "name": "spec",
                "task_type": "asset_spec",
                "output_key": "asset_spec",
            },
            {
                "name": "prompts",
                "task_type": "prompt_engineering",
                "input_key": "asset_spec",
                "output_key": "sd_prompts",
            },
        ],
    },
    "iterate": {
        "name": "iterate",
        "description": "Review and improve existing code",
        "steps": [
            {
                "name": "review",
                "task_type": "review",
                "output_key": "review",
            },
            {
                "name": "fix",
                "task_type": "debug_2d",
                "input_key": "review",
                "output_key": "fixes",
            },
            {
                "name": "validate",
                "task_type": "validate",
                "input_key": "fixes",
                "output_key": "validation",
            },
        ],
    },
}


def _dict_to_pipeline(data: dict[str, Any]) -> Pipeline:
    """Convert a dictionary definition to a Pipeline object."""
    pipeline = Pipeline(
        name=data["name"],
        description=data.get("description", ""),
    )
    
    for step_data in data.get("steps", []):
        pipeline.add_step(
            name=step_data["name"],
            task_type=step_data["task_type"],
            input_key=step_data.get("input_key"),
            output_key=step_data.get("output_key"),
            condition=step_data.get("condition"),
        )
    
    return pipeline


class PipelineRegistry:
    """
    Registry for discovering and managing pipelines.
    
    Loads built-in pipelines and custom YAML pipelines from a templates directory.
    """
    
    def __init__(self, templates_dir: Path | str | None = None):
        """
        Initialize the registry.
        
        Args:
            templates_dir: Directory containing custom pipeline YAML files.
                          Looks for pipelines in templates_dir/pipelines/
        """
        self.templates_dir = Path(templates_dir) if templates_dir else None
        self._pipelines: dict[str, Pipeline] = {}
        self._load_builtin_pipelines()
        self._load_custom_pipelines()
    
    def _load_builtin_pipelines(self) -> None:
        """Load built-in pipeline definitions."""
        for name, data in BUILTIN_PIPELINES.items():
            try:
                pipeline = _dict_to_pipeline(data)
                self._pipelines[name] = pipeline
                logger.debug(f"Loaded built-in pipeline: {name}")
            except Exception as e:
                logger.error(f"Failed to load built-in pipeline '{name}': {e}")
    
    def _load_custom_pipelines(self) -> None:
        """Load custom pipelines from YAML files."""
        if not self.templates_dir:
            return
        
        pipelines_dir = self.templates_dir / "pipelines"
        if not pipelines_dir.exists():
            logger.debug(f"No custom pipelines directory: {pipelines_dir}")
            return
        
        for yaml_file in pipelines_dir.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                
                if not data or "name" not in data:
                    logger.warning(f"Invalid pipeline file (missing 'name'): {yaml_file}")
                    continue
                
                pipeline = _dict_to_pipeline(data)
                
                # Custom pipelines override built-ins with same name
                if pipeline.name in self._pipelines:
                    logger.info(f"Custom pipeline '{pipeline.name}' overrides built-in")
                
                self._pipelines[pipeline.name] = pipeline
                logger.debug(f"Loaded custom pipeline: {pipeline.name} from {yaml_file}")
                
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse pipeline YAML '{yaml_file}': {e}")
            except Exception as e:
                logger.error(f"Failed to load pipeline from '{yaml_file}': {e}")
    
    def get(self, name: str) -> Pipeline | None:
        """
        Get a pipeline by name.
        
        Args:
            name: Pipeline name
            
        Returns:
            Pipeline if found, None otherwise
        """
        return self._pipelines.get(name)
    
    def list(self) -> list[dict[str, str]]:
        """
        List all available pipelines.
        
        Returns:
            List of dicts with 'name' and 'description' keys
        """
        return [
            {"name": p.name, "description": p.description}
            for p in self._pipelines.values()
        ]
    
    def names(self) -> list[str]:
        """Get list of all pipeline names."""
        return list(self._pipelines.keys())
    
    def __contains__(self, name: str) -> bool:
        """Check if a pipeline exists."""
        return name in self._pipelines
    
    def __len__(self) -> int:
        """Get number of registered pipelines."""
        return len(self._pipelines)
