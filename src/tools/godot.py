"""
Godot Tool for GADS

Interface for interacting with Godot projects and the Godot editor.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class GodotTool:
    """Tool for interacting with Godot projects."""
    
    def __init__(self, godot_executable: str = "godot", projects_dir: Path | None = None):
        self.godot_executable = godot_executable
        self.projects_dir = projects_dir or Path("./projects")
        self.projects_dir.mkdir(parents=True, exist_ok=True)
    
    def create_project(self, name: str, template: str = "default") -> Path:
        """Create a new Godot project from template."""
        project_path = self.projects_dir / name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create minimal project.godot
        project_godot = project_path / "project.godot"
        project_godot.write_text(self._generate_project_file(name))
        
        return project_path
    
    def _generate_project_file(self, name: str) -> str:
        """Generate a minimal project.godot file."""
        return f"""; Engine configuration file.
; It's best edited using the editor UI and not directly,
; since the parameters that go here are not all obvious.

config_version=5

[application]

config/name="{name}"
config/features=PackedStringArray("4.2", "Forward Plus")

[rendering]

renderer/rendering_method="forward_plus"
"""
    
    def create_scene(self, project_path: Path, scene_name: str, root_type: str = "Node2D") -> Path:
        """Create a new scene file."""
        scene_path = project_path / f"{scene_name}.tscn"
        scene_content = f"""[gd_scene format=3]

[node name="{scene_name}" type="{root_type}"]
"""
        scene_path.write_text(scene_content)
        return scene_path
    
    def create_script(self, project_path: Path, script_name: str, extends: str = "Node") -> Path:
        """Create a new GDScript file."""
        script_path = project_path / f"{script_name}.gd"
        script_content = f"""extends {extends}


func _ready() -> void:
    pass


func _process(delta: float) -> void:
    pass
"""
        script_path.write_text(script_content)
        return script_path
    
    def run_project(self, project_path: Path) -> subprocess.Popen:
        """Launch the Godot project."""
        return subprocess.Popen(
            [self.godot_executable, "--path", str(project_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    
    def validate_project(self, project_path: Path) -> dict[str, Any]:
        """Validate a Godot project structure."""
        issues = []
        
        project_file = project_path / "project.godot"
        if not project_file.exists():
            issues.append("Missing project.godot file")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "path": str(project_path),
        }
