"""
Stable Diffusion Tool for GADS

Interface for generating images via Stable Diffusion A1111 API.
Supports txt2img generation with presets optimized for game art.
"""

from __future__ import annotations

import base64
import asyncio
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

import aiohttp


class ArtPreset(str, Enum):
    """Pre-configured art style presets for game development."""
    
    PIXEL_ART = "pixel_art"
    LOW_POLY = "low_poly"
    CONCEPT_ART = "concept_art"
    UI_ICON = "ui_icon"
    SPRITE = "sprite"
    TEXTURE = "texture"
    CHARACTER = "character"
    ENVIRONMENT = "environment"
    CUSTOM = "custom"


@dataclass
class GenerationConfig:
    """Configuration for image generation."""
    
    prompt: str
    negative_prompt: str = ""
    width: int = 512
    height: int = 512
    steps: int = 20
    cfg_scale: float = 7.0
    sampler: str = "Euler a"
    seed: int = -1
    batch_size: int = 1
    
    # Optional overrides
    model: str | None = None
    clip_skip: int = 1


@dataclass 
class GenerationResult:
    """Result of an image generation."""
    
    success: bool
    images: list[bytes] = field(default_factory=list)
    seeds: list[int] = field(default_factory=list)
    prompt: str = ""
    error: str | None = None
    info: dict[str, Any] = field(default_factory=dict)


# Preset configurations optimized for different game art styles
PRESET_CONFIGS: dict[ArtPreset, dict[str, Any]] = {
    ArtPreset.PIXEL_ART: {
        "negative_prompt": "blurry, smooth, realistic, 3d render, photograph, anti-aliased",
        "width": 512,
        "height": 512,
        "steps": 25,
        "cfg_scale": 8.0,
        "sampler": "DPM++ 2M Karras",
        "prompt_prefix": "pixel art, 16-bit, retro game style, ",
        "prompt_suffix": ", pixelated, sharp pixels, no anti-aliasing",
    },
    ArtPreset.LOW_POLY: {
        "negative_prompt": "realistic, photograph, high detail, complex geometry",
        "width": 768,
        "height": 768,
        "steps": 25,
        "cfg_scale": 7.5,
        "sampler": "DPM++ 2M Karras",
        "prompt_prefix": "low poly 3d render, stylized, ",
        "prompt_suffix": ", simple geometry, flat shading, game asset",
    },
    ArtPreset.CONCEPT_ART: {
        "negative_prompt": "blurry, low quality, amateur, bad anatomy",
        "width": 1024,
        "height": 768,
        "steps": 30,
        "cfg_scale": 7.0,
        "sampler": "DPM++ 2M Karras",
        "prompt_prefix": "concept art, digital painting, professional, ",
        "prompt_suffix": ", detailed, artstation quality",
    },
    ArtPreset.UI_ICON: {
        "negative_prompt": "blurry, complex background, realistic",
        "width": 256,
        "height": 256,
        "steps": 20,
        "cfg_scale": 8.0,
        "sampler": "Euler a",
        "prompt_prefix": "game ui icon, simple, clear, ",
        "prompt_suffix": ", flat design, transparent background, centered",
    },
    ArtPreset.SPRITE: {
        "negative_prompt": "blurry, realistic, 3d render, complex background",
        "width": 512,
        "height": 512,
        "steps": 25,
        "cfg_scale": 7.5,
        "sampler": "DPM++ 2M Karras",
        "prompt_prefix": "2d game sprite, ",
        "prompt_suffix": ", game character, clean lines, transparent background",
    },
    ArtPreset.TEXTURE: {
        "negative_prompt": "objects, characters, text, watermark",
        "width": 512,
        "height": 512,
        "steps": 25,
        "cfg_scale": 7.0,
        "sampler": "DPM++ 2M Karras",
        "prompt_prefix": "seamless texture, tileable, ",
        "prompt_suffix": ", game texture, PBR ready",
    },
    ArtPreset.CHARACTER: {
        "negative_prompt": "blurry, bad anatomy, extra limbs, deformed",
        "width": 768,
        "height": 1024,
        "steps": 30,
        "cfg_scale": 7.0,
        "sampler": "DPM++ 2M Karras",
        "prompt_prefix": "character design, full body, ",
        "prompt_suffix": ", game character, clear silhouette",
    },
    ArtPreset.ENVIRONMENT: {
        "negative_prompt": "blurry, low quality, text, watermark",
        "width": 1024,
        "height": 576,
        "steps": 30,
        "cfg_scale": 7.0,
        "sampler": "DPM++ 2M Karras",
        "prompt_prefix": "environment concept, scenic, ",
        "prompt_suffix": ", game environment, atmospheric",
    },
    ArtPreset.CUSTOM: {
        "negative_prompt": "",
        "width": 512,
        "height": 512,
        "steps": 20,
        "cfg_scale": 7.0,
        "sampler": "Euler a",
        "prompt_prefix": "",
        "prompt_suffix": "",
    },
}


class StableDiffusionTool:
    """
    Tool for generating images via Stable Diffusion A1111 API.
    
    Features:
    - Art style presets optimized for game development
    - Batch generation support
    - Automatic retry on failure
    - Integration with Godot project structure
    """
    
    def __init__(
        self,
        api_url: str = "http://localhost:7860",
        api_key: str | None = None,
        timeout: int = 120,
    ):
        """
        Initialize the Stable Diffusion tool.
        
        Args:
            api_url: URL of the A1111 WebUI API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=headers,
            )
        return self._session
    
    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def health_check(self) -> dict[str, Any]:
        """
        Check if SD API is available and get basic info.
        
        Returns:
            Dict with 'available' bool and optional 'model', 'error' keys
        """
        try:
            session = await self._get_session()
            async with session.get(f"{self.api_url}/sdapi/v1/options") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "available": True,
                        "model": data.get("sd_model_checkpoint", "unknown"),
                        "api_url": self.api_url,
                    }
                return {
                    "available": False,
                    "error": f"API returned status {response.status}",
                }
        except aiohttp.ClientError as e:
            return {
                "available": False,
                "error": f"Connection failed: {e}",
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
            }
    
    async def get_models(self) -> list[dict[str, Any]]:
        """Get list of available SD models."""
        session = await self._get_session()
        async with session.get(f"{self.api_url}/sdapi/v1/sd-models") as response:
            if response.status != 200:
                raise RuntimeError(f"SD API error: {response.status}")
            return await response.json()
    
    async def get_samplers(self) -> list[str]:
        """Get list of available samplers."""
        session = await self._get_session()
        async with session.get(f"{self.api_url}/sdapi/v1/samplers") as response:
            if response.status != 200:
                raise RuntimeError(f"SD API error: {response.status}")
            data = await response.json()
            return [s["name"] for s in data]
    
    def apply_preset(
        self,
        prompt: str,
        preset: ArtPreset,
        **overrides: Any,
    ) -> GenerationConfig:
        """
        Create a generation config with a preset applied.
        
        Args:
            prompt: Base prompt for generation
            preset: Art style preset to apply
            **overrides: Override any preset values
            
        Returns:
            GenerationConfig with preset applied
        """
        preset_config = PRESET_CONFIGS.get(preset, PRESET_CONFIGS[ArtPreset.CUSTOM])
        
        # Build full prompt with prefix/suffix
        full_prompt = (
            preset_config.get("prompt_prefix", "") +
            prompt +
            preset_config.get("prompt_suffix", "")
        )
        
        config = GenerationConfig(
            prompt=full_prompt,
            negative_prompt=preset_config.get("negative_prompt", ""),
            width=preset_config.get("width", 512),
            height=preset_config.get("height", 512),
            steps=preset_config.get("steps", 20),
            cfg_scale=preset_config.get("cfg_scale", 7.0),
            sampler=preset_config.get("sampler", "Euler a"),
        )
        
        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    async def generate(
        self,
        config: GenerationConfig,
        retry_count: int = 2,
    ) -> GenerationResult:
        """
        Generate images using txt2img.
        
        Args:
            config: Generation configuration
            retry_count: Number of retries on failure
            
        Returns:
            GenerationResult with images and metadata
        """
        payload = {
            "prompt": config.prompt,
            "negative_prompt": config.negative_prompt,
            "width": config.width,
            "height": config.height,
            "steps": config.steps,
            "cfg_scale": config.cfg_scale,
            "sampler_name": config.sampler,
            "seed": config.seed,
            "batch_size": config.batch_size,
        }
        
        if config.clip_skip > 1:
            payload["override_settings"] = {"CLIP_stop_at_last_layers": config.clip_skip}
        
        last_error = None
        for attempt in range(retry_count + 1):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self.api_url}/sdapi/v1/txt2img",
                    json=payload,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        last_error = f"API error {response.status}: {error_text[:200]}"
                        continue
                    
                    data = await response.json()
                    
                    # Decode images
                    images = []
                    for img_b64 in data.get("images", []):
                        images.append(base64.b64decode(img_b64))
                    
                    # Parse info
                    info = {}
                    seeds = []
                    if "info" in data:
                        import json
                        try:
                            info = json.loads(data["info"])
                            seeds = info.get("all_seeds", [])
                        except json.JSONDecodeError:
                            pass
                    
                    return GenerationResult(
                        success=True,
                        images=images,
                        seeds=seeds,
                        prompt=config.prompt,
                        info=info,
                    )
                    
            except aiohttp.ClientError as e:
                last_error = f"Connection error: {e}"
            except Exception as e:
                last_error = f"Error: {e}"
            
            if attempt < retry_count:
                await asyncio.sleep(1)  # Wait before retry
        
        return GenerationResult(
            success=False,
            prompt=config.prompt,
            error=last_error,
        )
    
    async def generate_with_preset(
        self,
        prompt: str,
        preset: ArtPreset = ArtPreset.CONCEPT_ART,
        **overrides: Any,
    ) -> GenerationResult:
        """
        Convenience method to generate with a preset.
        
        Args:
            prompt: Base prompt for generation
            preset: Art style preset to apply
            **overrides: Override any preset values
            
        Returns:
            GenerationResult with images and metadata
        """
        config = self.apply_preset(prompt, preset, **overrides)
        return await self.generate(config)
    
    async def save_images(
        self,
        result: GenerationResult,
        output_dir: Path,
        name_prefix: str = "generated",
        format: str = "png",
    ) -> list[Path]:
        """
        Save generated images to disk.
        
        Args:
            result: GenerationResult containing images
            output_dir: Directory to save images
            name_prefix: Prefix for filenames
            format: Image format (png, jpg, webp)
            
        Returns:
            List of saved file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        for i, image_data in enumerate(result.images):
            seed = result.seeds[i] if i < len(result.seeds) else i
            filename = f"{name_prefix}_{seed}.{format}"
            filepath = output_dir / filename
            filepath.write_bytes(image_data)
            saved_paths.append(filepath)
        
        return saved_paths
    
    async def generate_to_godot_project(
        self,
        prompt: str,
        project_path: Path,
        preset: ArtPreset = ArtPreset.CONCEPT_ART,
        asset_type: str = "sprites",
        name: str = "generated",
        **overrides: Any,
    ) -> list[Path]:
        """
        Generate images and save directly to a Godot project.
        
        Args:
            prompt: Base prompt for generation
            project_path: Path to Godot project
            preset: Art style preset to apply
            asset_type: Type of asset (sprites, textures, concept_art, ui)
            name: Base name for the generated files
            **overrides: Override any preset values
            
        Returns:
            List of saved file paths
        """
        # Determine output directory based on asset type
        asset_dirs = {
            "sprites": "assets/sprites",
            "textures": "assets/textures", 
            "concept_art": "assets/concept_art",
            "ui": "assets/ui",
            "models": "assets/models",  # For texture references
        }
        
        asset_dir = asset_dirs.get(asset_type, "assets")
        output_dir = Path(project_path) / asset_dir
        
        # Generate
        result = await self.generate_with_preset(prompt, preset, **overrides)
        
        if not result.success:
            raise RuntimeError(f"Generation failed: {result.error}")
        
        # Save to project
        return await self.save_images(result, output_dir, name)
    
    async def batch_generate(
        self,
        prompts: list[str],
        preset: ArtPreset = ArtPreset.CONCEPT_ART,
        **overrides: Any,
    ) -> list[GenerationResult]:
        """
        Generate multiple images from a list of prompts.
        
        Args:
            prompts: List of prompts to generate
            preset: Art style preset to apply to all
            **overrides: Override any preset values
            
        Returns:
            List of GenerationResults
        """
        results = []
        for prompt in prompts:
            result = await self.generate_with_preset(prompt, preset, **overrides)
            results.append(result)
        return results


# Synchronous wrapper for CLI usage
def run_sync(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)
