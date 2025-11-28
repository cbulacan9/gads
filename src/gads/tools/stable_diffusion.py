"""
Stable Diffusion Tool for GADS

Interface for generating images via Stable Diffusion A1111 API.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import aiohttp


class StableDiffusionTool:
    """Tool for generating images via Stable Diffusion A1111 API."""
    
    def __init__(self, api_url: str = "http://localhost:7860", api_key: str | None = None):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        sampler: str = "Euler a",
        seed: int = -1,
    ) -> dict[str, Any]:
        """Generate an image using txt2img endpoint."""
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler,
            "seed": seed,
        }
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/sdapi/v1/txt2img",
                json=payload,
                headers=headers,
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"SD API error: {response.status}")
                
                data = await response.json()
                return data
    
    async def save_image(
        self,
        image_data: str,
        output_path: Path,
    ) -> Path:
        """Save a base64-encoded image to disk."""
        image_bytes = base64.b64decode(image_data)
        output_path.write_bytes(image_bytes)
        return output_path
    
    async def get_models(self) -> list[dict[str, Any]]:
        """Get available SD models."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/sdapi/v1/sd-models") as response:
                if response.status != 200:
                    raise RuntimeError(f"SD API error: {response.status}")
                return await response.json()
    
    async def health_check(self) -> bool:
        """Check if SD API is available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/sdapi/v1/options") as response:
                    return response.status == 200
        except Exception:
            return False
