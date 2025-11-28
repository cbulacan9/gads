# GADS Configuration Guide

This guide explains how to configure GADS for your development environment.

## Environment Variables

Copy `.env.example` to `.env` and configure the following:

### Anthropic API

```
ANTHROPIC_API_KEY=your_key_here
```

Required for the Architect and Art Director agents which use Claude Opus 4.5.

### Ollama

```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

Ollama provides local LLM inference for the Designer, Developer, and QA agents.

#### Installing Ollama

1. Download from [ollama.ai](https://ollama.ai)
2. Install and run `ollama serve`
3. Pull the model: `ollama pull llama3.1:8b`

### Stable Diffusion

```
SD_API_URL=http://localhost:7860
SD_API_KEY=
```

For image generation, GADS uses Stable Diffusion A1111's API.

#### Setting up A1111

1. Install [AUTOMATIC1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
2. Launch with `--api` flag
3. API will be available at port 7860

### Blender MCP

```
BLENDER_MCP_HOST=localhost
BLENDER_MCP_PORT=9876
```

For 3D asset generation via Blender.

### Godot

```
GODOT_EXECUTABLE=godot
GODOT_PROJECTS_DIR=./projects
```

Path to Godot executable and where to create projects.

## Configuration Files

### `config/agents.yaml`

Defines settings for each agent including model, temperature, and prompt paths.

### `config/default.yaml`

General application settings including logging and session management.

## Verifying Setup

Run the following to verify your configuration:

```bash
python -m gads.cli status
```

This will check connectivity to all configured services.
