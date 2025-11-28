"""
Blender MCP Tool for GADS

Interface for 3D asset creation via Blender MCP.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiohttp


class BlenderMCPTool:
    """Tool for interacting with Blender via MCP."""
    
    def __init__(self, host: str = "localhost", port: int = 9876):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
    
    async def create_model(
        self,
        description: str,
        style: str = "low_poly",
        output_format: str = "glb",
    ) -> dict[str, Any]:
        """Request 3D model creation from Blender MCP."""
        payload = {
            "description": description,
            "style": style,
            "output_format": output_format,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/create",
                json=payload,
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Blender MCP error: {response.status}")
                return await response.json()
    
    async def export_model(
        self,
        model_id: str,
        output_path: Path,
        format: str = "glb",
    ) -> Path:
        """Export a model to disk."""
        payload = {
            "model_id": model_id,
            "format": format,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/export",
                json=payload,
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Blender MCP error: {response.status}")
                
                data = await response.read()
                output_path.write_bytes(data)
                return output_path
    
    async def health_check(self) -> bool:
        """Check if Blender MCP is available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except Exception:
            return False
