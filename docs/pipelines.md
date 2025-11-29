# GADS Pipeline System

Pipelines are multi-agent workflows that chain together multiple agents to accomplish complex tasks. Each pipeline defines a sequence of steps where the output of one agent becomes input for the next.

## Quick Start

```bash
# List available pipelines
gads pipeline list

# Run a pipeline
gads pipeline run new-game "A roguelike deckbuilder with cooking mechanics"

# Run on existing project
gads pipeline run feature "Add inventory system" -s abc123
```

## Built-in Pipelines

### new-game
Creates a complete game concept from a brief description.

**Steps:**
1. **Architect** → Game concept and vision
2. **Architect** → Technical architecture for Godot
3. **Art Director** → Visual style and aesthetic
4. **Designer** → Core gameplay mechanics

**Example:**
```bash
gads new-project "Stellar Chef" --2d --style pixel-art
gads pipeline run new-game "A restaurant management game set on a space station"
```

### feature
Designs, implements, and reviews a new feature.

**Steps:**
1. **Designer** → Feature design document
2. **Developer** → GDScript implementation
3. **QA** → Code review and suggestions

**Example:**
```bash
gads pipeline run feature "Add a combo system for attacks"
```

### asset
Creates specifications and prompts for game assets.

**Steps:**
1. **Art Director** → Asset specifications
2. **Art Director** → Stable Diffusion prompts

**Example:**
```bash
gads pipeline run asset "Forest tileset with mushrooms and fallen logs"
```

### iterate
Reviews and improves existing code.

**Steps:**
1. **QA** → Code review
2. **Developer** → Bug fixes and improvements
3. **QA** → Validation

**Example:**
```bash
gads pipeline run iterate "The player movement feels sluggish"
```

## Project Settings

Project-level settings are established when creating a project and inherited by all pipeline runs:

```bash
# Create a 2D pixel-art project
gads new-project "Dungeon Crawler" --2d --style "pixel-art"

# Create a 3D low-poly project  
gads new-project "Racing Game" --3d --style "low-poly"
```

### Available Settings

| Setting | Flag | Values | Default |
|---------|------|--------|---------|
| Project Type | `--2d` / `--3d` | 2d, 3d | 2d |
| Art Style | `--style` | Any string | (none) |

These settings are stored in the session and automatically passed to all agents, so you don't need to repeat them on every command.

## Custom Pipelines

You can create custom pipelines by adding YAML files to `templates/pipelines/`.

### Pipeline Format

```yaml
# templates/pipelines/my-pipeline.yaml
name: my-pipeline
description: Description shown in 'gads pipeline list'
version: "1.0"

steps:
  - name: step_name
    task_type: game_concept    # TaskType enum value
    output_key: concept        # Key to store output in context
    
  - name: next_step
    task_type: mechanic_design
    input_key: concept         # Read from previous step's output
    output_key: mechanics
    
  - name: final_step
    task_type: review
    input_key: mechanics
    output_key: review
    requires_approval: true    # Optional: pause for user approval
```

### Available Task Types

**Architect Tasks:**
- `game_concept` - New game ideas and vision
- `system_design` - System architecture
- `architecture` - Technical structure
- `creative_direction` - Theme and tone

**Designer Tasks:**
- `mechanic_design` - Gameplay mechanics
- `level_design` - Level layouts
- `balancing` - Difficulty tuning

**Developer Tasks (2D):**
- `implement_feature_2d` - Implement features
- `create_scene_2d` - Create scenes
- `write_script_2d` - Write GDScript
- `debug_2d` - Fix bugs

**Developer Tasks (3D):**
- `implement_feature_3d` - Implement features
- `create_scene_3d` - Create scenes
- `write_script_3d` - Write GDScript
- `debug_3d` - Fix bugs

**Art Director Tasks:**
- `visual_style` - Art direction
- `asset_spec` - Asset specifications
- `prompt_engineering` - SD prompts

**QA Tasks:**
- `test` - Write tests
- `validate` - Check implementation
- `review` - Code review

### Example Custom Pipeline

```yaml
# templates/pipelines/prototype.yaml
name: prototype
description: Quickly prototype a game mechanic with code
version: "1.0"

steps:
  - name: design
    task_type: mechanic_design
    output_key: design
    
  - name: implement
    task_type: implement_feature_2d
    input_key: design
    output_key: code
```

Then run:
```bash
gads pipeline run prototype "A grappling hook that pulls the player"
```

## Pipeline Output

Pipeline results are displayed in the console after all steps complete:

```
============================================================
Pipeline: new-game
============================================================

Step 1/4: concept (architect)
------------------------------------------------------------
[Game concept output here...]

Step 2/4: architecture (architect)  
------------------------------------------------------------
[Architecture output here...]

Step 3/4: visual_style (art_director)
------------------------------------------------------------
[Visual style output here...]

Step 4/4: mechanics (designer)
------------------------------------------------------------
[Mechanics output here...]

============================================================
Pipeline completed successfully (4/4 steps)
============================================================
```

## CLI Reference

```bash
# List all available pipelines
gads pipeline list

# Run a pipeline
gads pipeline run <pipeline-name> "<prompt>" [options]

# Options:
#   -s, --session ID    Use existing session
#   -y, --yes           Skip approval prompts
```
