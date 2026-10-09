import asyncio
import base64
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

from studio.artifacts import validate_artifacts
from studio.errors import ServiceError
from studio.policy import validate_code


def encoded_artifacts():
    report = {
        "blender_version": "test-fixture",
        "units": "mm",
        "dimensions_mm": {"x": 20, "y": 20, "z": 20},
        "objects": 1,
        "vertices": 8,
        "triangles": 12,
        "watertight": True,
        "warnings": [],
    }
    files = {
        "model.glb": b"glTF" + struct.pack("<II", 2, 20) + b"\0" * 8,
        "model.stl": b"\0" * 80 + struct.pack("<I", 1) + b"\0" * 50,
        "scene.blend": b"BLENDER-fixture",
        "preview.png": b"\x89PNG\r\n\x1a\n" + b"\0" * 4 + b"IEND" + b"\0" * 4,
        "report.json": json.dumps(report).encode(),
    }
    return {name: base64.b64encode(data).decode() for name, data in files.items()}


@pytest.mark.parametrize("source", sorted((Path(__file__).resolve().parents[1] / "examples").glob("*.py")))
def test_original_examples_pass_policy(source):
    assert len(validate_code(source.read_text(encoding="utf-8"))) == 64


def test_artifact_headers_and_report():
    files, report = validate_artifacts(encoded_artifacts())
    assert len(files) == 5
    assert report["dimensions_mm"] == {"x": 20, "y": 20, "z": 20}


@pytest.mark.parametrize("mutation", ["missing", "unexpected", "bad_glb", "bad_stl", "nonfinite", "units"])
def test_rejects_invalid_artifacts(mutation):
    encoded = encoded_artifacts()
    if mutation == "missing":
        del encoded["preview.png"]
    elif mutation == "unexpected":
        encoded["../secret"] = "eA=="
    elif mutation in ("bad_glb", "bad_stl"):
        encoded["model.glb" if mutation == "bad_glb" else "model.stl"] = "eA=="
    else:
        report = json.loads(base64.b64decode(encoded["report.json"]))
        if mutation == "nonfinite":
            report["dimensions_mm"]["x"] = float("inf")
        else:
            report["units"] = "meters"
        encoded["report.json"] = base64.b64encode(json.dumps(report).encode()).decode()
    with pytest.raises(ServiceError):
        validate_artifacts(encoded)


def test_mcp_tool_schema_without_worker_or_credentials():
    from studio.mcp_bridge import server

    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == {"worker_health", "execute_blender"}
    execute = next(tool for tool in tools if tool.name == "execute_blender")
    assert execute.inputSchema["required"] == ["code"]


def test_mcp_rejects_unsafe_code_without_execution():
    from studio.mcp_bridge import execute_blender

    result = asyncio.run(execute_blender("import os"))
    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_code"


def test_execution_validates_before_socket_access(monkeypatch):
    from studio import execution

    async def unexpected_call(*args):
        pytest.fail("Invalid input must not reach worker")

    monkeypatch.setattr(execution, "worker_request", unexpected_call)
    with pytest.raises(ValueError):
        asyncio.run(execution.execute("import bpy", 999))


def test_successful_execution_writes_relative_manifest(tmp_path, monkeypatch):
    from studio import execution

    async def response(*args):
        return {"ok": True, "files": encoded_artifacts()}

    monkeypatch.setattr(execution, "worker_request", response)
    monkeypatch.setenv("BLENDER_OUTPUT_DIR", str(tmp_path))
    result = asyncio.run(execution.execute("import bpy"))
    manifest = tmp_path / result["run_id"] / "manifest.json"
    assert manifest.is_file()
    assert len(result["files"]) == 5
    assert all("url" not in item and "relative_path" in item for item in result["files"])


@pytest.mark.parametrize("structured", [True, False])
def test_mcp_smoke_handles_both_result_encodings(structured):
    from studio.smoke import tool_output

    result = SimpleNamespace(
        isError=False,
        structuredContent={"ok": True} if structured else None,
        content=[SimpleNamespace(type="text", text='{"ok": true}')],
    )
    assert tool_output(result) == {"ok": True}
