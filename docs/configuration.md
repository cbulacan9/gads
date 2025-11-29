# GADS Configuration Guide

This guide explains how to configure GADS for your development environment.

## Model Strategy

GADS uses a hybrid approach for optimal quality and cost:

| Agent | Model | Provider | Purpose |
|-------|-------|----------|---------|
| Architect | Claude Opus 4.5 | Anthropic API | High-level game design, creative vision |
| Art Director | Claude Opus 4.5 | Anthropic API | Visual style, SD prompts |
| Designer | Qwen2.5-Coder 14B | Ollama (local) | Game mechanics, balancing |
| Developer 2D | Qwen2.5-Coder 14B | Ollama (local) | GDScript for 2D games |
| Developer 3D | Qwen2.5-Coder 14B | Ollama (local) | GDScript for 3D games |
| QA | Qwen2.5-Coder 14B | Ollama (local) | Code review, testing |
| Router | Qwen2.5-Coder 14B | Ollama (local) | Task classification |

**Why this setup?**
- Claude Opus handles creative/architectural decisions (high quality, ~$1-2 per project)
- Qwen2.5-Coder runs locally for code tasks (free, fast, no latency)
- Single local model = no model switching overhead (~9GB VRAM)

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required for Architect and Art Director
ANTHROPIC_API_KEY=your_key_here

# Ollama (defaults shown)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b

# Optional services
SD_API_URL=http://localhost:7860
BLENDER_MCP_HOST=localhost
BLENDER_MCP_PORT=9876
```

## Ollama Setup

### 1. Install Ollama

Download from [ollama.ai](https://ollama.ai) and install.

### 2. Start the Server

```bash
ollama serve
```

### 3. Pull the Model

```bash
ollama pull qwen2.5-coder:14b
```

**VRAM Requirements:** ~9GB for Qwen2.5-Coder 14B (Q4 quantized)

### Alternative Models

If you have limited VRAM or want different capabilities:

| Model | VRAM | Command |
|-------|------|---------|
| Qwen2.5-Coder 7B | ~5GB | `ollama pull qwen2.5-coder:7b` |
| Qwen2.5-Coder 14B | ~9GB | `ollama pull qwen2.5-coder:14b` |
| DeepSeek Coder V2 16B | ~10GB | `ollama pull deepseek-coder-v2:16b` |

Update `OLLAMA_MODEL` in `.env` and `config/agents.yaml` to use a different model.

## Anthropic API Setup

1. Get an API key from [console.anthropic.com](https://console.anthropic.com)
2. Add to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

**Cost Estimate:** ~$1-2 per game project (Architect + Art Director calls only)

## Stable Diffusion (Optional)

For AI-generated concept art:

1. Install [AUTOMATIC1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
2. Launch with `--api` flag:
   ```bash
   ./webui.sh --api
   ```
3. API available at `http://localhost:7860`

## Blender MCP (Optional)

For 3D asset generation:

1. Install the Blender MCP addon
2. Start Blender with MCP server enabled
3. Default port: 9876

## Configuration Files

### `config/agents.yaml`

Defines model and settings for each agent:

```yaml
architect:
  provider: "anthropic"
  model: "claude-opus-4-5-20251101"
  temperature: 0.7

developer_2d:
  provider: "ollama"
  model: "qwen2.5-coder:14b"
  temperature: 0.3
```

### `config/default.yaml`

General application settings including logging and session management.

## Verifying Setup

```bash
# Check all services
gads check

# Expected output:
# ┌─────────────────┬────────────────────────┬──────────────────┬──────────┐
# │ Service         │ Status                 │ Details          │ Required │
# ├─────────────────┼────────────────────────┼──────────────────┼──────────┤
# │ Ollama          │ ✓ Running with 1 model │ qwen2.5-coder:14b│ Yes      │
# │ Stable Diffusion│ ○ Cannot connect       │ -                │ No       │
# │ Blender MCP     │ ○ Cannot connect       │ -                │ No       │
# └─────────────────┴────────────────────────┴──────────────────┴──────────┘
```

## Running Without Anthropic API

If you don't have an Anthropic API key, you can run GADS with Ollama only:

1. Edit `config/agents.yaml`
2. Change `architect` and `art_director` to use Ollama:
   ```yaml
   architect:
     provider: "ollama"
     model: "qwen2.5-coder:14b"
   ```

Note: Quality for creative/architectural tasks may be lower with local models.
