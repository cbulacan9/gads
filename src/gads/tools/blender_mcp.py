"""
Blender MCP Tool for GADS

Interface for 3D asset creation via Blender MCP (Model Context Protocol).

This module provides two ways to interact with Blender:
1. Via Claude's built-in MCP tools (when running inside Claude)
2. Via direct HTTP/WebSocket connection (for CLI usage)

The Blender MCP addon must be installed and running in Blender.
See: https://github.com/ahujasid/blender-mcp
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class BlenderConnectionError(Exception):
    """Raised when unable to connect to Blender MCP."""
    pass


class BlenderCommandError(Exception):
    """Raised when a Blender command fails."""
    pass


class ExportFormat(str, Enum):
    """Supported 3D export formats."""
    GLTF = "gltf"
    GLB = "glb"
    FBX = "fbx"
    OBJ = "obj"
    STL = "stl"


@dataclass
class SceneInfo:
    """Information about the current Blender scene."""
    name: str = "Scene"
    objects: list[dict[str, Any]] = field(default_factory=list)
    object_count: int = 0
    materials_count: int = 0


@dataclass
class ObjectInfo:
    """Information about a Blender object."""
    name: str
    type: str  # MESH, CURVE, EMPTY, LIGHT, CAMERA, etc.
    location: tuple[float, float, float] = (0, 0, 0)
    rotation: tuple[float, float, float] = (0, 0, 0)
    scale: tuple[float, float, float] = (1, 1, 1)
    visible: bool = True


class BlenderMCPTool:
    """
    Tool for interacting with Blender via MCP (Model Context Protocol).
    
    This tool can work in two modes:
    1. Direct mode - Executes Blender Python scripts via subprocess
    2. MCP mode - Uses the MCP protocol (when available)
    
    For GADS CLI, we primarily use direct mode which runs Blender
    in background mode to execute Python scripts.
    
    Prerequisites:
    1. Blender 3.0+ installed and in PATH (or specify path)
    2. For MCP mode: Blender MCP addon installed and running
    """
    
    def __init__(
        self,
        blender_path: str = "blender",
        timeout: int = 120,
    ):
        """
        Initialize the Blender MCP tool.
        
        Args:
            blender_path: Path to Blender executable
            timeout: Command timeout in seconds
        """
        self.blender_path = blender_path
        self.timeout = timeout
    
    async def close(self) -> None:
        """Cleanup (no-op for subprocess mode)."""
        pass
    
    def _run_blender_script(self, script: str, blend_file: str | None = None) -> str:
        """
        Run a Python script in Blender via subprocess.
        
        Args:
            script: Python script to execute
            blend_file: Optional .blend file to open first
            
        Returns:
            Script output (stdout)
        """
        cmd = [self.blender_path, "--background"]
        
        if blend_file:
            cmd.append(blend_file)
        
        cmd.extend(["--python-expr", script])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            if result.returncode != 0:
                raise BlenderCommandError(f"Blender error: {result.stderr[:500]}")
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            raise BlenderCommandError(f"Blender command timed out after {self.timeout}s")
        except FileNotFoundError:
            raise BlenderConnectionError(
                f"Blender not found at '{self.blender_path}'. "
                "Make sure Blender is installed and in PATH."
            )
    
    async def health_check(self) -> dict[str, Any]:
        """
        Check if Blender is available.
        
        Returns:
            Dict with 'available', 'blender_version', 'error' keys
        """
        script = """
import bpy
import sys
print(f"BLENDER_VERSION:{bpy.app.version_string}")
"""
        try:
            output = self._run_blender_script(script)
            
            # Parse version from output
            version = "unknown"
            for line in output.split("\n"):
                if line.startswith("BLENDER_VERSION:"):
                    version = line.split(":", 1)[1].strip()
                    break
            
            return {
                "available": True,
                "blender_version": version,
                "mode": "subprocess",
            }
        except BlenderConnectionError as e:
            return {
                "available": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
            }
    
    # =========================================================================
    # Scene Operations
    # =========================================================================
    
    async def get_scene_info(self) -> SceneInfo:
        """Get information about the current Blender scene."""
        script = """
import bpy
import json

scene = bpy.context.scene
objects = []
for obj in scene.objects:
    objects.append({
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
    })

result = {
    "name": scene.name,
    "object_count": len(scene.objects),
    "objects": objects,
    "materials_count": len(bpy.data.materials),
}
print(f"SCENE_INFO:{json.dumps(result)}")
"""
        output = self._run_blender_script(script)
        
        # Parse JSON from output
        for line in output.split("\n"):
            if line.startswith("SCENE_INFO:"):
                data = json.loads(line.split(":", 1)[1])
                return SceneInfo(
                    name=data.get("name", "Scene"),
                    objects=data.get("objects", []),
                    object_count=data.get("object_count", 0),
                    materials_count=data.get("materials_count", 0),
                )
        
        return SceneInfo()
    
    async def get_object_info(self, object_name: str) -> ObjectInfo:
        """Get information about a specific object."""
        script = f"""
import bpy
import json

obj = bpy.data.objects.get("{object_name}")
if obj:
    result = {{
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "visible": obj.visible_get(),
    }}
    print(f"OBJECT_INFO:{{json.dumps(result)}}")
else:
    print("OBJECT_INFO:null")
"""
        output = self._run_blender_script(script)
        
        for line in output.split("\n"):
            if line.startswith("OBJECT_INFO:"):
                data_str = line.split(":", 1)[1]
                if data_str == "null":
                    raise ValueError(f"Object not found: {object_name}")
                data = json.loads(data_str)
                return ObjectInfo(
                    name=data["name"],
                    type=data["type"],
                    location=tuple(data["location"]),
                    rotation=tuple(data["rotation"]),
                    scale=tuple(data["scale"]),
                    visible=data["visible"],
                )
        
        raise ValueError(f"Object not found: {object_name}")
    
    # =========================================================================
    # Object Creation
    # =========================================================================
    
    async def create_primitive(
        self,
        primitive_type: str,
        name: str | None = None,
        location: tuple[float, float, float] = (0, 0, 0),
        scale: tuple[float, float, float] = (1, 1, 1),
        output_file: str | None = None,
    ) -> str:
        """
        Create a primitive mesh object and optionally save.
        
        Args:
            primitive_type: Type of primitive (cube, sphere, cylinder, plane, cone, torus, monkey)
            name: Optional name for the object
            location: Object location (x, y, z)
            scale: Object scale (x, y, z)
            output_file: If provided, save the .blend file
            
        Returns:
            Name of the created object
        """
        primitives = {
            "cube": "bpy.ops.mesh.primitive_cube_add",
            "sphere": "bpy.ops.mesh.primitive_uv_sphere_add",
            "cylinder": "bpy.ops.mesh.primitive_cylinder_add",
            "plane": "bpy.ops.mesh.primitive_plane_add",
            "cone": "bpy.ops.mesh.primitive_cone_add",
            "torus": "bpy.ops.mesh.primitive_torus_add",
            "monkey": "bpy.ops.mesh.primitive_monkey_add",
        }
        
        if primitive_type.lower() not in primitives:
            raise ValueError(f"Unknown primitive type: {primitive_type}. "
                           f"Available: {list(primitives.keys())}")
        
        op = primitives[primitive_type.lower()]
        obj_name = name or primitive_type.capitalize()
        
        save_line = ""
        if output_file:
            filepath = str(output_file).replace("\\", "/")
            save_line = f'\nbpy.ops.wm.save_as_mainfile(filepath="{filepath}")'
        
        script = f"""
import bpy

# Clear default cube if exists
if "Cube" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)

# Create primitive
{op}(location={location}, scale={scale})
obj = bpy.context.active_object
obj.name = "{obj_name}"
{save_line}
print(f"CREATED:{{obj.name}}")
"""
        output = self._run_blender_script(script)
        
        for line in output.split("\n"):
            if line.startswith("CREATED:"):
                return line.split(":", 1)[1].strip()
        
        return obj_name
    
    # =========================================================================
    # Export Operations
    # =========================================================================
    
    async def export_gltf(
        self,
        output_path: str | Path,
        blend_file: str | None = None,
        export_selected: bool = False,
        export_format: str = "GLB",
    ) -> Path:
        """
        Export scene to GLTF/GLB format.
        
        Args:
            output_path: Output file path
            blend_file: .blend file to export from (uses default scene if None)
            export_selected: If True, export only selected objects
            export_format: 'GLB' (binary) or 'GLTF_SEPARATE'
            
        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if export_format == "GLB" and not str(output_path).endswith(".glb"):
            output_path = output_path.with_suffix(".glb")
        elif export_format == "GLTF_SEPARATE" and not str(output_path).endswith(".gltf"):
            output_path = output_path.with_suffix(".gltf")
        
        filepath = str(output_path).replace("\\", "/")
        
        script = f"""
import bpy
bpy.ops.export_scene.gltf(
    filepath="{filepath}",
    export_format="{export_format}",
    use_selection={export_selected},
)
print(f"EXPORTED:{filepath}")
"""
        self._run_blender_script(script, blend_file)
        return output_path
    
    async def export_fbx(
        self,
        output_path: str | Path,
        blend_file: str | None = None,
        export_selected: bool = False,
    ) -> Path:
        """Export scene to FBX format."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not str(output_path).endswith(".fbx"):
            output_path = output_path.with_suffix(".fbx")
        
        filepath = str(output_path).replace("\\", "/")
        
        script = f"""
import bpy
bpy.ops.export_scene.fbx(
    filepath="{filepath}",
    use_selection={export_selected},
)
print(f"EXPORTED:{filepath}")
"""
        self._run_blender_script(script, blend_file)
        return output_path
    
    async def export_obj(
        self,
        output_path: str | Path,
        blend_file: str | None = None,
        export_selected: bool = False,
    ) -> Path:
        """Export scene to OBJ format."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not str(output_path).endswith(".obj"):
            output_path = output_path.with_suffix(".obj")
        
        filepath = str(output_path).replace("\\", "/")
        
        script = f"""
import bpy
bpy.ops.wm.obj_export(
    filepath="{filepath}",
    export_selected_objects={export_selected},
)
print(f"EXPORTED:{filepath}")
"""
        self._run_blender_script(script, blend_file)
        return output_path
    
    # =========================================================================
    # Godot Integration
    # =========================================================================
    
    async def create_and_export_primitive(
        self,
        primitive_type: str,
        output_path: str | Path,
        name: str | None = None,
        scale: tuple[float, float, float] = (1, 1, 1),
    ) -> Path:
        """
        Create a primitive and export directly to GLB.
        
        Convenience method that creates and exports in one step.
        
        Args:
            primitive_type: Type of primitive
            output_path: Output GLB path
            name: Optional object name
            scale: Object scale
            
        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not str(output_path).endswith(".glb"):
            output_path = output_path.with_suffix(".glb")
        
        filepath = str(output_path).replace("\\", "/")
        
        primitives = {
            "cube": "bpy.ops.mesh.primitive_cube_add",
            "sphere": "bpy.ops.mesh.primitive_uv_sphere_add",
            "cylinder": "bpy.ops.mesh.primitive_cylinder_add",
            "plane": "bpy.ops.mesh.primitive_plane_add",
            "cone": "bpy.ops.mesh.primitive_cone_add",
            "torus": "bpy.ops.mesh.primitive_torus_add",
            "monkey": "bpy.ops.mesh.primitive_monkey_add",
        }
        
        if primitive_type.lower() not in primitives:
            raise ValueError(f"Unknown primitive type: {primitive_type}")
        
        op = primitives[primitive_type.lower()]
        obj_name = name or primitive_type.capitalize()
        
        script = f"""
import bpy

# Delete all mesh objects
for obj in list(bpy.data.objects):
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)

# Create primitive
{op}(location=(0, 0, 0), scale={scale})
obj = bpy.context.active_object
obj.name = "{obj_name}"

# Export to GLB
bpy.ops.export_scene.gltf(
    filepath="{filepath}",
    export_format="GLB",
    use_selection=False,
)
print(f"EXPORTED:{filepath}")
"""
        self._run_blender_script(script)
        return output_path
    
    async def export_to_godot_project(
        self,
        project_path: str | Path,
        filename: str = "model",
        blend_file: str | None = None,
        export_selected: bool = False,
    ) -> Path:
        """
        Export current scene to a Godot project.
        
        Exports as GLB which Godot 4 imports natively.
        
        Args:
            project_path: Path to Godot project
            filename: Name for exported file (without extension)
            blend_file: .blend file to export (uses default scene if None)
            export_selected: If True, export only selected objects
            
        Returns:
            Path to exported file
        """
        project_path = Path(project_path)
        models_dir = project_path / "assets" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = models_dir / f"{filename}.glb"
        
        return await self.export_gltf(
            output_path,
            blend_file=blend_file,
            export_selected=export_selected,
            export_format="GLB",
        )


# Convenience function for synchronous usage
def run_sync(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# Hyper3D Rodin Integration
# =============================================================================

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
        self._mode: str | None = None  # Will be set after checking status
    
    async def check_status(self) -> dict[str, Any]:
        """
        Check if Hyper3D Rodin integration is enabled.
        
        Returns:
            Dict with 'enabled', 'mode', 'error' keys
        """
        if not self.mcp_caller:
            return {
                "enabled": False,
                "error": "MCP caller not configured. Hyper3D requires Blender MCP addon."
            }
        
        try:
            result = await self.mcp_caller("blender:get_hyper3d_status", {})
            
            # Parse response to determine if enabled
            if "disabled" in result.lower():
                return {
                    "enabled": False,
                    "error": result
                }
            
            # Try to detect mode from response
            mode = "MAIN_SITE"  # Default
            if "FAL_AI" in result.upper():
                mode = "FAL_AI"
            
            self._mode = mode
            
            return {
                "enabled": True,
                "mode": mode,
                "message": result
            }
            
        except Exception as e:
            return {
                "enabled": False,
                "error": str(e)
            }
    
    async def generate_from_text(
        self,
        prompt: str,
        bbox_condition: list[float] | None = None,
    ) -> RodinGenerationResult:
        """
        Generate a 3D model from a text description.
        
        Args:
            prompt: Description of the desired model (in English)
            bbox_condition: Optional [Length, Width, Height] ratio for model dimensions
            
        Returns:
            RodinGenerationResult with task info for polling
        """
        if not self.mcp_caller:
            return RodinGenerationResult(
                success=False,
                error="MCP caller not configured"
            )
        
        try:
            params = {"text_prompt": prompt}
            if bbox_condition:
                params["bbox_condition"] = bbox_condition
            
            result = await self.mcp_caller(
                "blender:generate_hyper3d_model_via_text",
                params
            )
            
            # Parse result to get job identifiers
            # Response format varies by mode
            return self._parse_generation_result(result)
            
        except Exception as e:
            return RodinGenerationResult(
                success=False,
                error=str(e)
            )
    
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
            
        Returns:
            RodinGenerationResult with task info for polling
        """
        if not self.mcp_caller:
            return RodinGenerationResult(
                success=False,
                error="MCP caller not configured"
            )
        
        try:
            params = {}
            if image_paths:
                params["input_image_paths"] = image_paths
            if image_urls:
                params["input_image_urls"] = image_urls
            if bbox_condition:
                params["bbox_condition"] = bbox_condition
            
            result = await self.mcp_caller(
                "blender:generate_hyper3d_model_via_images",
                params
            )
            
            return self._parse_generation_result(result)
            
        except Exception as e:
            return RodinGenerationResult(
                success=False,
                error=str(e)
            )
    
    async def poll_job_status(
        self,
        task_uuid: str | None = None,
        subscription_key: str | None = None,
        request_id: str | None = None,
    ) -> RodinJobStatus:
        """
        Check the status of a generation job.
        
        Args:
            task_uuid: Task UUID (MAIN_SITE mode)
            subscription_key: Subscription key (MAIN_SITE mode)
            request_id: Request ID (FAL_AI mode)
            
        Returns:
            RodinJobStatus indicating completion state
        """
        if not self.mcp_caller:
            return RodinJobStatus(
                completed=False,
                status="error",
                error="MCP caller not configured"
            )
        
        try:
            params = {}
            if subscription_key:
                params["subscription_key"] = subscription_key
            if request_id:
                params["request_id"] = request_id
            
            result = await self.mcp_caller(
                "blender:poll_rodin_job_status",
                params
            )
            
            return self._parse_job_status(result)
            
        except Exception as e:
            return RodinJobStatus(
                completed=False,
                status="error",
                error=str(e)
            )
    
    async def import_model(
        self,
        name: str,
        task_uuid: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Import a generated model into Blender.
        
        Args:
            name: Name for the imported object
            task_uuid: Task UUID (MAIN_SITE mode)
            request_id: Request ID (FAL_AI mode)
            
        Returns:
            Dict with import result
        """
        if not self.mcp_caller:
            return {"success": False, "error": "MCP caller not configured"}
        
        try:
            params = {"name": name}
            if task_uuid:
                params["task_uuid"] = task_uuid
            if request_id:
                params["request_id"] = request_id
            
            result = await self.mcp_caller(
                "blender:import_generated_asset",
                params
            )
            
            return {"success": True, "message": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_generation_result(self, result: str) -> RodinGenerationResult:
        """Parse the generation result from MCP response."""
        # The response format varies, try to extract key info
        result_lower = result.lower()
        
        if "error" in result_lower or "failed" in result_lower:
            return RodinGenerationResult(
                success=False,
                error=result
            )
        
        # Try to extract identifiers from response
        task_uuid = None
        subscription_key = None
        request_id = None
        mode = self._mode or "MAIN_SITE"
        
        # Look for common patterns in response
        if "task_uuid" in result_lower:
            # Try to extract UUID
            import re
            uuid_match = re.search(r'task_uuid["\']?\s*[:=]\s*["\']?([a-f0-9-]+)', result, re.I)
            if uuid_match:
                task_uuid = uuid_match.group(1)
        
        if "subscription_key" in result_lower:
            import re
            key_match = re.search(r'subscription_key["\']?\s*[:=]\s*["\']?([^"\',\s]+)', result, re.I)
            if key_match:
                subscription_key = key_match.group(1)
        
        if "request_id" in result_lower:
            import re
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
        
        # Check for completion states
        if "done" in result_lower or "completed" in result_lower:
            return RodinJobStatus(
                completed=True,
                status="COMPLETED"
            )
        
        if "failed" in result_lower or "canceled" in result_lower:
            return RodinJobStatus(
                completed=True,
                status="FAILED",
                error=result
            )
        
        if "in_progress" in result_lower or "in_queue" in result_lower or "processing" in result_lower:
            return RodinJobStatus(
                completed=False,
                status="IN_PROGRESS"
            )
        
        # Default to in progress if we can't determine
        return RodinJobStatus(
            completed=False,
            status="UNKNOWN",
            error=f"Unknown status: {result}"
        )
