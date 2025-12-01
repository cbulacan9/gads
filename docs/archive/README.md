# GADS Archive

This directory contains code that was removed from GADS core to keep the project focused.

## Why Archived?

GADS was originally designed with an integrated creative asset pipeline (Stable Diffusion for 2D art, Hyper3D Rodin for 3D generation). After review, we decided to:

1. **Keep GADS focused** on Godot game development automation (design → code → test)
2. **Separate asset generation** into a potential future project that can serve multiple game engines

The archived code is functional and well-tested. It can seed a future "Asset Pipeline" or "Forge" project.

## Archived Files

| File | Original Location | Purpose |
|------|-------------------|---------|
| `stable_diffusion.py` | `src/gads/tools/` | AUTOMATIC1111 WebUI integration with 9 art presets |
| `art_director.py` | `src/gads/agents/` | Agent for visual style and SD prompt generation |
| `blender_hyper3d.py` | `src/gads/tools/blender_mcp.py` | Hyper3D Rodin AI 3D generation (extracted) |

## If You Want to Use This Code

### Stable Diffusion Tool

Requires AUTOMATIC1111 WebUI running with `--api` flag:

```python
from stable_diffusion import StableDiffusionTool, ArtPreset

tool = StableDiffusionTool(api_url="http://localhost:7860")
result = await tool.generate_with_preset(
    prompt="fantasy sword, game item",
    preset=ArtPreset.PIXEL_ART,
)
```

### Hyper3D Rodin Tool

Requires Blender MCP addon with Hyper3D enabled and API key:

```python
from blender_hyper3d import Hyper3DRodinTool

tool = Hyper3DRodinTool(mcp_caller=my_mcp_caller)
result = await tool.generate_from_text("a treasure chest")
# Poll for completion, then import
```

### Art Director Agent

Was designed to work with the above tools. Would need adaptation for standalone use.

## Date Archived

December 2024

## Related

- Original spec: `GADS_Specification_v0.2.md` (Phases 4-5 described creative pipeline)
- Current GADS focuses on Phases 1-3: Foundation, Core Agents, Review System
