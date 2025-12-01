"""
Blender MCP Tool for GADS

Interface for 3D asset creation via Blender subprocess.

This module runs Blender in background mode to:
- Create primitive meshes (cube, sphere, cylinder, etc.)
- Export to GLB/FBX/OBJ formats
- Integrate with Godot project structure

Note: AI-powered 3D generation (Hyper3D Rodin) has been archived.
See docs/archive/blender_hyper3d.py if needed.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field
from enum import Enum


class BlenderConnectionError(Exception):
    """Raised when unable to connect to Blender."""
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
    Tool for creating placeholder 3D assets via Blender subprocess.
    
    This tool runs Blender in background mode to execute Python scripts.
    Useful for creating simple placeholder geometry during development.
    
    Prerequisites:
    1. Blender 3.0+ installed
    2. Blender executable in PATH (or specify path)
    """
    
    def __init__(
        self,
        blender_path: str = "blender",
        timeout: int = 120,
    ):
        """
        Initialize the Blender tool.
        
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
