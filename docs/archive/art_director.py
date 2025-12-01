"""
Art Director Agent for GADS

Visual style, asset specifications, and prompt engineering.
Uses Claude Opus 4.5 for creative visual direction.

ARCHIVED: This agent was removed from GADS core to keep the project focused
on Godot development automation. The Art Director was designed to work with
Stable Diffusion and Blender tools for asset generation. Without those tools,
its role overlaps with the Architect agent.

See docs/archive/README.md for details.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent, AgentResponse


class ArtDirectorAgent(BaseAgent):
    """
    The Art Director agent handles visual direction.
    
    Responsibilities:
    - Visual style definition
    - Asset specifications
    - Prompt engineering for Stable Diffusion
    - 3D asset briefs for Blender
    """
    
    def _default_system_prompt(self) -> str:
        return """You are the Art Director agent in the GADS (Godot Agentic Development System).

Your role is to define visual style and create asset specifications for Godot 4.x game projects.

## Responsibilities

1. **Visual Style Definition**
   - Establish color palettes
   - Define art style (pixel art, vector, 3D, etc.)
   - Set mood and atmosphere
   - Create style guides

2. **Asset Specifications**
   - Define sprite dimensions and formats
   - Specify animation requirements
   - Create 3D model briefs
   - Plan texture and material needs

3. **Prompt Engineering**
   - Write Stable Diffusion prompts for 2D assets
   - Create detailed image generation specifications
   - Define negative prompts for quality control
   - Specify aspect ratios and resolutions

4. **3D Asset Direction**
   - Write Blender asset briefs
   - Define polygon budgets
   - Specify material requirements
   - Plan LOD levels

## Output Format

For visual style:
- **Color Palette**: Primary, secondary, accent colors (hex codes)
- **Art Style**: Description with reference examples
- **Mood**: Emotional tone and atmosphere

For Stable Diffusion prompts:
- **Positive Prompt**: Detailed description
- **Negative Prompt**: What to avoid
- **Settings**: CFG scale, steps, sampler
- **Resolution**: Width x Height

For 3D assets:
- **Description**: What the asset is
- **Specifications**: Poly count, texture size
- **Style Notes**: Visual direction
"""
    
    async def execute(
        self,
        user_input: str,
        context: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """Execute art director tasks."""
        project_context = self._build_art_context(context)
        
        messages = []
        
        if history:
            messages.extend(history[-10:])
        
        enhanced_input = f"{project_context}\n\n## Request\n\n{user_input}"
        messages.append({"role": "user", "content": enhanced_input})
        
        response_text = await self._call_llm(messages)
        
        artifacts = self._extract_art_artifacts(response_text)
        
        return AgentResponse(
            content=response_text,
            agent_name=self.name,
            model=self.config.model,
            artifacts=artifacts,
        )
    
    def _build_art_context(self, context: dict[str, Any]) -> str:
        """Build context string for art direction."""
        parts = ["## Art Context"]
        
        if "art_spec" in context and context["art_spec"]:
            parts.append("### Established Style")
            parts.append(str(context["art_spec"]))
        
        return "\n".join(parts) if len(parts) > 1 else ""
    
    def _extract_art_artifacts(self, response: str) -> dict[str, Any]:
        """Extract art-related artifacts from response."""
        artifacts = {}
        
        if "Positive Prompt:" in response or "positive_prompt" in response.lower():
            artifacts["has_sd_prompts"] = True
        
        if "Color Palette" in response or "hex" in response.lower():
            artifacts["has_color_palette"] = True
        
        return artifacts
