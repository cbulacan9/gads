"""
Architect Agent for GADS

High-level game design, system architecture, and creative direction.
Uses Claude Opus 4.5 for complex reasoning and creative tasks.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, AgentConfig, AgentResponse


class ArchitectAgent(BaseAgent):
    """
    The Architect agent handles high-level design decisions.
    
    Responsibilities:
    - Game concept development
    - System architecture design
    - Creative direction
    - Cross-cutting design decisions
    - Coordination of other agents
    """
    
    def _default_system_prompt(self) -> str:
        return """You are the Architect agent in the GADS (Godot Agentic Development System).

Your role is to provide high-level game design, system architecture, and creative direction for Godot 4.x game projects.

## Responsibilities

1. **Game Concept Development**
   - Transform vague ideas into concrete game concepts
   - Define core gameplay loops and player experience goals
   - Identify target audience and platform considerations

2. **System Architecture**
   - Design the overall structure of the Godot project
   - Define scene hierarchy and node organization
   - Specify autoloads, signals, and communication patterns
   - Plan for scalability and maintainability

3. **Creative Direction**
   - Establish the game's tone, theme, and aesthetic direction
   - Guide the visual and audio style
   - Ensure consistency across all game elements

4. **Technical Decisions**
   - Choose appropriate Godot features for requirements
   - Recommend design patterns (State machines, ECS-like, etc.)
   - Identify potential technical challenges early

## Output Format

When designing a game concept, provide:
- **Title**: Working title for the project
- **Elevator Pitch**: One-sentence description
- **Core Loop**: The primary gameplay cycle
- **Key Features**: 3-5 main features
- **Technical Approach**: High-level Godot implementation strategy

When designing architecture, provide:
- **Scene Structure**: Main scenes and their purposes
- **Core Systems**: Autoloads and managers needed
- **Data Flow**: How information moves through the game
- **Extension Points**: Where new features can be added

Always consider Godot 4.x best practices and GDScript conventions.
Be specific about node types, signal patterns, and resource usage.
"""
    
    async def execute(
        self,
        user_input: str,
        context: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """Execute architect tasks."""
        
        # Build context-aware prompt
        project_context = self._build_project_context(context)
        
        messages = []
        
        # Add relevant history
        if history:
            messages.extend(history[-10:])  # Last 10 messages for context
        
        # Add current request with context
        enhanced_input = f"{project_context}\n\n## Current Request\n\n{user_input}"
        messages.append({"role": "user", "content": enhanced_input})
        
        # Call LLM
        response_text = await self._call_llm(messages)
        
        # Parse response for any structured outputs
        artifacts = self._extract_artifacts(response_text)
        
        return AgentResponse(
            content=response_text,
            agent_name=self.name,
            model=self.config.model,
            artifacts=artifacts,
            suggested_next_agent=self._suggest_next_agent(response_text),
        )
    
    def _build_project_context(self, context: dict[str, Any]) -> str:
        """Build a context string from project state."""
        parts = ["## Project Context"]
        
        if "project" in context:
            project = context["project"]
            parts.append(f"**Project**: {project.get('name', 'Unnamed')}")
            if project.get("description"):
                parts.append(f"**Description**: {project['description']}")
            if project.get("current_phase"):
                parts.append(f"**Phase**: {project['current_phase']}")
        
        if "game_design_doc" in context and context["game_design_doc"]:
            parts.append("\n### Existing Design")
            parts.append(str(context["game_design_doc"]))
        
        return "\n".join(parts) if len(parts) > 1 else ""
    
    def _extract_artifacts(self, response: str) -> dict[str, Any]:
        """Extract structured artifacts from the response."""
        artifacts = {}
        
        # Look for code blocks
        import re
        code_blocks = re.findall(r"```(\w+)?\n(.*?)```", response, re.DOTALL)
        if code_blocks:
            artifacts["code_blocks"] = [
                {"language": lang or "text", "code": code.strip()}
                for lang, code in code_blocks
            ]
        
        # Look for structured sections
        if "## Scene Structure" in response or "## Core Systems" in response:
            artifacts["has_architecture"] = True
        
        if "## Core Loop" in response or "## Key Features" in response:
            artifacts["has_game_concept"] = True
        
        return artifacts
    
    def _suggest_next_agent(self, response: str) -> str | None:
        """Suggest which agent should handle the next step."""
        response_lower = response.lower()
        
        if any(kw in response_lower for kw in ["implement", "code this", "create script"]):
            return "developer"
        if any(kw in response_lower for kw in ["visual style", "art direction", "aesthetic"]):
            return "art_director"
        if any(kw in response_lower for kw in ["mechanic details", "balance", "gameplay"]):
            return "designer"
        
        return None
