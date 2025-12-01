# GADS Tools Reference

This document describes the external tools integrated with GADS for game development.

## Overview

GADS integrates with external tools to support game project creation:

| Tool | Purpose | Required |
|------|---------|----------|
| **GodotTool** | Project creation and export | Built-in |
| **BlenderMCPTool** | Placeholder 3D asset creation | Optional |

> **Note:** Stable Diffusion and Hyper3D Rodin integrations have been archived.
> See `docs/archive/` if you need AI-powered asset generation.

---

## GodotTool

Creates and manages Godot 4.x projects.

### Features

- **Project Creation** - Complete Godot project structure
- **Scene Generation** - 2D and 3D main scenes with camera, lighting, environment
- **Script Management** - GDScript file creation and organization
- **Player Templates** - Ready-to-use CharacterBody2D/3D scenes
- **Export Validation** - Ensures projects run correctly

### Generated Project Structure

```
project_name/
├── project.godot           # Godot project configuration
├── icon.svg                # Project icon
├── README.md               # Project documentation
├── .gitignore              # Git ignore rules
├── scenes/
│   └── main.tscn           # Main scene (2D or 3D)
├── scripts/
│   └── *.gd                # GDScript files
├── assets/
│   ├── sprites/            # 2D sprite images
│   ├── textures/           # Texture files
│   ├── models/             # 3D models (GLB, FBX)
│   ├── audio/              # Sound effects and music
│   ├── fonts/              # Custom fonts
│   └── ui/                 # UI assets
├── autoloads/
│   └── game_manager.gd     # Global singleton
├── resources/              # Godot resources
└── scenes/                 # Additional scenes
```

### 3D Scene Contents

When creating a 3D project, the main scene includes:

- **Camera3D** - Positioned at (0, 5, 10) looking at origin
- **DirectionalLight3D** - Sun-like lighting with shadows
- **WorldEnvironment** - Procedural sky with atmosphere
- **CSGBox3D** - Ground plane (20x1x20) with collision
- **CanvasLayer** - UI layer with info label

### 2D Scene Contents

When creating a 2D project, the main scene includes:

- **Camera2D** - Centered camera
- **StaticBody2D** - Ground platform with collision
- **CanvasLayer** - UI layer with info label

### Usage via CLI

```bash
# Create and export project
gads new-project "My Game" --3d
gads export

# Export with options
gads export -o ./custom-output --open
```

### Usage via Python

```python
from gads.tools import GodotTool

tool = GodotTool(projects_dir="./projects")

# Create project
project_path = tool.create_project(
    name="My Game",
    project_type="3d",
    description="A 3D adventure game",
    art_style="low-poly"
)

# Create additional scenes
tool.create_scene(project_path, "player", "CharacterBody3D")

# Create scripts
tool.create_script(
    project_path,
    script_name="player",
    extends="CharacterBody3D",
    content="# Player controller code..."
)

# Validate project
result = tool.validate_project(project_path)
print(f"Valid: {result['valid']}")
```

---

## BlenderMCPTool

Creates placeholder 3D geometry using Blender in subprocess mode.

### Requirements

- Blender 3.0+ installed
- Blender executable in PATH, or `BLENDER_PATH` set in `.env`

### Installation

1. Download from https://www.blender.org/download/
2. Install Blender
3. Add to PATH or set environment variable:

```bash
# .env
BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```

### Supported Primitives

| Primitive | Description |
|-----------|-------------|
| `cube` | Box mesh |
| `sphere` | UV sphere |
| `cylinder` | Cylinder mesh |
| `plane` | Flat plane |
| `cone` | Cone mesh |
| `torus` | Donut shape |
| `monkey` | Suzanne (Blender mascot) |

### Export Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| GLB | `.glb` | Godot 4 (recommended) |
| GLTF | `.gltf` | Separate files |
| FBX | `.fbx` | Universal exchange |
| OBJ | `.obj` | Legacy support |

### Usage via CLI

```bash
# Check Blender
gads blender check

# Create and export primitive
gads blender create cube --output model.glb

# Create with scale
gads blender create sphere --output ball.glb --scale 2.0

# Create directly to project
gads blender to-project monkey --name enemy -p ./my_project

# Export .blend file
gads blender export output.glb --file model.blend
```

### Usage via Python

```python
import asyncio
from gads.tools.blender_mcp import BlenderMCPTool

async def create_models():
    tool = BlenderMCPTool(blender_path="blender")
    
    try:
        # Check Blender
        status = await tool.health_check()
        print(f"Blender: {status['blender_version']}")
        
        # Create and export primitive
        path = await tool.create_and_export_primitive(
            primitive_type="sphere",
            output_path="./models/sphere.glb",
            name="Player",
            scale=(1.0, 1.0, 1.0)
        )
        print(f"Created: {path}")
        
        # Export to Godot project
        path = await tool.export_to_godot_project(
            project_path="./projects/my_game",
            filename="enemy",
            blend_file="./enemy.blend"
        )
        print(f"Exported: {path}")
        
    finally:
        await tool.close()

asyncio.run(create_models())
```

### Exporting Existing .blend Files

```python
# Export to GLB (Godot-compatible)
await tool.export_gltf(
    output_path="./models/character.glb",
    blend_file="./character.blend",
    export_format="GLB"
)

# Export to FBX
await tool.export_fbx(
    output_path="./models/character.fbx",
    blend_file="./character.blend"
)
```

---

## Integration with Agents

### Developer Agents

Developer agents generate GDScript that references assets:

```bash
# Generate player controller
gads iterate "Create a player that can pick up items" --agent developer_3d

# Export with scripts
gads export
```

---

## Troubleshooting

### Blender

**"Blender not found":**
```bash
# Set path in .env
BLENDER_PATH=/path/to/blender
```

**"Command timed out":**
- Complex scenes may need longer timeout
- Check Blender isn't hanging

**Export errors:**
- Ensure output directory exists
- Check file permissions

### Godot

**"Not a valid Godot project":**
- Check `project.godot` exists in the path
- Run `gads export` first

**Models not appearing:**
- Rescan filesystem in Godot (right-click → Rescan)
- Check model is in `assets/models/`
- GLB files auto-import on project open
