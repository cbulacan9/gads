# GADS - Godot Agentic Development System

A multi-agent AI framework for automated Godot game development.

## Overview

GADS orchestrates multiple AI agents to collaboratively design, develop, and iterate on Godot games. The system combines local LLM inference (Ollama), cloud AI (Anthropic Claude), image generation (Stable Diffusion), and 3D asset creation (Blender MCP) into a cohesive development pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Human Creative Director                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Python Orchestrator                        │
│            (Session Management, Agent Routing)               │
└──────┬──────────┬──────────┬──────────┬──────────┬─────────┘
       │          │          │          │          │
   ┌───▼───┐  ┌───▼───┐  ┌───▼───┐  ┌───▼───┐  ┌───▼───┐
   │Architect│ │Designer│ │  Dev  │ │  Art  │ │  QA   │
   │ Agent  │ │ Agent  │ │ Agent │ │Director│ │ Agent │
   └───┬───┘  └───┬───┘  └───┬───┘  └───┬───┘  └───┬───┘
       │          │          │          │          │
       └──────────┴──────────┴──────────┴──────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐      ┌─────▼─────┐     ┌─────▼─────┐
   │  Godot  │      │  Stable   │     │  Blender  │
   │ Project │      │ Diffusion │     │    MCP    │
   └─────────┘      └───────────┘     └───────────┘
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **Architect** | Claude Opus 4.5 | High-level game design, system architecture, creative direction |
| **Designer** | Ollama (local) | Game mechanics, level design, balancing |
| **Developer** | Ollama (local) | GDScript implementation, scene creation, debugging |
| **Art Director** | Claude Opus 4.5 | Visual style, asset specifications, prompt engineering |
| **QA** | Ollama (local) | Testing, validation, quality assurance |

## Tech Stack

- **Python 3.11+** - Orchestrator runtime
- **Ollama** - Local LLM inference
- **Anthropic API** - Claude Opus 4.5 for complex reasoning
- **Stable Diffusion A1111** - Concept art and texture generation
- **Blender MCP** - 3D asset pipeline
- **Godot 4.x** - Game engine

## Project Structure

```
gads/
├── src/
│   ├── orchestrator/       # Core orchestration logic
│   ├── agents/             # Agent implementations
│   ├── tools/              # MCP tools and integrations
│   └── utils/              # Shared utilities
├── config/                 # Configuration files
├── prompts/                # Agent system prompts
├── templates/              # Godot project templates
├── tests/                  # Test suite
├── docs/                   # Documentation
└── examples/               # Example projects
```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/gads.git
cd gads

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

1. Set up Ollama with required models
2. Configure Anthropic API key
3. Set up Stable Diffusion A1111 API
4. Configure Blender MCP connection

See [Configuration Guide](docs/configuration.md) for details.

## Usage

```bash
# Start the orchestrator
python -m gads.main

# Or use the CLI
gads new-project "My Game Idea"
gads iterate "Add a jump mechanic"
```

## Development Status

- [x] Phase 0: Specification
- [ ] Phase 1: Foundation (Current)
  - [ ] Project scaffolding
  - [ ] Orchestrator skeleton
  - [ ] Agent base classes
  - [ ] Configuration system
- [ ] Phase 2: Core Agents
- [ ] Phase 3: Tool Integration
- [ ] Phase 4: Pipeline Assembly
- [ ] Phase 5: Testing & Refinement

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.
