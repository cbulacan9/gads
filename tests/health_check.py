"""
GADS Health Check Script

Verifies connectivity to all external services:
- Ollama (LLM inference)
- Stable Diffusion A1111 (optional - image generation)
- Blender MCP (optional - 3D assets)

Run with: python -m tests.health_check
Or: python tests/health_check.py
"""

import asyncio
import sys
from dataclasses import dataclass

import aiohttp


@dataclass
class ServiceStatus:
    """Status of an external service."""
    name: str
    available: bool
    message: str
    details: dict | None = None


async def check_ollama(host: str = "http://localhost:11434") -> ServiceStatus:
    """Check Ollama connectivity and available models."""
    try:
        async with aiohttp.ClientSession() as session:
            # Check API is responding
            async with session.get(f"{host}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return ServiceStatus(
                        name="Ollama",
                        available=False,
                        message=f"API returned status {resp.status}",
                    )
                
                data = await resp.json()
                models = [m["name"] for m in data.get("models", [])]
                
                # Check for required model
                has_llama = any("llama3" in m.lower() for m in models)
                
                if not models:
                    return ServiceStatus(
                        name="Ollama",
                        available=False,
                        message="No models installed. Run: ollama pull llama3.1:8b",
                        details={"models": []},
                    )
                
                if not has_llama:
                    return ServiceStatus(
                        name="Ollama",
                        available=True,
                        message=f"Running, but no llama3 model. Available: {', '.join(models)}",
                        details={"models": models},
                    )
                
                return ServiceStatus(
                    name="Ollama",
                    available=True,
                    message=f"Running with {len(models)} model(s)",
                    details={"models": models},
                )
                
    except asyncio.TimeoutError:
        return ServiceStatus(
            name="Ollama",
            available=False,
            message="Connection timeout. Is Ollama running? Try: ollama serve",
        )
    except aiohttp.ClientConnectorError:
        return ServiceStatus(
            name="Ollama",
            available=False,
            message="Cannot connect. Is Ollama running? Try: ollama serve",
        )
    except Exception as e:
        return ServiceStatus(
            name="Ollama",
            available=False,
            message=f"Error: {e}",
        )


async def check_stable_diffusion(url: str = "http://localhost:7860") -> ServiceStatus:
    """Check Stable Diffusion A1111 connectivity."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{url}/sdapi/v1/sd-models",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return ServiceStatus(
                        name="Stable Diffusion",
                        available=False,
                        message=f"API returned status {resp.status}",
                    )
                
                data = await resp.json()
                models = [m.get("title", "unknown") for m in data]
                
                return ServiceStatus(
                    name="Stable Diffusion",
                    available=True,
                    message=f"Running with {len(models)} model(s)",
                    details={"models": models[:5]},  # First 5 models
                )
                
    except asyncio.TimeoutError:
        return ServiceStatus(
            name="Stable Diffusion",
            available=False,
            message="Connection timeout. Is A1111 running with --api flag?",
        )
    except aiohttp.ClientConnectorError:
        return ServiceStatus(
            name="Stable Diffusion",
            available=False,
            message="Cannot connect (optional service)",
        )
    except Exception as e:
        return ServiceStatus(
            name="Stable Diffusion",
            available=False,
            message=f"Error: {e}",
        )


async def check_blender_mcp(host: str = "localhost", port: int = 9876) -> ServiceStatus:
    """Check Blender MCP connectivity."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{host}:{port}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    return ServiceStatus(
                        name="Blender MCP",
                        available=True,
                        message="Running",
                    )
                else:
                    return ServiceStatus(
                        name="Blender MCP",
                        available=False,
                        message=f"API returned status {resp.status}",
                    )
                    
    except asyncio.TimeoutError:
        return ServiceStatus(
            name="Blender MCP",
            available=False,
            message="Connection timeout (optional service)",
        )
    except aiohttp.ClientConnectorError:
        return ServiceStatus(
            name="Blender MCP",
            available=False,
            message="Cannot connect (optional service)",
        )
    except Exception as e:
        return ServiceStatus(
            name="Blender MCP",
            available=False,
            message=f"Error: {e}",
        )


async def check_all_services() -> list[ServiceStatus]:
    """Check all external services."""
    results = await asyncio.gather(
        check_ollama(),
        check_stable_diffusion(),
        check_blender_mcp(),
    )
    return list(results)


def print_status(statuses: list[ServiceStatus]) -> bool:
    """Print status report and return True if all required services are available."""
    print("\n" + "=" * 60)
    print("GADS Service Health Check")
    print("=" * 60)
    
    all_required_ok = True
    
    for status in statuses:
        # Ollama is required, others are optional
        is_required = status.name == "Ollama"
        
        if status.available:
            icon = "✓"
            color = "\033[92m"  # Green
        elif is_required:
            icon = "✗"
            color = "\033[91m"  # Red
            all_required_ok = False
        else:
            icon = "○"
            color = "\033[93m"  # Yellow
        
        reset = "\033[0m"
        required_tag = " [REQUIRED]" if is_required else " [optional]"
        
        print(f"\n{color}{icon} {status.name}{required_tag}{reset}")
        print(f"  {status.message}")
        
        if status.details:
            for key, value in status.details.items():
                if isinstance(value, list):
                    print(f"  {key}: {', '.join(value[:5])}")
                    if len(value) > 5:
                        print(f"  ... and {len(value) - 5} more")
                else:
                    print(f"  {key}: {value}")
    
    print("\n" + "-" * 60)
    
    if all_required_ok:
        print("\033[92m✓ Ready to run GADS\033[0m")
        print("\nRun end-to-end tests with:")
        print("  pytest tests/test_e2e_ollama.py -v --run-e2e")
    else:
        print("\033[91m✗ Required services not available\033[0m")
        print("\nTo start Ollama:")
        print("  1. Install from https://ollama.ai")
        print("  2. Run: ollama serve")
        print("  3. Pull model: ollama pull llama3.1:8b")
    
    print("=" * 60 + "\n")
    
    return all_required_ok


async def main():
    """Run health check."""
    statuses = await check_all_services()
    success = print_status(statuses)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
