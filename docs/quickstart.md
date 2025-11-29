# GADS Quick Start Guide

Get up and running with GADS in 5 minutes.

## Prerequisites

- Python 3.11+
- Ollama (for local AI agents)
- Optional: Stable Diffusion WebUI (for art generation)
- Optional: Blender (for 3D models)
- Optional: Godot 4.x (to run exported projects)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd gads

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e .

# Copy environment file
cp .env.example .env
```

## Configure Services

### 1. Ollama (Required)

```bash
# Install from https://ollama.ai
# Start the server
ollama serve

# Pull the model
ollama pull qwen2.5-coder:14b
```

### 2. Anthropic API (Optional but Recommended)

Add your API key to `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Stable Diffusion (Optional)

```bash
# Start WebUI with API enabled
./webui.sh --api
```

### 4. Blender (Optional)

Add Blender path to `.env`:
```
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

## Verify Setup

```bash
gads check
```

Expected output:
```
┌─────────────────┬────────────────────────┬──────────────────┬──────────┐
│ Service         │ Status                 │ Details          │ Required │
├─────────────────┼────────────────────────┼──────────────────┼──────────┤
│ Ollama          │ ✓ Running with 1 model │ qwen2.5-coder:14b│ Yes      │
│ Stable Diffusion│ ✓ Running with 1 model │ -                │ No       │
│ Blender MCP     │ ○ Cannot connect       │ -                │ No       │
└─────────────────┴────────────────────────┴──────────────────┴──────────┘
```

## Create Your First Game

### Step 1: Create a Project

```bash
gads new-project "Space Shooter" --2d -d "A classic arcade space shooter"
```

### Step 2: Design the Game (Optional)

```bash
gads iterate "Design the core gameplay loop with waves of enemies" --agent architect
```

### Step 3: Export to Godot

```bash
gads export
```

### Step 4: Generate Art (if SD is running)

```bash
# Generate a spaceship sprite
gads art to-project "pixel art spaceship, top-down view" --preset pixel_art --name player_ship -p ./projects/space_shooter

# Generate enemy sprites
gads art to-project "pixel art alien enemy" --preset pixel_art --name enemy -p ./projects/space_shooter
```

### Step 5: Create 3D Placeholders (if Blender is available)

```bash
gads blender create-to-project sphere --name bullet -s 0.2 -p ./projects/space_shooter
```

### Step 6: Open in Godot

```bash
godot --path "./projects/space_shooter"
```

## Common Workflows

### Create a 3D Game

```bash
gads new-project "Fantasy RPG" --3d --style low-poly
gads export
gads blender create-to-project monkey --name player -p ./projects/fantasy_rpg
godot --path "./projects/fantasy_rpg"
```

### Generate Concept Art

```bash
gads art generate "medieval castle on a cliff" --preset concept_art --name castle
gads art generate "fantasy warrior character" --preset character --name hero
```

### Run a Full Pipeline

```bash
gads pipeline run new-game "A puzzle platformer with time manipulation"
gads export
```

### Add Features Iteratively

```bash
gads iterate "Add a double-jump ability to the player"
gads iterate "Create an enemy that patrols back and forth"
gads iterate "Add a health system with 3 hearts"
gads export  # Re-export to get new scripts
```

## CLI Cheat Sheet

| Command | Description |
|---------|-------------|
| `gads check` | Verify all services |
| `gads new-project NAME` | Create new project |
| `gads export` | Export to Godot |
| `gads status` | Show current session |
| `gads sessions` | List all sessions |
| `gads iterate "..."` | Add features/changes |
| `gads art generate "..."` | Generate images |
| `gads art to-project "..."` | Generate to project |
| `gads blender create TYPE` | Create 3D primitive |
| `gads blender create-to-project TYPE` | Create to project |
| `gads pipeline list` | List pipelines |
| `gads pipeline run NAME "..."` | Run pipeline |

## Next Steps

- Read the [CLI Reference](cli-reference.md) for all commands
- Read the [Tools Reference](tools-reference.md) for detailed tool docs
- Read the [Pipelines Guide](pipelines.md) for multi-agent workflows
- Read the [Configuration Guide](configuration.md) for setup options

## Troubleshooting

**"Ollama not running"**
```bash
ollama serve
```

**"No session found"**
```bash
gads new-project "My Game"
```

**"Project not exported"**
```bash
gads export
```

**"Blender not found"**
Set `BLENDER_PATH` in `.env`

**"SD API not available"**
Start WebUI with `--api` flag
