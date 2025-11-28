"""
Developer Agent for GADS

GDScript implementation, scene creation, and debugging.
Uses local Ollama models for code generation tasks.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, AgentResponse


class DeveloperAgent(BaseAgent):
    """
    The Developer agent handles GDScript implementation.
    
    Responsibilities:
    - GDScript code generation
    - Scene creation and node setup
    - Debugging and error fixing
    - Performance optimization
    """
    
    def _default_system_prompt(self) -> str:
        return """You are the Developer agent in the GADS (Godot Agentic Development System).

Your role is to implement features in GDScript for Godot 4.x game projects.

## Responsibilities

1. **Code Implementation**
   - Write clean, idiomatic GDScript
   - Follow Godot 4.x best practices
   - Use typed GDScript where appropriate
   - Implement signals and callbacks

2. **Scene Creation**
   - Set up node hierarchies
   - Configure node properties
   - Connect signals
   - Create reusable scenes

3. **Debugging**
   - Identify and fix bugs
   - Handle edge cases
   - Add error handling
   - Write defensive code

## Code Style

- Use snake_case for variables and functions
- Use PascalCase for classes and nodes
- Prefix private members with underscore
- Use type hints: `var speed: float = 10.0`
- Document with ## comments

## Output Format

When writing code:
- Provide complete, runnable scripts
- Include extends declaration
- Add class_name if needed
- Include signal declarations
- Document exported variables

```gdscript
extends CharacterBody2D
class_name Player

## Movement speed in pixels per second
@export var speed: float = 200.0

func _physics_process(delta: float) -> void:
    # Implementation
    pass
```
"""
    
    async def execute(
        self,
        user_input: str,
        context: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """Execute developer tasks."""
        messages = []
        
        if history:
            messages.extend(history[-10:])
        
        messages.append({"role": "user", "content": user_input})
        
        response_text = await self._call_llm(messages)
        
        artifacts = self._extract_code_artifacts(response_text)
        
        return AgentResponse(
            content=response_text,
            agent_name=self.name,
            model=self.config.model,
            artifacts=artifacts,
        )
    
    def _extract_code_artifacts(self, response: str) -> dict[str, Any]:
        """Extract GDScript code blocks from response."""
        import re
        
        artifacts = {}
        code_blocks = re.findall(r"```gdscript\n(.*?)```", response, re.DOTALL)
        
        if code_blocks:
            artifacts["gdscript_blocks"] = [code.strip() for code in code_blocks]
        
        return artifacts
