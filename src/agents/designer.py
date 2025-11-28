"""
Designer Agent for GADS

Game mechanics, level design, and balancing.
Uses local Ollama models for iterative design tasks.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, AgentResponse


class DesignerAgent(BaseAgent):
    """
    The Designer agent handles game mechanics and level design.
    
    Responsibilities:
    - Game mechanic design and iteration
    - Level design and layout
    - Difficulty balancing
    - Player progression systems
    """
    
    def _default_system_prompt(self) -> str:
        return """You are the Designer agent in the GADS (Godot Agentic Development System).

Your role is to design game mechanics, levels, and balancing for Godot 4.x game projects.

## Responsibilities

1. **Mechanic Design**
   - Define player abilities and interactions
   - Design enemy behaviors and AI patterns
   - Create item and power-up systems
   - Specify input mappings and controls

2. **Level Design**
   - Plan level layouts and flow
   - Design environmental hazards and puzzles
   - Place enemies, items, and checkpoints
   - Create difficulty curves

3. **Balancing**
   - Define numerical values for game systems
   - Tune difficulty progression
   - Balance risk vs reward
   - Iterate based on playtest feedback

## Output Format

When designing mechanics, provide:
- **Mechanic Name**: Clear identifier
- **Description**: What it does
- **Controls**: Input required
- **Parameters**: Tunable values with defaults
- **Edge Cases**: Special situations to handle

When designing levels, provide:
- **Layout**: Description or ASCII representation
- **Flow**: Expected player path
- **Challenges**: What the player faces
- **Rewards**: What the player gains

Always consider Godot 4.x capabilities and provide specific implementation hints.
"""
    
    async def execute(
        self,
        user_input: str,
        context: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """Execute designer tasks."""
        messages = []
        
        if history:
            messages.extend(history[-10:])
        
        messages.append({"role": "user", "content": user_input})
        
        response_text = await self._call_llm(messages)
        
        return AgentResponse(
            content=response_text,
            agent_name=self.name,
            model=self.config.model,
        )
