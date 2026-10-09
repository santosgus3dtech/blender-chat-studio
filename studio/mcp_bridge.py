"""Local stdio tools; never an unauthenticated public execution endpoint."""

import asyncio

from mcp.server.fastmcp import FastMCP

from studio.errors import ServiceError
from studio.execution import execute, health
from studio.policy import CodeRejected

server = FastMCP("blender-chat-studio")
lock = asyncio.Lock()


@server.tool()
async def worker_health() -> dict:
    """Inspect the isolated Blender worker without executing code or contacting AI."""
    try:
        return await health()
    except ServiceError as error:
        return {"ok": False, "error": error.as_dict()}


@server.tool()
async def execute_blender(code: str, preview_size: int = 512) -> dict:
    """Execute a complete bpy geometry scene in a fresh restricted Linux worker.

    Coordinates, STL and reports use mm; GLB uses meters. Only bpy, math and
    mathutils imports are allowed. No filesystem, network, subprocess, drivers,
    private attributes, export operators, cameras or lights in generated code.
    The trusted wrapper exports GLB, STL, BLEND, PNG and a geometry report.
    Topology checks do not certify physical printability or solid unions.
    """
    async with lock:
        try:
            return await execute(code, preview_size)
        except (CodeRejected, ValueError):
            return {"ok": False, "error": {"code": "invalid_code", "message": "Modeling policy rejected the input."}}
        except ServiceError as error:
            return {"ok": False, "error": error.as_dict()}


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
