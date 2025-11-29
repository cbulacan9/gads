"""
Test script for GodotTool project creation.

Run with: python tests/test_godot_tool.py
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_create_2d_project():
    """Test creating a 2D project."""
    print("\n" + "=" * 50)
    print("Testing 2D Project Creation")
    print("=" * 50)
    
    from gads.tools import GodotTool
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = GodotTool(projects_dir=tmpdir)
        
        project_path = tool.create_project(
            name="My Test Game",
            project_type="2d",
            description="A test 2D platformer",
            art_style="pixel-art",
        )
        
        print(f"✓ Project created at: {project_path}")
        
        # Check structure
        assert project_path.exists(), "Project directory not created"
        assert (project_path / "project.godot").exists(), "project.godot not created"
        assert (project_path / "scenes").exists(), "scenes/ not created"
        assert (project_path / "scripts").exists(), "scripts/ not created"
        assert (project_path / "assets" / "sprites").exists(), "assets/sprites/ not created"
        assert (project_path / "autoloads").exists(), "autoloads/ not created"
        assert (project_path / "scenes" / "main.tscn").exists(), "main.tscn not created"
        assert (project_path / "autoloads" / "game_manager.gd").exists(), "game_manager.gd not created"
        assert (project_path / "README.md").exists(), "README.md not created"
        assert (project_path / ".gitignore").exists(), ".gitignore not created"
        
        print("✓ All expected files/folders exist")
        
        # Validate
        validation = tool.validate_project(project_path)
        assert validation["valid"], f"Project validation failed: {validation['issues']}"
        print("✓ Project validation passed")
        
        # Check project.godot content
        project_content = (project_path / "project.godot").read_text(encoding="utf-8")
        assert 'config/name="My Test Game"' in project_content
        assert 'main_scene="res://scenes/main.tscn"' in project_content
        print("✓ project.godot has correct configuration")
        
        # Check README content
        readme_content = (project_path / "README.md").read_text(encoding="utf-8")
        assert "My Test Game" in readme_content
        assert "pixel-art" in readme_content
        assert "2D" in readme_content
        print("✓ README.md has correct content")
        
        # Check enhanced main scene
        main_scene = (project_path / "scenes" / "main.tscn").read_text(encoding="utf-8")
        assert "Camera2D" in main_scene, "2D main scene should have Camera2D"
        assert "CanvasLayer" in main_scene, "2D main scene should have UI CanvasLayer"
        print("✓ 2D Main scene has Camera2D and UI layer")
        
        print("\n2D Project Test: PASSED")


def test_create_3d_project():
    """Test creating a 3D project with enhanced scene."""
    print("\n" + "=" * 50)
    print("Testing 3D Project Creation")
    print("=" * 50)
    
    from gads.tools import GodotTool
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = GodotTool(projects_dir=tmpdir)
        
        project_path = tool.create_project(
            name="Space Explorer",
            project_type="3d",
            description="A 3D space adventure",
            art_style="low-poly",
        )
        
        print(f"✓ Project created at: {project_path}")
        
        # Check 3D-specific structure
        assert (project_path / "assets" / "models").exists(), "assets/models/ not created"
        assert (project_path / "assets" / "textures").exists(), "assets/textures/ not created"
        print("✓ 3D-specific folders exist")
        
        # Check main scene has all required 3D elements
        main_scene = (project_path / "scenes" / "main.tscn").read_text(encoding="utf-8")
        assert 'type="Node3D"' in main_scene, "Main scene should have Node3D"
        assert "Camera3D" in main_scene, "Main scene should have Camera3D"
        assert "DirectionalLight3D" in main_scene, "Main scene should have DirectionalLight3D"
        assert "WorldEnvironment" in main_scene, "Main scene should have WorldEnvironment"
        assert "CSGBox3D" in main_scene, "Main scene should have ground plane"
        print("✓ 3D Main scene has Camera3D, lighting, environment, and ground")
        
        print("\n3D Project Test: PASSED")


def test_create_scene_and_script():
    """Test creating additional scenes and scripts."""
    print("\n" + "=" * 50)
    print("Testing Scene and Script Creation")
    print("=" * 50)
    
    from gads.tools import GodotTool
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = GodotTool(projects_dir=tmpdir)
        
        # Create project first
        project_path = tool.create_project("Test Game", project_type="2d")
        
        # Create a script
        script_path = tool.create_script(
            project_path,
            script_name="player",
            extends="CharacterBody2D",
            content="""extends CharacterBody2D

@export var speed: float = 200.0

func _physics_process(delta: float) -> void:
    var direction = Input.get_vector("move_left", "move_right", "move_up", "move_down")
    velocity = direction * speed
    move_and_slide()
""",
        )
        
        assert script_path.exists()
        assert "CharacterBody2D" in script_path.read_text(encoding="utf-8")
        print(f"✓ Script created: {script_path.name}")
        
        # Create a scene with attached script
        scene_path = tool.create_scene(
            project_path,
            scene_name="player",
            root_type="CharacterBody2D",
            script_path="res://scripts/player.gd",
        )
        
        assert scene_path.exists()
        scene_content = scene_path.read_text(encoding="utf-8")
        assert 'type="CharacterBody2D"' in scene_content
        assert 'res://scripts/player.gd' in scene_content
        print(f"✓ Scene created with script: {scene_path.name}")
        
        print("\nScene/Script Test: PASSED")


def test_player_scene_creation():
    """Test creating player scenes."""
    print("\n" + "=" * 50)
    print("Testing Player Scene Creation")
    print("=" * 50)
    
    from gads.tools import GodotTool
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = GodotTool(projects_dir=tmpdir)
        
        # Create 2D project and player
        project_2d = tool.create_project("Test 2D", project_type="2d")
        player_2d = tool.create_player_scene_2d(project_2d)
        
        assert player_2d.exists()
        content = player_2d.read_text(encoding="utf-8")
        assert "CharacterBody2D" in content
        assert "CollisionShape2D" in content
        assert "Sprite2D" in content
        print("✓ 2D Player scene created with CharacterBody2D")
        
        # Create 3D project and player
        project_3d = tool.create_project("Test 3D", project_type="3d")
        player_3d = tool.create_player_scene_3d(project_3d)
        
        assert player_3d.exists()
        content = player_3d.read_text(encoding="utf-8")
        assert "CharacterBody3D" in content
        assert "CollisionShape3D" in content
        assert "MeshInstance3D" in content
        print("✓ 3D Player scene created with CharacterBody3D")
        
        # Test with script attached
        tool.create_script(
            project_2d,
            "player_controller",
            extends="CharacterBody2D",
        )
        player_with_script = tool.create_player_scene_2d(
            project_2d,
            script_path="res://scripts/player_controller.gd",
        )
        content = player_with_script.read_text(encoding="utf-8")
        assert "res://scripts/player_controller.gd" in content
        print("✓ Player scene with script reference works")
        
        print("\nPlayer Scene Test: PASSED")


def test_list_projects():
    """Test listing projects."""
    print("\n" + "=" * 50)
    print("Testing Project Listing")
    print("=" * 50)
    
    from gads.tools import GodotTool
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = GodotTool(projects_dir=tmpdir)
        
        # Create a few projects
        tool.create_project("Game One", project_type="2d")
        tool.create_project("Game Two", project_type="3d")
        
        projects = tool.list_projects()
        
        assert len(projects) == 2
        names = [p["name"] for p in projects]
        assert "game_one" in names
        assert "game_two" in names
        print(f"✓ Found {len(projects)} projects: {names}")
        
        print("\nProject Listing Test: PASSED")


def main():
    print("=" * 50)
    print("GodotTool Test Suite")
    print("=" * 50)
    
    try:
        test_create_2d_project()
        test_create_3d_project()
        test_create_scene_and_script()
        test_player_scene_creation()
        test_list_projects()
        
        print("\n" + "=" * 50)
        print("✓ All GodotTool tests passed!")
        print("=" * 50)
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
