import base64
import hashlib
import json
import math
from pathlib import Path
import struct

from studio.errors import ServiceError
from studio.protocol import FILE_TYPES, MAX_ARTIFACT_TOTAL


def invalid():
    return ServiceError(
        "artifact_invalid", "O Blender não retornou todos os arquivos válidos. Tente simplificar o modelo."
    )


def validate_artifacts(encoded: dict) -> tuple[dict[str, bytes], dict]:
    if not isinstance(encoded, dict) or set(encoded) != set(FILE_TYPES):
        raise invalid()
    files, total = {}, 0
    try:
        for name, content in encoded.items():
            if not isinstance(content, str) or len(content) > MAX_ARTIFACT_TOTAL * 4 // 3 + 8:
                raise invalid()
            payload = base64.b64decode(content, validate=True)
            total += len(payload)
            if not payload or total > MAX_ARTIFACT_TOTAL:
                raise invalid()
            files[name] = payload
        glb = files["model.glb"]
        if len(glb) < 20 or glb[:4] != b"glTF" or struct.unpack_from("<II", glb, 4) != (2, len(glb)):
            raise invalid()
        stl = files["model.stl"]
        if len(stl) < 134 or len(stl) != 84 + struct.unpack_from("<I", stl, 80)[0] * 50:
            raise invalid()
        if not files["scene.blend"].startswith(b"BLENDER"):
            raise invalid()
        png = files["preview.png"]
        if not png.startswith(b"\x89PNG\r\n\x1a\n") or b"IEND" not in png[-12:]:
            raise invalid()
        report = json.loads(files["report.json"])
        if report["units"] != "mm" or not isinstance(report["blender_version"], str):
            raise invalid()
        dimensions = report["dimensions_mm"]
        if set(dimensions) != {"x", "y", "z"} or not all(
            isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 100000
            for value in dimensions.values()
        ):
            raise invalid()
        for key in ("objects", "vertices", "triangles"):
            if not isinstance(report[key], int) or not 0 < report[key] <= 1000000:
                raise invalid()
        if report["watertight"] is not None and not isinstance(report["watertight"], bool):
            raise invalid()
        if not isinstance(report["warnings"], list) or not all(
            isinstance(warning, str) for warning in report["warnings"]
        ):
            raise invalid()
    except (ValueError, KeyError, TypeError, struct.error):
        raise invalid() from None
    return files, report


def save_artifacts(root: Path, job_id: str, encoded: dict, code: str) -> dict:
    files, report = validate_artifacts(encoded)
    root.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, payload in files.items():
        temporary = root / (name + ".part")
        temporary.write_bytes(payload)
        temporary.replace(root / name)
        manifest.append(
            {
                "name": name,
                "relative_path": f"{job_id}/{name}",
                "media_type": FILE_TYPES[name],
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    (root / "last_code.py").write_text(code, encoding="utf-8")
    result = {"files": manifest, "report": report}
    temporary = root / "manifest.json.part"
    temporary.write_text(json.dumps(result, ensure_ascii=True), encoding="utf-8")
    temporary.replace(root / "manifest.json")
    return result
