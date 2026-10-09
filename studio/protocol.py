"""Size-bounded JSON-lines protocol on a private Unix socket."""

import asyncio
import json

from studio.errors import ServiceError

MAX_REQUEST = 32768
MAX_RESPONSE = 48 * 1024 * 1024
MAX_ARTIFACT_TOTAL = 32 * 1024 * 1024
FILE_TYPES = {
    "model.glb": "model/gltf-binary",
    "model.stl": "model/stl",
    "scene.blend": "application/x-blender",
    "preview.png": "image/png",
    "report.json": "application/json",
}


async def worker_request(socket_path: str, payload: dict, timeout: float) -> dict:
    writer = None
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_unix_connection(socket_path, limit=MAX_RESPONSE + 1)
            request = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode() + b"\n"
            if len(request) > MAX_REQUEST:
                raise ServiceError("invalid_code", "O pedido excede o limite do worker.")
            writer.write(request)
            await writer.drain()
            response = await reader.readline()
            if len(response) > MAX_RESPONSE or not response.endswith(b"\n"):
                raise ServiceError("artifact_invalid", "O worker retornou dados inválidos.")
            result = json.loads(response)
            if not isinstance(result, dict):
                raise ValueError()
            return result
    except TimeoutError:
        raise ServiceError(
            "worker_timeout",
            "O worker Blender excedeu o tempo permitido. Simplifique o modelo e tente novamente.",
            True,
        ) from None
    except (OSError, ValueError, asyncio.IncompleteReadError, NotImplementedError):
        raise ServiceError(
            "worker_unavailable",
            "O worker Blender está indisponível. Verifique o container e o socket compartilhado.",
            True,
        ) from None
    finally:
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
