"""
Quick Integration Test for GADS

Tests that both Anthropic (Claude) and Ollama (Qwen) are working correctly.

Run with: python tests/quick_test.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gads.orchestrator import Orchestrator, TaskType
from gads.utils import load_settings


async def test_ollama_agent():
    """Test an Ollama-based agent (Designer)."""
    print("\n" + "=" * 60)
    print("Testing Ollama Agent (Designer - qwen2.5-coder:14b)")
    print("=" * 60)
    
    settings = load_settings()
    orchestrator = Orchestrator(
        settings=settings,
        approval_callback=lambda msg, decision: True,
    )
    
    session = orchestrator.new_project("Test Project", "Testing Ollama integration")
    
    try:
        response = await orchestrator.run(
            "Design a simple double-jump mechanic for a 2D platformer. Keep it brief.",
            session=session,
            task_type=TaskType.MECHANIC_DESIGN,
        )
        
        print(f"\n✓ Agent: {response.agent_name}")
        print(f"✓ Model: {response.model}")
        print(f"\nResponse preview (first 500 chars):")
        print("-" * 40)
        print(response.content[:500] + "..." if len(response.content) > 500 else response.content)
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


async def test_anthropic_agent():
    """Test an Anthropic-based agent (Architect)."""
    print("\n" + "=" * 60)
    print("Testing Anthropic Agent (Architect - Claude Opus 4.5)")
    print("=" * 60)
    
    settings = load_settings()
    
    if not settings.anthropic_api_key:
        print("\n⚠ ANTHROPIC_API_KEY not set in .env - skipping Anthropic test")
        return None
    
    orchestrator = Orchestrator(
        settings=settings,
        approval_callback=lambda msg, decision: True,
    )
    
    session = orchestrator.new_project("Test Project 2", "Testing Anthropic integration")
    
    try:
        response = await orchestrator.run(
            "Briefly describe a game concept: a cozy farming sim with magic elements. 2-3 sentences only.",
            session=session,
            task_type=TaskType.GAME_CONCEPT,
        )
        
        print(f"\n✓ Agent: {response.agent_name}")
        print(f"✓ Model: {response.model}")
        print(f"\nResponse preview (first 500 chars):")
        print("-" * 40)
        print(response.content[:500] + "..." if len(response.content) > 500 else response.content)
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


async def test_router_classification():
    """Test that the router correctly classifies requests."""
    print("\n" + "=" * 60)
    print("Testing Router Classification (Ollama)")
    print("=" * 60)
    
    settings = load_settings()
    orchestrator = Orchestrator(
        settings=settings,
        approval_callback=lambda msg, decision: True,
    )
    
    session = orchestrator.new_project("Router Test", "Testing classification")
    
    test_cases = [
        ("I want to make a game about robots", "architect tasks"),
        ("Write a player movement script", "developer tasks"),
        ("Design a health system mechanic", "designer tasks"),
    ]
    
    all_passed = True
    
    for prompt, expected_category in test_cases:
        try:
            task_type = await orchestrator.router.classify_request(prompt, session)
            print(f"\n✓ '{prompt[:40]}...'")
            print(f"  → Classified as: {task_type.value}")
        except Exception as e:
            print(f"\n✗ '{prompt[:40]}...' failed: {e}")
            all_passed = False
    
    return all_passed


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("GADS Quick Integration Test")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Router (uses Ollama)
    results["Router"] = await test_router_classification()
    
    # Test 2: Ollama agent
    results["Ollama (Designer)"] = await test_ollama_agent()
    
    # Test 3: Anthropic agent
    results["Anthropic (Architect)"] = await test_anthropic_agent()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        if passed is None:
            status = "⚠ SKIPPED"
        elif passed:
            status = "✓ PASSED"
        else:
            status = "✗ FAILED"
        print(f"  {test_name}: {status}")
    
    # Overall result
    failed = [k for k, v in results.items() if v is False]
    if failed:
        print(f"\n✗ Some tests failed: {', '.join(failed)}")
        return 1
    else:
        print("\n✓ All tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
