"""
End-to-End Tests with Real Ollama

These tests require a running Ollama instance with llama3.1:8b model.
They verify the complete flow from CLI/orchestrator through to actual LLM responses.

Run with: pytest tests/test_e2e_ollama.py -v -s
Skip these in CI with: pytest -m "not e2e"
"""

import asyncio
import pytest
from pathlib import Path

import aiohttp

from gads.orchestrator import Orchestrator, TaskType, Pipeline, PipelineStatus
from gads.agents import AgentFactory, AgentResponse
from gads.utils import Settings


# Mark all tests in this module as e2e (can be skipped in CI)
pytestmark = pytest.mark.e2e


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def ollama_available():
    """Check if Ollama is running and has a compatible model."""
    async def check():
        try:
            async with aiohttp.ClientSession() as session:
                # Check Ollama is running
                async with session.get(
                    "http://localhost:11434/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status != 200:
                        return False, "Ollama not responding", None
                    
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    
                    if not models:
                        return False, "No models installed", []
                    
                    # Find the first available llama model
                    # Prefer llama3.1:8b, but accept others
                    preferred = ["llama3.1:8b", "llama3.2:3b", "llama3:8b", "llama3"]
                    selected_model = None
                    
                    for pref in preferred:
                        for m in models:
                            if pref in m.lower():
                                selected_model = m
                                break
                        if selected_model:
                            break
                    
                    # Fallback: any model with "llama" in name
                    if not selected_model:
                        for m in models:
                            if "llama" in m.lower():
                                selected_model = m
                                break
                    
                    # Last resort: use first available model
                    if not selected_model:
                        selected_model = models[0]
                    
                    return True, f"Using model: {selected_model}", selected_model
                    
        except asyncio.TimeoutError:
            return False, "Connection timeout", None
        except aiohttp.ClientConnectorError:
            return False, "Cannot connect to Ollama. Run: ollama serve", None
        except Exception as e:
            return False, f"Error: {e}", None
    
    available, message, model = asyncio.run(check())
    if not available:
        pytest.skip(f"Ollama not available: {message}")
    
    return model  # Return the selected model name


@pytest.fixture
def e2e_config_dir(tmp_path, ollama_available):
    """Create config directory for e2e tests using Ollama for all agents."""
    model_name = ollama_available  # This is the detected model name
    
    config_path = tmp_path / "config"
    config_path.mkdir()
    
    # Use Ollama for all agents in e2e tests (no Anthropic API needed)
    agents_yaml = config_path / "agents.yaml"
    agents_yaml.write_text(f"""
architect:
  name: "architect"
  provider: "ollama"
  model: "{model_name}"
  temperature: 0.7
  max_tokens: 2048

designer:
  name: "designer"
  provider: "ollama"
  model: "{model_name}"
  temperature: 0.7
  max_tokens: 2048

developer_2d:
  name: "developer_2d"
  provider: "ollama"
  model: "{model_name}"
  temperature: 0.3
  max_tokens: 4096

developer_3d:
  name: "developer_3d"
  provider: "ollama"
  model: "{model_name}"
  temperature: 0.3
  max_tokens: 4096

art_director:
  name: "art_director"
  provider: "ollama"
  model: "{model_name}"
  temperature: 0.8
  max_tokens: 2048

qa:
  name: "qa"
  provider: "ollama"
  model: "{model_name}"
  temperature: 0.2
  max_tokens: 2048
""")
    
    # Create prompts directory with basic prompts
    prompts_path = tmp_path / "prompts"
    prompts_path.mkdir()
    
    # Architect prompt
    (prompts_path / "architect.md").write_text("""You are the Architect agent for a Godot game development system.

Your role is to:
- Design high-level game concepts
- Plan system architecture
- Define core game loops
- Make creative decisions about game direction

When given a game concept request, provide:
1. A brief game overview
2. Core gameplay mechanics
3. Target platform considerations
4. Technical approach for Godot 4.x

Be concise but thorough. Focus on actionable design decisions.""")
    
    # Designer prompt
    (prompts_path / "designer.md").write_text("""You are the Designer agent for a Godot game development system.

Your role is to:
- Design specific game mechanics
- Create level layouts and progression
- Balance gameplay elements
- Define player interactions

Provide specific, implementable designs that developers can code directly.
Include GDScript pseudocode where helpful.""")
    
    # Developer 2D prompt
    (prompts_path / "developer_2d.md").write_text("""You are a Godot 4.x 2D Developer agent.

Your role is to write GDScript code for 2D games. Always:
- Use Godot 4.x syntax (typed GDScript)
- Use appropriate 2D nodes: CharacterBody2D, Sprite2D, CollisionShape2D, etc.
- Follow Godot best practices
- Include comments explaining the code

Provide complete, working GDScript that can be used directly in Godot.""")
    
    # Developer 3D prompt
    (prompts_path / "developer_3d.md").write_text("""You are a Godot 4.x 3D Developer agent.

Your role is to write GDScript code for 3D games. Always:
- Use Godot 4.x syntax (typed GDScript)
- Use appropriate 3D nodes: CharacterBody3D, MeshInstance3D, CollisionShape3D, etc.
- Follow Godot best practices
- Include comments explaining the code

Provide complete, working GDScript that can be used directly in Godot.""")
    
    # Art Director prompt
    (prompts_path / "art_director.md").write_text("""You are the Art Director agent for a Godot game development system.

Your role is to:
- Define visual styles and aesthetics
- Specify asset requirements
- Create color palettes
- Write Stable Diffusion prompts for concept art

Provide clear, actionable art direction that artists and AI tools can follow.""")
    
    # QA prompt
    (prompts_path / "qa.md").write_text("""You are the QA agent for a Godot game development system.

Your role is to:
- Review code for bugs and issues
- Suggest test cases
- Validate implementations against designs
- Check for Godot best practices

Be thorough but constructive in your feedback.""")
    
    return tmp_path


@pytest.fixture
def e2e_settings(tmp_path, ollama_available):
    """Settings for e2e tests."""
    model_name = ollama_available  # This is the detected model name
    
    return Settings(
        session_dir=tmp_path / "sessions",
        anthropic_api_key="",  # Not needed for Ollama tests
        ollama_host="http://localhost:11434",
        ollama_model=model_name,
    )


@pytest.fixture
def orchestrator(e2e_config_dir, e2e_settings):
    """Create orchestrator with real Ollama connection."""
    return Orchestrator(
        settings=e2e_settings,
        config_dir=e2e_config_dir,
        approval_callback=lambda msg, decision: True,  # Auto-approve
    )


# ============================================================================
# Router Classification Tests
# ============================================================================

class TestRouterClassification:
    """Test LLM-based request classification."""
    
    @pytest.mark.asyncio
    async def test_classifies_game_concept(self, orchestrator):
        """Test classification of game concept requests."""
        session = orchestrator.new_project("Test Game")
        
        task_type = await orchestrator.router.classify_request(
            "I want to make a platformer game where you play as a cat",
            session,
        )
        
        # Should route to architect-level tasks
        assert task_type in [
            TaskType.GAME_CONCEPT,
            TaskType.CREATIVE_DIRECTION,
            TaskType.SYSTEM_DESIGN,
        ]
    
    @pytest.mark.asyncio
    async def test_classifies_mechanic_design(self, orchestrator):
        """Test classification of mechanic design requests."""
        session = orchestrator.new_project("Test Game")
        
        task_type = await orchestrator.router.classify_request(
            "Design a double jump mechanic for the player",
            session,
        )
        
        assert task_type in [
            TaskType.MECHANIC_DESIGN,
            TaskType.IMPLEMENT_FEATURE_2D,  # Could go either way
        ]
    
    @pytest.mark.asyncio
    async def test_classifies_code_request_2d(self, orchestrator):
        """Test classification of 2D code requests."""
        session = orchestrator.new_project("Test Game")
        
        task_type = await orchestrator.router.classify_request(
            "Write a CharacterBody2D script for player movement with WASD",
            session,
        )
        
        # Should route to 2D developer
        assert task_type in [
            TaskType.IMPLEMENT_FEATURE_2D,
            TaskType.WRITE_SCRIPT_2D,
        ]
    
    @pytest.mark.asyncio
    async def test_classifies_code_request_3d(self, orchestrator):
        """Test classification of 3D code requests."""
        session = orchestrator.new_project("Test Game")
        
        task_type = await orchestrator.router.classify_request(
            "Create a CharacterBody3D first-person camera controller",
            session,
        )
        
        # Should route to 3D developer
        assert task_type in [
            TaskType.IMPLEMENT_FEATURE_3D,
            TaskType.WRITE_SCRIPT_3D,
        ]
    
    @pytest.mark.asyncio
    async def test_classifies_visual_style(self, orchestrator):
        """Test classification of art direction requests."""
        session = orchestrator.new_project("Test Game")
        
        task_type = await orchestrator.router.classify_request(
            "What visual style should we use? I'm thinking pixel art with a dark fantasy theme",
            session,
        )
        
        assert task_type in [
            TaskType.VISUAL_STYLE,
            TaskType.ASSET_SPEC,
        ]


# ============================================================================
# Single Agent Execution Tests
# ============================================================================

class TestAgentExecution:
    """Test individual agent execution with real LLM."""
    
    @pytest.mark.asyncio
    async def test_architect_generates_concept(self, orchestrator):
        """Test Architect agent generates a game concept."""
        session = orchestrator.new_project("Space Explorer")
        
        response = await orchestrator.run(
            "Design a simple 2D space exploration game where you mine asteroids",
            session=session,
            task_type=TaskType.GAME_CONCEPT,
        )
        
        assert response.agent_name == "architect"
        assert len(response.content) > 100  # Should have substantial content
        
        # Should mention key game elements
        content_lower = response.content.lower()
        assert any(word in content_lower for word in ["space", "asteroid", "mine", "player", "game"])
    
    @pytest.mark.asyncio
    async def test_designer_creates_mechanic(self, orchestrator):
        """Test Designer agent creates a game mechanic."""
        session = orchestrator.new_project("Platformer")
        
        response = await orchestrator.run(
            "Design a wall jump mechanic for a 2D platformer",
            session=session,
            task_type=TaskType.MECHANIC_DESIGN,
        )
        
        assert response.agent_name == "designer"
        assert len(response.content) > 50
        
        # Should describe the mechanic
        content_lower = response.content.lower()
        assert any(word in content_lower for word in ["wall", "jump", "player"])
    
    @pytest.mark.asyncio
    async def test_developer_2d_writes_code(self, orchestrator):
        """Test Developer2D agent writes GDScript."""
        session = orchestrator.new_project("Platformer")
        
        response = await orchestrator.run(
            "Write a simple player movement script for a CharacterBody2D that moves left/right with arrow keys",
            session=session,
            task_type=TaskType.WRITE_SCRIPT_2D,
        )
        
        assert response.agent_name == "developer_2d"
        
        # Should contain GDScript code
        content = response.content
        assert "extends" in content or "func" in content
        assert any(node in content for node in ["CharacterBody2D", "Node2D", "Node"])
    
    @pytest.mark.asyncio
    async def test_developer_3d_writes_code(self, orchestrator):
        """Test Developer3D agent writes GDScript for 3D."""
        session = orchestrator.new_project("3D Game")
        
        response = await orchestrator.run(
            "Write a basic CharacterBody3D movement script with WASD controls",
            session=session,
            task_type=TaskType.WRITE_SCRIPT_3D,
        )
        
        assert response.agent_name == "developer_3d"
        
        # Should contain GDScript code
        content = response.content
        assert "extends" in content or "func" in content
    
    @pytest.mark.asyncio
    async def test_art_director_defines_style(self, orchestrator):
        """Test Art Director agent defines visual style."""
        session = orchestrator.new_project("Fantasy RPG")
        
        response = await orchestrator.run(
            "Define the visual style for a cozy fantasy RPG with a cottage core aesthetic",
            session=session,
            task_type=TaskType.VISUAL_STYLE,
        )
        
        assert response.agent_name == "art_director"
        assert len(response.content) > 50
        
        # Should describe visual elements
        content_lower = response.content.lower()
        assert any(word in content_lower for word in ["color", "style", "visual", "art", "palette"])
    
    @pytest.mark.asyncio
    async def test_qa_reviews_code(self, orchestrator):
        """Test QA agent reviews code."""
        session = orchestrator.new_project("Test Game")
        
        # First add some context about code to review
        session.add_message("human", "Here's my player script")
        session.add_message("agent", """
extends CharacterBody2D

var speed = 200

func _physics_process(delta):
    var velocity = Vector2.ZERO
    if Input.is_action_pressed("move_right"):
        velocity.x += 1
    if Input.is_action_pressed("move_left"):
        velocity.x -= 1
    velocity = velocity.normalized() * speed
    move_and_slide()
""", agent_name="developer_2d")
        
        response = await orchestrator.run(
            "Review the player movement code for potential issues",
            session=session,
            task_type=TaskType.REVIEW,
        )
        
        assert response.agent_name == "qa"
        assert len(response.content) > 50


# ============================================================================
# Auto-Classification Tests
# ============================================================================

class TestAutoClassification:
    """Test the full flow with automatic task classification."""
    
    @pytest.mark.asyncio
    async def test_auto_routes_to_architect(self, orchestrator):
        """Test auto-classification routes concept requests to architect."""
        session = orchestrator.new_project("New Game")
        
        # Don't specify task_type - let it auto-classify
        response = await orchestrator.run(
            "I want to create a game about a robot learning to feel emotions",
            session=session,
        )
        
        # Should route to architect for high-level concept
        assert response.agent_name in ["architect", "designer"]
        assert len(response.content) > 100
    
    @pytest.mark.asyncio
    async def test_auto_routes_to_developer(self, orchestrator):
        """Test auto-classification routes code requests to developer."""
        session = orchestrator.new_project("Platformer")
        
        response = await orchestrator.run(
            "Write GDScript code for a health bar UI that displays player HP",
            session=session,
        )
        
        # Should route to a developer agent
        assert response.agent_name in ["developer_2d", "developer_3d", "designer"]
        assert "func" in response.content or "extends" in response.content or "health" in response.content.lower()


# ============================================================================
# Session History Tests
# ============================================================================

class TestSessionHistory:
    """Test that session history is properly maintained and used."""
    
    @pytest.mark.asyncio
    async def test_history_preserved_across_calls(self, orchestrator):
        """Test that conversation history is preserved."""
        session = orchestrator.new_project("My Game")
        
        # First interaction
        await orchestrator.run(
            "Let's make a puzzle game about matching colors",
            session=session,
            task_type=TaskType.GAME_CONCEPT,
        )
        
        assert len(session.history) == 2  # human + agent
        
        # Second interaction
        await orchestrator.run(
            "How should the scoring system work?",
            session=session,
            task_type=TaskType.MECHANIC_DESIGN,
        )
        
        assert len(session.history) == 4  # 2 + 2
    
    @pytest.mark.asyncio
    async def test_agent_receives_history(self, orchestrator):
        """Test that agents receive conversation history for context."""
        session = orchestrator.new_project("RPG Game")
        
        # Establish context
        await orchestrator.run(
            "We're making a turn-based RPG with a magic system based on elements",
            session=session,
            task_type=TaskType.GAME_CONCEPT,
        )
        
        # Follow-up should reference previous context
        response = await orchestrator.run(
            "Now design the fire element abilities",
            session=session,
            task_type=TaskType.MECHANIC_DESIGN,
        )
        
        # Response should be contextual
        content_lower = response.content.lower()
        assert any(word in content_lower for word in ["fire", "element", "ability", "spell", "magic"])


# ============================================================================
# Pipeline Tests
# ============================================================================

class TestPipelineExecution:
    """Test multi-step pipeline execution with real LLM."""
    
    @pytest.mark.asyncio
    async def test_simple_pipeline(self, orchestrator):
        """Test a simple two-step pipeline."""
        session = orchestrator.new_project("Pipeline Test")
        
        # Create pipeline: design -> implement
        pipeline = (
            Pipeline("design_and_implement", "Design then implement a feature")
            .add_step(
                "design",
                "mechanic_design",
                output_key="design_doc",
            )
            .add_step(
                "implement",
                "implement_feature_2d",
                input_key="design_doc",
                output_key="code",
            )
        )
        
        result = await orchestrator.run_pipeline(
            pipeline,
            session=session,
            initial_input="Create a collectible coin that the player can pick up",
        )
        
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.completed_steps) == 2
        assert "design_doc" in result.outputs
        assert "code" in result.outputs
        
        # The code output should contain GDScript
        code_output = result.outputs["code"]
        assert "func" in code_output or "extends" in code_output
    
    @pytest.mark.asyncio
    async def test_design_review_pipeline(self, orchestrator):
        """Test a design -> review pipeline."""
        session = orchestrator.new_project("Review Test")
        
        pipeline = (
            Pipeline("design_and_review", "Design then review")
            .add_step(
                "design",
                "mechanic_design",
                output_key="design",
            )
            .add_step(
                "review",
                "review",
                input_key="design",
                output_key="review",
            )
        )
        
        result = await orchestrator.run_pipeline(
            pipeline,
            session=session,
            initial_input="Design an inventory system with limited slots",
        )
        
        assert result.status == PipelineStatus.COMPLETED
        assert "design" in result.outputs
        assert "review" in result.outputs


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling with real LLM calls."""
    
    @pytest.mark.asyncio
    async def test_handles_empty_input(self, orchestrator):
        """Test handling of empty input."""
        session = orchestrator.new_project("Test")
        
        response = await orchestrator.run(
            "",
            session=session,
            task_type=TaskType.GAME_CONCEPT,
        )
        
        # Should still get a response (LLM will respond to empty prompt)
        assert response.content is not None
    
    @pytest.mark.asyncio
    async def test_session_saved_after_error_recovery(self, orchestrator):
        """Test that session is saved even after recovering from issues."""
        session = orchestrator.new_project("Recovery Test")
        
        # Make a normal request
        await orchestrator.run(
            "Design a simple game",
            session=session,
            task_type=TaskType.GAME_CONCEPT,
        )
        
        # Session should be saved
        loaded = orchestrator.get_session(session.id)
        assert loaded is not None
        assert len(loaded.history) == 2


# ============================================================================
# Performance / Smoke Tests
# ============================================================================

class TestPerformance:
    """Basic performance and reliability tests."""
    
    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self, orchestrator):
        """Test multiple sequential requests work reliably."""
        session = orchestrator.new_project("Sequential Test")
        
        prompts = [
            ("Design a simple idle clicker game", TaskType.GAME_CONCEPT),
            ("What upgrades should the player be able to buy?", TaskType.MECHANIC_DESIGN),
            ("Write a simple click counter script", TaskType.WRITE_SCRIPT_2D),
        ]
        
        for prompt, task_type in prompts:
            response = await orchestrator.run(
                prompt,
                session=session,
                task_type=task_type,
            )
            assert response.content is not None
            assert len(response.content) > 20
        
        # Should have all interactions in history
        assert len(session.history) == 6  # 3 human + 3 agent
    
    @pytest.mark.asyncio
    async def test_response_time_reasonable(self, orchestrator):
        """Test that response time is reasonable."""
        import time
        
        session = orchestrator.new_project("Timing Test")
        
        start = time.time()
        await orchestrator.run(
            "Describe a simple game concept in 2-3 sentences",
            session=session,
            task_type=TaskType.GAME_CONCEPT,
        )
        elapsed = time.time() - start
        
        # Should complete within 60 seconds (generous for slower hardware)
        assert elapsed < 60, f"Response took too long: {elapsed:.1f}s"


# ============================================================================
# Utility function for manual testing
# ============================================================================

async def detect_ollama_model() -> str:
    """Detect an available Ollama model."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:11434/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError("Ollama not responding")
                
                data = await resp.json()
                models = [m["name"] for m in data.get("models", [])]
                
                if not models:
                    raise RuntimeError("No models installed. Run: ollama pull llama3.2:3b")
                
                # Prefer llama models
                for m in models:
                    if "llama" in m.lower():
                        return m
                
                return models[0]
    except aiohttp.ClientConnectorError:
        raise RuntimeError("Cannot connect to Ollama. Run: ollama serve")


async def interactive_test():
    """Run an interactive test session (for manual debugging)."""
    import tempfile
    
    # First detect available model
    try:
        model_name = await detect_ollama_model()
        print(f"Using Ollama model: {model_name}")
    except RuntimeError as e:
        print(f"Error: {e}")
        return
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # Setup
        config_path = tmp_path / "config"
        config_path.mkdir()
        
        (config_path / "agents.yaml").write_text(f"""
architect:
  name: "architect"
  provider: "ollama"
  model: "{model_name}"
  temperature: 0.7
  max_tokens: 2048

designer:
  name: "designer"
  provider: "ollama"
  model: "{model_name}"
  temperature: 0.7
  max_tokens: 2048

developer_2d:
  name: "developer_2d"
  provider: "ollama"
  model: "{model_name}"
  temperature: 0.3
  max_tokens: 4096
""")
        
        prompts_path = tmp_path / "prompts"
        prompts_path.mkdir()
        
        settings = Settings(
            session_dir=tmp_path / "sessions",
            ollama_host="http://localhost:11434",
            ollama_model=model_name,
        )
        
        orchestrator = Orchestrator(
            settings=settings,
            config_dir=tmp_path,
            approval_callback=lambda msg, decision: True,
        )
        
        session = orchestrator.new_project("Interactive Test")
        
        print("\n" + "=" * 60)
        print("GADS Interactive Test Session")
        print("=" * 60)
        print("Type 'quit' to exit\n")
        
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() == "quit":
                break
            
            print("\nThinking...")
            try:
                response = await orchestrator.run(user_input, session=session)
                print(f"\n[{response.agent_name}]:")
                print(response.content)
            except Exception as e:
                print(f"\nError: {e}")


if __name__ == "__main__":
    # Run interactive test when executed directly
    asyncio.run(interactive_test())
