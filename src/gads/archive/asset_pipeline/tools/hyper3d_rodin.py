"""
Hyper3D Rodin Integration (ARCHIVED)

Tool for generating 3D models using Hyper3D Rodin AI.
Requires Blender MCP addon with Hyper3D Rodin integration enabled.

NOTE: This file has been archived from the main GADS codebase.
See archive/asset_pipeline/README.md for details.

This code was originally part of blender_mcp.py but has been separated
because it requires Claude's MCP session to function, making it unsuitable
for the standalone CLI-focused GADS tool.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class RodinGenerationResult:
    """Result of a Hyper3D Rodin generation."""
    success: bool
    task_uuid: str | None = None
    request_id: str | None = None
    subscription_key: str | None = None
    mode: str | None = None  # "MAIN_SITE" or "FAL_AI"
    error: str | None = None


@dataclass 
class RodinJobStatus:
    """Status of a Hyper3D Rodin generation job."""
    completed: bool
    status: str
    statuses: list[str] | None = None
    error: str | None = None


class Hyper3DRodinTool:
    """
    Tool for generating 3D models using Hyper3D Rodin AI.
    
    This tool uses the Blender MCP addon's Hyper3D Rodin integration
    to generate 3D models from text prompts or images.
    
    Prerequisites:
    1. Blender MCP addon installed and running
    2. Hyper3D Rodin integration enabled in addon settings
    3. Valid Hyper3D API key configured
    
    The generation is asynchronous:
    1. Call generate_from_text() or generate_from_images()
    2. Poll poll_job_status() until complete
    3. Call import_model() to bring the model into Blender
    """
    
    def __init__(self, mcp_caller: Callable | None = None):
        """
        Initialize the Hyper3D Rodin tool.
        
        Args:
            mcp_caller: Optional callable to invoke MCP tools.
                       If None, will raise error (MCP required).
        """
        self.mcp_caller = mcp_caller
        self._mode: str | None = None
    
    async def check_status(self) -> dict[str, Any]:
        """Check if Hyper3D Rodin integration is enabled."""
        if not self.mcp_caller:
            return {
                "enabled": False,
                "error": "MCP caller not configured. Hyper3D requires Blender MCP addon."
            }
        
        try:
            result = await self.mcp_caller("blender:get_hyper3d_status", {})
            
            if "disabled" in result.lower():
                return {"enabled": False, "error": result}
            
            mode = "MAIN_SITE"
            if "FAL_AI" in result.upper():
                mode = "FAL_AI"
            
            self._mode = mode
            return {"enabled": True, "mode": mode, "message": result}
            
        except Exception as e:
            return {"enabled": False, "error": str(e)}
    
    async def generate_from_text(
        self,
        prompt: str,
        bbox_condition: list[float] | None = None,
    ) -> RodinGenerationResult:
        """
        Generate a 3D model from a text description.
        
        Args:
            prompt: Description of the desired model (in English)
            bbox_condition: Optional [Length, Width, Height] ratio
        """
        if not self.mcp_caller:
            return RodinGenerationResult(success=False, error="MCP caller not configured")
        
        try:
            params = {"text_prompt": prompt}
            if bbox_condition:
                params["bbox_condition"] = bbox_condition
            
            result = await self.mcp_caller("blender:generate_hyper3d_model_via_text", params)
            return self._parse_generation_result(result)
            
        except Exception as e:
            return RodinGenerationResult(success=False, error=str(e))
    
    async def generate_from_images(
        self,
        image_paths: list[str] | None = None,
        image_urls: list[str] | None = None,
        bbox_condition: list[float] | None = None,
    ) -> RodinGenerationResult:
        """
        Generate a 3D model from reference images.
        
        Args:
            image_paths: Absolute paths to input images (for MAIN_SITE mode)
            image_urls: URLs of input images (for FAL_AI mode)
            bbox_condition: Optional [Length, Width, Height] ratio
        """
        if not self.mcp_caller:
            return RodinGenerationResult(success=False, error="MCP caller not configured")
        
        try:
            params = {}
            if image_paths:
                params["input_image_paths"] = image_paths
            if image_urls:
                params["input_image_urls"] = image_urls
            if bbox_condition:
                params["bbox_condition"] = bbox_condition
            
            result = await self.mcp_caller("blender:generate_hyper3d_model_via_images", params)
            return self._parse_generation_result(result)
            
        except Exception as e:
            return RodinGenerationResult(success=False, error=str(e))
    
    async def poll_job_status(
        self,
        task_uuid: str | None = None,
        subscription_key: str | None = None,
        request_id: str | None = None,
    ) -> RodinJobStatus:
        """Check the status of a generation job."""
        if not self.mcp_caller:
            return RodinJobStatus(completed=False, status="error", error="MCP caller not configured")
        
        try:
            params = {}
            if subscription_key:
                params["subscription_key"] = subscription_key
            if request_id:
                params["request_id"] = request_id
            
            result = await self.mcp_caller("blender:poll_rodin_job_status", params)
            return self._parse_job_status(result)
            
        except Exception as e:
            return RodinJobStatus(completed=False, status="error", error=str(e))
    
    async def import_model(
        self,
        name: str,
        task_uuid: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Import a generated model into Blender."""
        if not self.mcp_caller:
            return {"success": False, "error": "MCP caller not configured"}
        
        try:
            params = {"name": name}
            if task_uuid:
                params["task_uuid"] = task_uuid
            if request_id:
                params["request_id"] = request_id
            
            result = await self.mcp_caller("blender:import_generated_asset", params)
            return {"success": True, "message": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_generation_result(self, result: str) -> RodinGenerationResult:
        """Parse the generation result from MCP response."""
        result_lower = result.lower()
        
        if "error" in result_lower or "failed" in result_lower:
            return RodinGenerationResult(success=False, error=result)
        
        task_uuid = None
        subscription_key = None
        request_id = None
        mode = self._mode or "MAIN_SITE"
        
        import re
        if "task_uuid" in result_lower:
            uuid_match = re.search(r'task_uuid["\']?\s*[:=]\s*["\']?([a-f0-9-]+)', result, re.I)
            if uuid_match:
                task_uuid = uuid_match.group(1)
        
        if "subscription_key" in result_lower:
            key_match = re.search(r'subscription_key["\']?\s*[:=]\s*["\']?([^"\',\s]+)', result, re.I)
            if key_match:
                subscription_key = key_match.group(1)
        
        if "request_id" in result_lower:
            req_match = re.search(r'request_id["\']?\s*[:=]\s*["\']?([^"\',\s]+)', result, re.I)
            if req_match:
                request_id = req_match.group(1)
                mode = "FAL_AI"
        
        return RodinGenerationResult(
            success=True,
            task_uuid=task_uuid,
            subscription_key=subscription_key,
            request_id=request_id,
            mode=mode,
        )
    
    def _parse_job_status(self, result: str) -> RodinJobStatus:
        """Parse the job status from MCP response."""
        result_lower = result.lower()
        
        if "done" in result_lower or "completed" in result_lower:
            return RodinJobStatus(completed=True, status="COMPLETED")
        
        if "failed" in result_lower or "canceled" in result_lower:
            return RodinJobStatus(completed=True, status="FAILED", error=result)
        
        if "in_progress" in result_lower or "in_queue" in result_lower or "processing" in result_lower:
            return RodinJobStatus(completed=False, status="IN_PROGRESS")
        
        return RodinJobStatus(completed=False, status="UNKNOWN", error=f"Unknown status: {result}")
