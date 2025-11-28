# End-to-End Testing with Ollama

This guide explains how to run the end-to-end tests that verify GADS works correctly with a real Ollama LLM backend.

## Prerequisites

1. **Ollama installed and running**
   ```bash
   # Install from https://ollama.ai
   # Then start the server:
   ollama serve
   ```

2. **Required model pulled**
   ```bash
   ollama pull llama3.1:8b
   ```

3. **GADS installed in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

## Quick Start

### 1. Check Service Health

First, verify all services are running:

```bash
# Using the CLI
gads check

# Or using the test script
python tests/health_check.py
```

You should see:
```
GADS Service Health Check

┌─────────────────┬───────────────────────────┬──────────────────┬──────────┐
│ Service         │ Status                    │ Details          │ Required │
├─────────────────┼───────────────────────────┼──────────────────┼──────────┤
│ Ollama          │ ✓ Running with 3 model(s) │ llama3.1:8b, ... │ Yes      │
│ Stable Diffusion│ ○ Cannot connect          │ -                │ No       │
│ Blender MCP     │ ○ Cannot connect          │ -                │ No       │
└─────────────────┴───────────────────────────┴──────────────────┴──────────┘

✓ Ready to run GADS
```

### 2. Run End-to-End Tests

```bash
# Run all e2e tests
pytest tests/test_e2e_ollama.py -v --run-e2e

# Run specific test class
pytest tests/test_e2e_ollama.py::TestAgentExecution -v --run-e2e

# Run a single test
pytest tests/test_e2e_ollama.py::TestAgentExecution::test_architect_generates_concept -v --run-e2e
```

### 3. Run Interactive Test (Manual)

For manual testing and debugging:

```bash
python tests/test_e2e_ollama.py
```

This starts an interactive session where you can chat with the agents.

## Test Categories

### Router Classification Tests
Tests that the LLM-based router correctly classifies different types of requests:
- Game concepts → Architect
- Mechanics → Designer
- 2D code → Developer2D
- 3D code → Developer3D
- Visual style → Art Director

### Agent Execution Tests
Tests that each agent produces reasonable output:
- Architect generates game concepts
- Designer creates mechanics
- Developer2D writes GDScript for 2D
- Developer3D writes GDScript for 3D
- Art Director defines visual styles
- QA reviews code

### Auto-Classification Tests
Tests the full flow where the router automatically determines which agent to use.

### Session History Tests
Tests that conversation history is properly maintained and passed to agents.

### Pipeline Tests
Tests multi-step workflows where output from one agent feeds into the next.

## Running in CI

The e2e tests are skipped by default in CI (no `--run-e2e` flag). To include them:

```yaml
# GitHub Actions example
- name: Run e2e tests
  run: |
    ollama serve &
    sleep 5
    ollama pull llama3.1:8b
    pytest tests/test_e2e_ollama.py -v --run-e2e
```

## Troubleshooting

### "Ollama not available" error

1. Check Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. If not running, start it:
   ```bash
   ollama serve
   ```

### "No llama3 model found" error

Pull the required model:
```bash
ollama pull llama3.1:8b
```

### Tests timing out

Increase the timeout in pytest:
```bash
pytest tests/test_e2e_ollama.py -v --run-e2e --timeout=120
```

### Response quality issues

The tests use fairly loose assertions since LLM output varies. If tests are failing due to response content:

1. Check the model is working: `ollama run llama3.1:8b "Hello"`
2. Review the system prompts in `prompts/`
3. Try a different model size if available

## Writing New E2E Tests

When adding new e2e tests:

1. Mark them with `@pytest.mark.e2e` or place in `test_e2e_*.py`
2. Use the `orchestrator` fixture for full system tests
3. Use `ollama_available` fixture to skip if Ollama isn't running
4. Keep assertions flexible (LLM output varies)
5. Test behavior, not exact output

Example:
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_my_feature(orchestrator):
    session = orchestrator.new_project("Test")
    response = await orchestrator.run(
        "My test prompt",
        session=session,
        task_type=TaskType.GAME_CONCEPT,
    )
    assert response.agent_name == "architect"
    assert len(response.content) > 50
```
