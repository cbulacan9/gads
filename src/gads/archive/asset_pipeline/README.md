# Asset Pipeline Archive

This directory contains archived code from GADS that was originally intended for creative asset generation. This code has been separated from the core GADS project to maintain focus on the Godot development workflow.

## Why Archived?

The asset generation pipeline (Stable Diffusion, Hyper3D Rodin, AI 3D generation) represents a different problem domain from the core GADS mission:

1. **Different execution context**: GADS agents run via Ollama locally; AI asset generation often requires Claude's MCP session or external cloud APIs
2. **Different workflows**: Design→Code→Test cycles differ fundamentally from Prompt→Generate→Refine→Approve cycles
3. **Different maturity levels**: GADS agent framework is stable; AI 3D generation APIs evolve weekly
4. **Scope management**: Keeping these separate allows each to evolve independently

## Contents

### tools/
- `stable_diffusion.py` - AUTOMATIC1111 WebUI API integration with game art presets
- `blender_hyper3d.py` - Hyper3D Rodin integration (extracted from blender_mcp.py)

### agents/
- `art_director.py` - Agent for visual style, asset specs, and SD prompt generation

## Potential Future Use

This code could be repurposed into a standalone "Asset Forge" or similar project that:
- Integrates with Claude's MCP for Blender/Hyper3D
- Provides a dedicated UI for asset generation workflows
- Serves multiple game engines (not just Godot)
- Operates as a companion tool to GADS

## Original CLI Commands (Removed from GADS)

```bash
# Art generation
gads art check
gads art presets
gads art generate "prompt" --preset pixel_art
gads art to-project "prompt" --type sprites

# Hyper3D Rodin
gads blender rodin check
gads blender rodin info
```

## Dependencies

If reviving this code, you'll need:
- `aiohttp` (for Stable Diffusion API)
- AUTOMATIC1111 WebUI running with `--api` flag
- Blender MCP addon with Hyper3D enabled
- Hyper3D API key or fal.ai account

---
Archived: December 2024
