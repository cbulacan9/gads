# GADS Documentation

Welcome to the Godot Agentic Development System (GADS) documentation.

## What is GADS?

GADS is a multi-agent AI framework for game development with Godot Engine. It combines:

- **AI Agents** - Specialized agents for design, development, art direction, and QA
- **Stable Diffusion** - Generate 2D art assets with optimized game art presets
- **Blender Integration** - Create and export 3D models to Godot
- **Godot Export** - Automatically create runnable Godot 4.x projects

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](quickstart.md) | Get up and running in 5 minutes |
| [CLI Reference](cli-reference.md) | Complete command-line reference |
| [Tools Reference](tools-reference.md) | StableDiffusion, Blender, and Godot tools |
| [Configuration](configuration.md) | Environment setup and configuration |
| [Pipelines](pipelines.md) | Multi-agent workflow pipelines |
| [E2E Testing](e2e_testing.md) | End-to-end testing guide |

## Quick Links

### Getting Started
```bash
# Install
pip install -e .

# Check services
gads check

# Create a project
gads new-project "My Game" --3d
gads export
```

### Generate Assets
```bash
# 2D Art (requires Stable Diffusion)
gads art generate "fantasy sword" --preset pixel_art

# 3D Models (requires Blender)
gads blender create sphere --output ball.glb
```

### AI Assistance
```bash
# Design with AI
gads iterate "Design a combat system" --agent architect

# Generate code
gads iterate "Add player movement" --agent developer_3d
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        GADS CLI                              │
├─────────────────────────────────────────────────────────────┤
│                      Orchestrator                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│
│  │Architect│ │Designer │ │Developer│ │Art Dir. │ │   QA   ││
│  │(Claude) │ │(Ollama) │ │(Ollama) │ │(Claude) │ │(Ollama)││
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘│
├─────────────────────────────────────────────────────────────┤
│                         Tools                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ GodotTool   │  │    SD Tool  │  │BlenderTool  │         │
│  │ (Projects)  │  │ (2D Art)    │  │ (3D Models) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                    External Services                         │
│  ┌─────────┐  ┌─────────────────┐  ┌─────────┐  ┌────────┐ │
│  │ Ollama  │  │Stable Diffusion │  │ Blender │  │ Godot  │ │
│  └─────────┘  └─────────────────┘  └─────────┘  └────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Agents

| Agent | Provider | Purpose |
|-------|----------|---------|
| **Architect** | Claude Opus 4.5 | Game design, creative vision, architecture |
| **Designer** | Ollama (local) | Mechanics, level design, balancing |
| **Developer 2D** | Ollama (local) | GDScript for 2D games |
| **Developer 3D** | Ollama (local) | GDScript for 3D games |
| **Art Director** | Claude Opus 4.5 | Visual style, SD prompts |
| **QA** | Ollama (local) | Testing, code review |

## Tools

| Tool | Purpose | Required |
|------|---------|----------|
| **GodotTool** | Create Godot projects | Built-in |
| **StableDiffusionTool** | Generate 2D art | Optional |
| **BlenderMCPTool** | Create 3D models | Optional |

## Requirements

- Python 3.11+
- Ollama with qwen2.5-coder:14b model
- Optional: Anthropic API key (for Architect/Art Director)
- Optional: Stable Diffusion WebUI with --api
- Optional: Blender 3.0+
- Optional: Godot 4.x

## License

MIT License - See LICENSE file for details.
