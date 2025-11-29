# GADS CLI Reference

Complete command-line interface reference for the Godot Agentic Development System.

## Overview

GADS provides a rich CLI for managing game development projects with AI assistance. The CLI is organized into command groups:

- **Project Commands** - Create and manage projects
- **Agent Commands** - Interact with AI agents
- **Art Commands** - Generate 2D art with Stable Diffusion
- **Blender Commands** - Create 3D models with Blender
- **Pipeline Commands** - Run multi-agent workflows

## Installation

```bash
# Clone and install
git clone <repository>
cd gads
pip install -e .

# Verify installation
gads --help
```

## Quick Start

```bash
# 1. Check services are running
gads check

# 2. Create a new project
gads new-project "My Game" --3d -d "A 3D adventure game"

# 3. Export to Godot
gads export

# 4. Generate art assets
gads art generate "fantasy sword" --preset pixel_art --name sword

# 5. Create 3D models
gads blender create-to-project sphere --name player -p ./projects/my_game

# 6. Open in Godot
godot --path "./projects/my_game"
```

---

## Project Commands

### `gads new-project`

Create a new game project with AI-assisted design.

```bash
gads new-project "Project Name" [OPTIONS]
```

**Arguments:**
- `NAME` - Name for the new game project (required)

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--description` | `-d` | Project description |
| `--2d` | | Create a 2D project (default) |
| `--3d` | | Create a 3D project |
| `--style` | `-s` | Art style (e.g., 'pixel-art', 'low-poly') |
| `--prompt` | `-p` | Initial prompt for the Architect agent |
| `--yes` | `-y` | Skip approval prompts |

**Examples:**
```bash
# Simple 2D project
gads new-project "Pixel Quest"

# 3D project with description
gads new-project "Space Explorer" --3d -d "A sci-fi exploration game"

# With art style and initial prompt
gads new-project "Retro RPG" --2d --style pixel-art -p "Design a turn-based combat system"
```

### `gads export`

Export a session to a Godot project.

```bash
gads export [OPTIONS]
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--output` | `-o` | Output directory for Godot project |
| `--session` | `-s` | Session ID to export |
| `--open` | | Open project in Godot after export |

**Examples:**
```bash
# Export current session
gads export

# Export to specific directory
gads export -o ./my-games

# Export and open in Godot
gads export --open
```

**What Gets Exported:**
- `project.godot` - Godot project configuration
- `scenes/main.tscn` - Main scene with camera, lighting, environment
- `scripts/` - All GDScript files from session
- `assets/` - Folder structure for sprites, textures, models, audio
- `autoloads/game_manager.gd` - Global game manager singleton

### `gads status`

Show the status of the current session and project.

```bash
gads status [OPTIONS]
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--session` | `-s` | Session ID to check |

### `gads sessions`

List all saved sessions.

```bash
gads sessions
```

### `gads iterate`

Iterate on an existing project with a natural language instruction.

```bash
gads iterate "instruction" [OPTIONS]
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--session` | `-s` | Session ID to continue |
| `--agent` | `-a` | Force specific agent |
| `--yes` | `-y` | Skip approval prompts |

**Available Agents:** `architect`, `designer`, `developer_2d`, `developer_3d`, `art_director`, `qa`

**Examples:**
```bash
# Auto-route to appropriate agent
gads iterate "Add a double-jump mechanic"

# Force specific agent
gads iterate "Review the player controller code" --agent qa
```

### `gads agents`

List available agents and their roles.

```bash
gads agents
```

### `gads check`

Check connectivity to all external services.

```bash
gads check
```

**Checks:**
- Ollama (required) - Local LLM inference
- Stable Diffusion (optional) - Image generation
- Blender (optional) - 3D model creation

---

## Art Commands

Generate 2D art assets using Stable Diffusion.

### `gads art check`

Check Stable Diffusion API connectivity.

```bash
gads art check
```

**Requirements:**
- Stable Diffusion WebUI running with `--api` flag
- Default URL: `http://localhost:7860`

### `gads art presets`

List available art generation presets.

```bash
gads art presets
```

**Available Presets:**

| Preset | Size | Steps | Best For |
|--------|------|-------|----------|
| `pixel_art` | 512x512 | 25 | Retro pixel art sprites and tiles |
| `low_poly` | 768x768 | 25 | Low-poly 3D style renders |
| `concept_art` | 1024x768 | 30 | Detailed concept art and illustrations |
| `ui_icon` | 256x256 | 20 | Simple game UI icons |
| `sprite` | 512x512 | 25 | 2D game character sprites |
| `texture` | 512x512 | 25 | Seamless tileable textures |
| `character` | 768x1024 | 30 | Character design sheets |
| `environment` | 1024x576 | 30 | Environment and background art |
| `custom` | 512x512 | 20 | Custom settings (no modifications) |

### `gads art generate`

Generate an image using Stable Diffusion.

```bash
gads art generate "prompt" [OPTIONS]
```

**Arguments:**
- `PROMPT` - Description of the image to generate (required)

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--preset` | `-p` | Art style preset | `concept_art` |
| `--output` | `-o` | Output directory | `./generated` |
| `--name` | `-n` | Base name for output files | `image` |
| `--width` | `-W` | Override width | (from preset) |
| `--height` | `-H` | Override height | (from preset) |
| `--steps` | | Override sampling steps | (from preset) |
| `--seed` | | Random seed (-1 for random) | `-1` |
| `--batch` | `-b` | Number of images to generate | `1` |
| `--negative` | | Additional negative prompt | (none) |

**Examples:**
```bash
# Basic generation
gads art generate "a fantasy sword, game item"

# With preset
gads art generate "knight character" --preset sprite --name knight

# Custom size and batch
gads art generate "forest background" --preset environment -W 1920 -H 1080 --batch 4

# With seed for reproducibility
gads art generate "pixel art treasure chest" --preset pixel_art --seed 12345
```

### `gads art to-project`

Generate art and save directly to a Godot project.

```bash
gads art to-project "prompt" [OPTIONS]
```

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--preset` | | Art style preset | `concept_art` |
| `--type` | `-t` | Asset type folder | `sprites` |
| `--name` | `-n` | Base name for output files | `asset` |
| `--session` | `-s` | Session ID to get project from | (current) |
| `--project` | `-p` | Direct path to Godot project | (from session) |
| `--batch` | `-b` | Number of images to generate | `1` |

**Asset Types:** `sprites`, `textures`, `concept_art`, `ui`

**Examples:**
```bash
# Generate to current project
gads art to-project "player character" --preset sprite --name hero

# Generate to specific project
gads art to-project "stone wall" --preset texture -t textures -p ./projects/my_game

# Generate UI icons
gads art to-project "health potion icon" --preset ui_icon -t ui --name health_potion
```

---

## Blender Commands

Create and export 3D models using Blender.

### `gads blender check`

Check Blender availability.

```bash
gads blender check
```

**Requirements:**
- Blender installed and in PATH, or
- `BLENDER_PATH` set in `.env`

### `gads blender scene`

Show Blender scene info (from default scene).

```bash
gads blender scene [OPTIONS]
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--file` | `-f` | Path to .blend file to inspect |

### `gads blender create`

Create a primitive mesh and optionally export to GLB.

```bash
gads blender create PRIMITIVE [OPTIONS]
```

**Arguments:**
- `PRIMITIVE` - Primitive type (required)

**Available Primitives:** `cube`, `sphere`, `cylinder`, `plane`, `cone`, `torus`, `monkey`

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--name` | `-n` | Name for the object | (primitive name) |
| `--output` | `-o` | Export directly to GLB file | (none) |
| `--scale` | `-s` | Uniform scale | `1.0` |

**Examples:**
```bash
# Create and export a cube
gads blender create cube --output ./models/cube.glb

# Create scaled sphere
gads blender create sphere --output ball.glb --scale 2.0

# Create Suzanne (monkey)
gads blender create monkey --output suzanne.glb --name "Suzanne"
```

### `gads blender export`

Export a .blend file to GLB/FBX/OBJ.

```bash
gads blender export OUTPUT [OPTIONS]
```

**Arguments:**
- `OUTPUT` - Output file path (required)

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--file` | `-f` | Path to .blend file to export | (default scene) |
| `--format` | | Export format | `glb` |

**Supported Formats:** `glb`, `gltf`, `fbx`, `obj`

**Examples:**
```bash
# Export default scene to GLB
gads blender export model.glb

# Export .blend file to FBX
gads blender export character.fbx --file ./character.blend --format fbx
```

### `gads blender create-to-project`

Create a primitive and export directly to a Godot project.

```bash
gads blender create-to-project PRIMITIVE [OPTIONS]
```

**Arguments:**
- `PRIMITIVE` - Primitive type (required)

**Options:**
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--name` | `-n` | Name for the model file | (primitive name) |
| `--scale` | `-s` | Uniform scale | `1.0` |
| `--session` | | Session ID to get project from | (current) |
| `--project` | `-p` | Direct path to Godot project | (from session) |

**Examples:**
```bash
# Create sphere in current project
gads blender create-to-project sphere --name player_placeholder

# Create in specific project with scale
gads blender create-to-project monkey --name enemy -s 0.5 -p ./projects/my_game
```

### `gads blender to-project`

Export a .blend file directly to a Godot project.

```bash
gads blender to-project NAME [OPTIONS]
```

**Arguments:**
- `NAME` - Name for the exported model (default: `model`)

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--file` | `-f` | Path to .blend file to export |
| `--session` | `-s` | Session ID to get project from |
| `--project` | | Direct path to Godot project |

---

## Pipeline Commands

Run multi-agent workflows.

### `gads pipeline list`

List all available pipelines.

```bash
gads pipeline list
```

### `gads pipeline run`

Run a multi-agent pipeline.

```bash
gads pipeline run NAME "prompt" [OPTIONS]
```

**Arguments:**
- `NAME` - Name of the pipeline to run (required)
- `PROMPT` - Initial prompt for the pipeline (required)

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--session` | `-s` | Session ID to continue |
| `--yes` | `-y` | Skip approval prompts |

**Built-in Pipelines:**
- `new-game` - Create complete game concept
- `feature` - Design, implement, and review a feature
- `asset` - Create asset specifications and SD prompts
- `iterate` - Review and improve existing code

**Examples:**
```bash
# Create new game concept
gads pipeline run new-game "A roguelike deckbuilder with cooking mechanics"

# Add a feature
gads pipeline run feature "Add inventory system with drag-and-drop"

# Create asset specs
gads pipeline run asset "Character sprite sheet for a wizard"
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required for Architect and Art Director agents
ANTHROPIC_API_KEY=sk-ant-...

# Ollama (local LLM)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b

# Stable Diffusion
SD_API_URL=http://localhost:7860

# Blender
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe

# Godot
GODOT_EXECUTABLE=godot
GODOT_PROJECTS_DIR=./projects
```

### Service Setup

**Ollama (Required):**
```bash
# Install from https://ollama.ai
ollama serve
ollama pull qwen2.5-coder:14b
```

**Stable Diffusion (Optional):**
```bash
# Install AUTOMATIC1111 WebUI
# Launch with API enabled:
./webui.sh --api
# Or on Windows:
webui-user.bat --api
```

**Blender (Optional):**
- Install from https://www.blender.org/download/
- Add to PATH or set `BLENDER_PATH` in `.env`

---

## Complete Workflow Example

```bash
# 1. Verify services
gads check

# 2. Create project
gads new-project "Dragon Quest" --3d -d "A fantasy adventure game" --style low-poly

# 3. Design the game (optional - uses Architect agent)
gads iterate "Design a combat system with sword attacks and magic spells" --agent architect

# 4. Export to Godot
gads export

# 5. Generate concept art
gads art to-project "fire breathing dragon" --preset character --name dragon -p ./projects/dragon_quest

# 6. Generate textures
gads art to-project "stone castle wall" --preset texture -t textures --name castle_wall -p ./projects/dragon_quest

# 7. Create 3D placeholders
gads blender create-to-project sphere --name player -p ./projects/dragon_quest
gads blender create-to-project cube --name enemy --scale 1.5 -p ./projects/dragon_quest

# 8. Open in Godot
godot --path "./projects/dragon_quest"
```

---

## Troubleshooting

### "Ollama not running"
```bash
ollama serve
```

### "Stable Diffusion API not available"
Make sure SD WebUI is running with `--api` flag.

### "Blender not found"
Set `BLENDER_PATH` in `.env` to your Blender executable path.

### "No session found"
Create a project first:
```bash
gads new-project "My Game"
```

### "Project not exported yet"
Export the session to create the Godot project:
```bash
gads export
```
