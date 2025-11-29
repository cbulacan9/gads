# GADS Tools Reference

This document describes the external tools integrated with GADS for game asset creation.

## Overview

GADS integrates with three external tools:

| Tool | Purpose | Required |
|------|---------|----------|
| **GodotTool** | Project creation and export | Built-in |
| **StableDiffusionTool** | 2D art generation | Optional |
| **BlenderMCPTool** | 3D model creation | Optional |

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

## StableDiffusionTool

Generates 2D art using Stable Diffusion (AUTOMATIC1111 WebUI API).

### Requirements

- AUTOMATIC1111 Stable Diffusion WebUI
- Running with `--api` flag
- Default URL: `http://localhost:7860`

### Installation

```bash
# Clone A1111 WebUI
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui
cd stable-diffusion-webui

# Launch with API
./webui.sh --api
# Or on Windows:
webui-user.bat --api
```

### Art Presets

Presets optimize generation settings for different game art types:

| Preset | Resolution | Steps | CFG | Use Case |
|--------|------------|-------|-----|----------|
| `pixel_art` | 512x512 | 25 | 8.0 | Retro sprites, tiles |
| `low_poly` | 768x768 | 25 | 7.5 | 3D-style renders |
| `concept_art` | 1024x768 | 30 | 7.0 | Illustrations |
| `ui_icon` | 256x256 | 20 | 8.0 | Interface icons |
| `sprite` | 512x512 | 25 | 7.5 | Character sprites |
| `texture` | 512x512 | 25 | 7.0 | Tileable textures |
| `character` | 768x1024 | 30 | 7.0 | Character sheets |
| `environment` | 1024x576 | 30 | 7.0 | Backgrounds |
| `custom` | 512x512 | 20 | 7.0 | No modifications |

Each preset includes optimized:
- **Prompt prefix/suffix** - Style-specific keywords
- **Negative prompt** - Quality and style exclusions
- **Sampler** - Best sampler for the style
- **Resolution** - Optimal dimensions

### Usage via CLI

```bash
# Check connectivity
gads art check

# List presets
gads art presets

# Generate art
gads art generate "fantasy sword" --preset pixel_art --name sword

# Generate to project
gads art to-project "player sprite" --preset sprite -p ./my_project
```

### Usage via Python

```python
import asyncio
from gads.tools.stable_diffusion import StableDiffusionTool, ArtPreset

async def generate_art():
    tool = StableDiffusionTool(api_url="http://localhost:7860")
    
    try:
        # Check connection
        status = await tool.health_check()
        print(f"Connected: {status['available']}")
        
        # Generate with preset
        result = await tool.generate_with_preset(
            prompt="a magical staff, game item",
            preset=ArtPreset.PIXEL_ART,
            seed=12345
        )
        
        if result.success:
            # Save images
            paths = await tool.save_images(
                result,
                output_dir="./generated",
                name_prefix="staff"
            )
            print(f"Saved: {paths}")
        else:
            print(f"Error: {result.error}")
            
    finally:
        await tool.close()

asyncio.run(generate_art())
```

### Advanced Configuration

```python
from gads.tools.stable_diffusion import GenerationConfig

# Full control over generation
config = GenerationConfig(
    prompt="detailed fantasy castle, digital art",
    negative_prompt="blurry, low quality, watermark",
    width=1024,
    height=768,
    steps=30,
    cfg_scale=7.0,
    sampler="DPM++ 2M Karras",
    seed=42,
    batch_size=4
)

result = await tool.generate(config)
```

### Batch Generation

```python
# Generate multiple prompts
prompts = [
    "red potion bottle",
    "blue mana flask",
    "green health elixir"
]

results = await tool.batch_generate(
    prompts,
    preset=ArtPreset.UI_ICON
)

for result in results:
    if result.success:
        await tool.save_images(result, "./icons", result.prompt[:20])
```

---

## BlenderMCPTool

Creates 3D models using Blender in batch/subprocess mode.

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
gads blender create-to-project monkey --name enemy -p ./my_project

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

### Art Director Agent

The Art Director agent can generate Stable Diffusion prompts that work with the presets:

```bash
# Ask Art Director for prompts
gads iterate "Create concept art prompts for a forest tileset" --agent art_director

# Use the prompts with SD
gads art generate "<prompt from art director>" --preset texture
```

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

### Stable Diffusion

**"Cannot connect" error:**
```bash
# Ensure WebUI is running with --api
./webui.sh --api
```

**"API returned 404":**
- API not enabled. Restart with `--api` flag.

**Slow generation:**
- Check GPU is being used
- Reduce steps or resolution
- Use smaller model

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

---

## Hyper3D Rodin AI (Experimental)

Generate 3D models from text prompts or images using AI.

### Requirements

- Blender MCP addon installed and running
- Hyper3D Rodin enabled in addon settings
- Hyper3D API key (or fal.ai account)

### Setup

1. Open Blender
2. Press `N` to show the sidebar in 3D Viewport
3. Find the **BlenderMCP** panel
4. Check **"Use Hyper3D Rodin 3D model generation"**
5. Enter your Hyper3D API key
6. Connect Claude to the MCP server

### Generation Methods

| Method | Description |
|--------|-------------|
| Text-to-3D | Generate from text description |
| Image-to-3D | Generate from reference images |

### Available Modes

| Mode | Description |
|------|-------------|
| MAIN_SITE | Direct Hyper3D API (requires API key) |
| FAL_AI | Via fal.ai service (alternative) |

### Usage via CLI

```bash
# Check if Rodin is enabled
gads blender rodin check

# Show info about Rodin
gads blender rodin info
```

### Usage via Claude

Once enabled, ask Claude to generate models:

```
"Generate a 3D model of a medieval sword"
"Create a low-poly tree model"
"Make a 3D character from this image" (with uploaded image)
```

### Bbox Condition

Control model proportions with `bbox_condition` [Length, Width, Height]:

```python
[1, 1, 2]  # Tall object (2x height)
[2, 1, 1]  # Long object (2x length)
[1, 1, 1]  # Default proportions
```

### Python API

```python
from gads.tools import Hyper3DRodinTool

# Initialize with MCP caller (when running in Claude)
tool = Hyper3DRodinTool(mcp_caller=my_mcp_caller)

# Check status
status = await tool.check_status()
print(f"Enabled: {status['enabled']}")

# Generate from text
result = await tool.generate_from_text(
    prompt="a treasure chest with gold coins",
    bbox_condition=[1, 1, 0.8]  # Slightly flat
)

# Poll until complete
while True:
    status = await tool.poll_job_status(
        subscription_key=result.subscription_key
    )
    if status.completed:
        break
    await asyncio.sleep(5)

# Import the model
await tool.import_model(
    name="treasure_chest",
    task_uuid=result.task_uuid
)
```

### Generation from Images

```python
# From local images (MAIN_SITE mode)
result = await tool.generate_from_images(
    image_paths=["/path/to/reference.png"]
)

# From URLs (FAL_AI mode)
result = await tool.generate_from_images(
    image_urls=["https://example.com/reference.png"]
)
```

### Troubleshooting

**"Hyper3D Rodin integration is disabled"**
- Enable it in Blender's BlenderMCP panel

**"MCP caller not configured"**
- Hyper3D requires Claude's MCP connection to Blender
- Use Claude to generate models, not the CLI directly

**Generation takes too long**
- AI model generation typically takes 30-120 seconds
- Complex prompts may take longer
