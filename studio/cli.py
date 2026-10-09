import argparse
import asyncio
import json
from pathlib import Path

from studio.errors import ServiceError
from studio.execution import execute, health
from studio.policy import CodeRejected, MAX_CODE_BYTES, validate_code


def main():
    parser = argparse.ArgumentParser(description="Provider-free Blender MCP execution core")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("health", help="Check the isolated worker")
    validate = commands.add_parser("validate", help="Validate syntax policy without running Blender")
    validate.add_argument("source", type=Path)
    run = commands.add_parser("run", help="Export a scene through the restricted worker (Linux container only)")
    run.add_argument("source", type=Path)
    run.add_argument("--preview-size", type=int, choices=(256, 512, 768), default=512)
    arguments = parser.parse_args()
    try:
        if arguments.command == "health":
            result = asyncio.run(health())
            if result.get("ok") is not True:
                raise ServiceError("worker_unavailable", "The worker is not healthy.")
        else:
            with arguments.source.open("rb") as source:
                payload = source.read(MAX_CODE_BYTES + 1)
            if len(payload) > MAX_CODE_BYTES:
                raise ValueError("Source file exceeds the modeling policy limit.")
            code = payload.decode("utf-8")
            digest = validate_code(code)
            result = (
                {"ok": True, "code_sha256": digest, "execution": False}
                if arguments.command == "validate"
                else asyncio.run(execute(code, arguments.preview_size))
            )
        print(json.dumps(result, ensure_ascii=True))
    except (OSError, UnicodeError, CodeRejected, ValueError, ServiceError) as error:
        code = error.code if isinstance(error, ServiceError) else "invalid_input"
        print(json.dumps({"ok": False, "error": code}))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
