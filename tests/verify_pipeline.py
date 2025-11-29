"""
Quick verification script for pipeline implementation.

Run with: python tests/verify_pipeline.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that all new imports work."""
    print("Testing imports...")
    
    from gads.orchestrator import PipelineRegistry, PipelineStatus
    print("  ✓ PipelineRegistry imported")
    
    from gads.orchestrator.session import ProjectState
    ps = ProjectState(name="Test", project_type="3d", art_style="low-poly")
    assert ps.project_type == "3d"
    assert ps.art_style == "low-poly"
    print("  ✓ ProjectState has new fields")
    
    from gads.cli import app, pipeline_app
    print("  ✓ CLI app imported with pipeline subcommand")


def test_registry():
    """Test the pipeline registry."""
    print("\nTesting PipelineRegistry...")
    
    from gads.orchestrator import PipelineRegistry
    
    # Test without templates dir (built-ins only)
    registry = PipelineRegistry()
    
    print(f"  ✓ Built-in pipelines: {len(registry)}")
    
    names = registry.names()
    assert "new-game" in names, "Missing new-game pipeline"
    assert "feature" in names, "Missing feature pipeline"
    assert "asset" in names, "Missing asset pipeline"
    assert "iterate" in names, "Missing iterate pipeline"
    print(f"  ✓ All built-in pipelines found: {', '.join(names)}")
    
    # Test getting a pipeline
    pipeline = registry.get("new-game")
    assert pipeline is not None
    assert len(pipeline.steps) == 4
    print(f"  ✓ new-game pipeline has {len(pipeline.steps)} steps")
    
    # Test with templates dir
    templates_dir = Path(__file__).parent.parent / "templates"
    registry2 = PipelineRegistry(templates_dir=templates_dir)
    
    if "prototype" in registry2:
        print("  ✓ Custom prototype pipeline loaded from YAML")
    else:
        print("  ⚠ Custom prototype pipeline not found (templates dir may be missing)")


def test_session_manager():
    """Test SessionManager with new parameters."""
    print("\nTesting SessionManager...")
    
    import tempfile
    from gads.orchestrator import SessionManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager(Path(tmpdir))
        
        session = manager.create_session(
            "Test Project",
            "A test",
            project_type="3d",
            art_style="pixel-art",
        )
        
        assert session.project.project_type == "3d"
        assert session.project.art_style == "pixel-art"
        print("  ✓ SessionManager.create_session accepts new params")
        
        # Reload and verify
        loaded = manager.load(session.id)
        assert loaded.project.project_type == "3d"
        assert loaded.project.art_style == "pixel-art"
        print("  ✓ Project settings persist after save/load")


def main():
    print("=" * 50)
    print("Pipeline Implementation Verification")
    print("=" * 50)
    
    try:
        test_imports()
        test_registry()
        test_session_manager()
        
        print("\n" + "=" * 50)
        print("✓ All verifications passed!")
        print("=" * 50)
        
        print("\nNext steps:")
        print("  1. gads pipeline list")
        print("  2. gads new-project \"My Game\" --3d --style pixel-art")
        print("  3. gads pipeline run new-game \"A puzzle game about time\"")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
