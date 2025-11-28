"""
Tests for GADS Tools
"""

import pytest
from pathlib import Path
from gads.tools.godot import GodotTool


class TestGodotTool:
    """Tests for GodotTool."""
    
    def test_project_file_generation(self, tmp_path):
        """Test generating a project.godot file."""
        tool = GodotTool(projects_dir=tmp_path)
        
        project_path = tool.create_project("TestGame")
        project_file = project_path / "project.godot"
        
        assert project_file.exists()
        content = project_file.read_text()
        assert 'config/name="TestGame"' in content
    
    def test_scene_creation(self, tmp_path):
        """Test creating a scene file."""
        tool = GodotTool(projects_dir=tmp_path)
        project_path = tool.create_project("TestGame")
        
        scene_path = tool.create_scene(project_path, "Main", "Node2D")
        
        assert scene_path.exists()
        content = scene_path.read_text()
        assert 'type="Node2D"' in content
    
    def test_script_creation(self, tmp_path):
        """Test creating a GDScript file."""
        tool = GodotTool(projects_dir=tmp_path)
        project_path = tool.create_project("TestGame")
        
        script_path = tool.create_script(project_path, "player", "CharacterBody2D")
        
        assert script_path.exists()
        content = script_path.read_text()
        assert "extends CharacterBody2D" in content
    
    def test_project_validation(self, tmp_path):
        """Test validating a project."""
        tool = GodotTool(projects_dir=tmp_path)
        project_path = tool.create_project("TestGame")
        
        result = tool.validate_project(project_path)
        
        assert result["valid"] is True
        assert len(result["issues"]) == 0
