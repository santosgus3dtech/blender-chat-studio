"""Provider-free adapter between MCP/CLI and the restricted worker."""

import os
from pathlib import Path
from uuid import uuid4

from studio.artifacts import save_artifacts
from studio.errors import ServiceError
from studio.policy import validate_code
from studio.protocol import worker_request


def socket_path() -> str:
    return os.environ.get("BLENDER_SOCKET_PATH", "/run/blender/worker.sock")


async def health() -> dict:
    return await worker_request(socket_path(), {"op": "health"}, 3)


async def execute(code: str, preview_size: int = 512) -> dict:
    validate_code(code)
    if preview_size not in (256, 512, 768):
        raise ValueError("Preview size must be 256, 512 or 768.")
    response = await worker_request(
        socket_path(), {"op": "execute", "code": code, "preview_size": preview_size}, 100
    )
    if response.get("ok") is not True:
        raise ServiceError("worker_failed", "The isolated worker did not produce a complete result.")
    run_id = str(uuid4())
    root = Path(os.environ.get("BLENDER_OUTPUT_DIR", "artifacts")) / run_id
    saved = save_artifacts(root, run_id, response.get("files"), code)
    return {"ok": True, "run_id": run_id, "report": saved["report"], "files": saved["files"]}
