# GADS - Godot Agentic Development System

A multi-agent AI framework for game development with Godot Engine.

![Version](https://img.shields.io/badge/version-0.2-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Godot](https://img.shields.io/badge/godot-4.x-purple)

## Features

- 🤖 **Multi-Agent System** - Specialized AI agents for design, development, art, and QA
- 🎨 **Art Generation** - Create 2D assets with Stable Diffusion (9 game art presets)
- 🎲 **3D Models** - Generate and export 3D primitives with Blender
- 🎮 **Godot Export** - Automatically create runnable Godot 4.x projects
- 🔄 **Pipelines** - Multi-agent workflows for complex tasks

## Quick Start

```bash
# Install
git clone <repository>
cd gads
pip install -e .

# Setup Ollama
ollama serve
ollama pull qwen2.5-coder:14b

# Verify
gads check

# Create a game!
gads new-project "Space Shooter" --2d
gads export
godot --path "./projects/space_shooter"
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                       GADS CLI                            │
├──────────────────────────────────────────────────────────┤
│   Architect    Designer    Developer    Art Dir.    QA   │
│   (Claude)     (Ollama)    (Ollama)     (Claude)  (Ollama)│
├──────────────────────────────────────────────────────────┤
│   GodotTool        SD Tool           BlenderTool         │
│   (Projects)       (2D Art)          (3D Models)         │
└──────────────────────────────────────────────────────────┘
```

## CLI Commands

### Project Management
```bash
gads new-project "Name" --3d          # Create project
gads export                            # Export to Godot
gads status                            # Show status
gads sessions                          # List sessions
gads iterate "Add feature..."          # Modify project
```

### Art Generation (Stable Diffusion)
```bash
gads art check                         # Check SD connection
gads art presets                       # List art presets
gads art generate "prompt" --preset pixel_art
gads art to-project "prompt" -p ./project
```

### 3D Models (Blender)
```bash
gads blender check                     # Check Blender
gads blender create cube -o model.glb  # Create primitive
gads blender create-to-project sphere -p ./project
```

### Pipelines
```bash
gads pipeline list                     # List pipelines
gads pipeline run new-game "A roguelike deckbuilder"
```

## Art Presets

| Preset | Size | Best For |
|--------|------|----------|
| `pixel_art` | 512x512 | Retro sprites |
| `sprite` | 512x512 | Character sprites |
| `texture` | 512x512 | Tileable textures |
| `ui_icon` | 256x256 | Interface icons |
| `concept_art` | 1024x768 | Illustrations |
| `character` | 768x1024 | Character sheets |
| `environment` | 1024x576 | Backgrounds |

## Configuration

Create `.env` in project root:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b

# Optional - Stable Diffusion
SD_API_URL=http://localhost:7860

# Optional - Blender
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

## Requirements

| Service | Required | Purpose |
|---------|----------|---------|
| Ollama | ✅ Yes | Local LLM for most agents |
| Anthropic API | ⚡ Recommended | High-quality Architect/Art Director |
| Stable Diffusion | ❌ Optional | 2D art generation |
| Blender | ❌ Optional | 3D model creation |
| Godot | ❌ Optional | Run exported projects |

## Documentation

- [Quick Start Guide](docs/quickstart.md)
- [CLI Reference](docs/cli-reference.md)
- [Tools Reference](docs/tools-reference.md)
- [Configuration](docs/configuration.md)
- [Pipelines](docs/pipelines.md)

## Example Workflow

```bash
# 1. Create project
gads new-project "Dragon Quest" --3d -d "Fantasy adventure game"

# 2. Design with AI
gads iterate "Design a combat system with melee and magic" --agent architect

# 3. Export to Godot
gads export

# 4. Generate art
gads art to-project "fire dragon" --preset character --name dragon -p ./projects/dragon_quest

# 5. Create 3D placeholder
gads blender create-to-project monkey --name dragon_model -p ./projects/dragon_quest

# 6. Open in Godot
godot --path "./projects/dragon_quest"
```

## Contributing

Contributions welcome! Please read the contributing guidelines first.

## License

MIT License - see LICENSE file for details.
