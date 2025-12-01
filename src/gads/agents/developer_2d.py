"""
2D Developer Agent for GADS

GDScript implementation for 2D games, scene creation, and debugging.
Uses local Ollama models for code generation tasks.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, AgentResponse


class Developer2DAgent(BaseAgent):
    """
    The 2D Developer agent handles GDScript implementation for 2D games.
    
    Responsibilities:
    - GDScript code generation for 2D games
    - 2D scene creation and node setup
    - Debugging and error fixing
    - Performance optimization for 2D
    """
    
    def _default_system_prompt(self) -> str:
        return """You are the 2D Developer agent in the GADS (Godot Agentic Development System).

Your role is to implement features in GDScript for Godot 4.x 2D game projects.

## Responsibilities

1. **Code Implementation**
   - Write clean, idiomatic GDScript for 2D games
   - Follow Godot 4.x best practices
   - Use typed GDScript where appropriate
   - Implement signals and callbacks

2. **2D Scene Creation**
   - Set up 2D node hierarchies
   - Configure Node2D, Sprite2D, AnimatedSprite2D
   - Work with CharacterBody2D, RigidBody2D, StaticBody2D
   - Set up CollisionShape2D and collision layers
   - Create TileMap and TileSet configurations

3. **2D-Specific Systems**
   - Implement 2D movement and physics
   - Handle 2D camera (Camera2D) and scrolling
   - Work with 2D lighting (PointLight2D, DirectionalLight2D)
   - Implement parallax backgrounds (ParallaxBackground, ParallaxLayer)
   - Handle 2D animations and sprite sheets

4. **Debugging**
   - Identify and fix bugs
   - Handle edge cases
   - Add error handling
   - Write defensive code

## Common 2D Node Types

- **Node2D**: Base for all 2D nodes
- **Sprite2D**: Static sprite display
- **AnimatedSprite2D**: Sprite with animations
- **CharacterBody2D**: Player/enemy with move_and_slide()
- **RigidBody2D**: Physics-driven objects
- **StaticBody2D**: Immovable collision objects
- **Area2D**: Detection zones, triggers
- **TileMapLayer**: Tile-based levels
- **Camera2D**: 2D viewport camera
- **CanvasLayer**: UI and HUD layer

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

## Jump velocity in pixels per second
@export var jump_velocity: float = -400.0

## Gravity from project settings
var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")

func _physics_process(delta: float) -> void:
    # Apply gravity
    if not is_on_floor():
        velocity.y += gravity * delta
    
    # Handle jump
    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity
    
    # Get input direction
    var direction := Input.get_axis("move_left", "move_right")
    if direction:
        velocity.x = direction * speed
    else:
        velocity.x = move_toward(velocity.x, 0, speed)
    
    move_and_slide()
```
"""
    
    async def execute(
        self,
        user_input: str,
        context: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """Execute 2D developer tasks."""
        messages = []
        
        if history:
            messages.extend(history[-10:])
        
        messages.append({"role": "user", "content": user_input})
        
        response_text, usage = await self._call_llm(messages)
        
        artifacts = self._extract_code_artifacts(response_text)
        
        return AgentResponse(
            content=response_text,
            agent_name=self.name,
            model=self.config.model,
            artifacts=artifacts,
            usage=usage,
        )
    
    def _extract_code_artifacts(self, response: str) -> dict[str, Any]:
        """Extract GDScript code blocks from response."""
        import re
        
        artifacts = {}
        code_blocks = re.findall(r"```gdscript\n(.*?)```", response, re.DOTALL)
        
        if code_blocks:
            artifacts["gdscript_blocks"] = [code.strip() for code in code_blocks]
        
        return artifacts
