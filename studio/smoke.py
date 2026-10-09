"""Real MCP discovery and Blender generation, with no inference provider."""

import asyncio
import json
import os
from pathlib import Path
import struct
import sys
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def tool_output(result) -> dict:
    assert not result.isError
    if isinstance(result.structuredContent, dict):
        return result.structuredContent
    return json.loads(next(item.text for item in result.content if item.type == "text"))


async def check():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "studio.mcp_bridge"],
        env={key: os.environ[key] for key in ("BLENDER_SOCKET_PATH", "BLENDER_OUTPUT_DIR") if key in os.environ},
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=105)) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {"worker_health", "execute_blender"}
            health = await session.call_tool("worker_health", {})
            assert tool_output(health)["ok"]
            result = await session.call_tool(
                "execute_blender",
                {"code": "import bpy\nbpy.ops.mesh.primitive_cube_add(size=20, location=(0,0,10))", "preview_size": 256},
            )
            proof = tool_output(result)
            assert proof["ok"] and len(proof["files"]) == 5
            assert proof["report"]["dimensions_mm"] == {"x": 20.0, "y": 20.0, "z": 20.0}
            root = Path(os.environ.get("BLENDER_OUTPUT_DIR", "artifacts")) / proof["run_id"]
            glb = (root / "model.glb").read_bytes()
            length = struct.unpack_from("<I", glb, 12)[0]
            gltf = json.loads(glb[20 : 20 + length])
            mesh = gltf["meshes"][0]["primitives"][0]
            position = gltf["accessors"][mesh["attributes"]["POSITION"]]
            node = next(node for node in gltf["nodes"] if "mesh" in node)
            scale = node.get("scale", [1, 1, 1])
            extent = [(position["max"][i] - position["min"][i]) * scale[i] for i in range(3)]
            assert all(abs(value - 0.020) < 0.00001 for value in extent)
            print(json.dumps({"mcp_stdio": "ok", "real_blender": "ok", "glb_units": "meters", "ai": False}))


if __name__ == "__main__":
    asyncio.run(check())
