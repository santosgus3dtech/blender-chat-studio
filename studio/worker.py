"""Networkless worker daemon; stdlib only, compatible with Debian Blender 3.4."""

import asyncio
import base64
import json
import os
from pathlib import Path
import resource
import signal
import stat
import tempfile

from studio.policy import CodeRejected, validate_code
from studio.protocol import FILE_TYPES, MAX_ARTIFACT_TOTAL, MAX_REQUEST, MAX_RESPONSE

SOCKET = os.environ.get("BLENDER_SOCKET_PATH", "/run/blender/worker.sock")
BINARY = os.environ.get("BLENDER_BINARY", "/usr/bin/blender")
TIMEOUT = max(10, min(120, int(os.environ.get("BLENDER_EXECUTION_TIMEOUT", "90"))))
WRAPPER = Path(__file__).with_name("blender_wrapper.py")


def process_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT, TIMEOUT + 2))
    # Blender startup uses memfd-backed files larger than a small model export.
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 * 1024, 128 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))


def clean_environment():
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp",
        "TMPDIR": "/tmp",
        "LANG": "C.UTF-8",
        "PYTHONPATH": str(WRAPPER.parent.parent),
        "OMP_NUM_THREADS": "2",
        "OPENBLAS_NUM_THREADS": "2",
        "PYTHONNOUSERSITE": "1",
    }


class Worker:
    def __init__(self):
        self.busy = False
        self.version = None

    async def probe(self):
        try:
            process = await asyncio.create_subprocess_exec(
                BINARY,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=clean_environment(),
            )
            try:
                stdout, _ = await asyncio.wait_for(process.communicate(), 5)
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            if process.returncode == 0 and stdout.startswith(b"Blender "):
                self.version = stdout.splitlines()[0].decode("ascii", "replace")[8:80]
        except (OSError, TimeoutError):
            self.version = None

    async def execute(self, request: dict) -> dict:
        if self.busy:
            return {"ok": False, "error": "worker_busy"}
        try:
            validate_code(request.get("code"))
        except CodeRejected:
            return {"ok": False, "error": "invalid_code"}
        if request.get("preview_size") not in (256, 512, 768):
            return {"ok": False, "error": "invalid_code"}
        self.busy = True
        process = None
        try:
            with tempfile.TemporaryDirectory(prefix="blender-job-", dir="/tmp") as temporary:
                root = Path(temporary)
                (root / "request.json").write_text(
                    json.dumps({"code": request["code"], "preview_size": request["preview_size"]}), encoding="utf-8"
                )
                # Bounded file log avoids PIPE deadlock and unbounded communicate() RAM.
                with (root / "blender.log").open("wb") as log:
                    process = await asyncio.create_subprocess_exec(
                        BINARY,
                        "--background",
                        "--factory-startup",
                        "--disable-autoexec",
                        "--threads",
                        "2",
                        "--python-exit-code",
                        "1",
                        "--python",
                        str(WRAPPER),
                        "--",
                        str(root),
                        stdin=asyncio.subprocess.DEVNULL,
                        stdout=log,
                        stderr=log,
                        cwd=root,
                        env=clean_environment(),
                        start_new_session=True,
                        preexec_fn=process_limits,
                    )
                    try:
                        await asyncio.wait_for(process.wait(), TIMEOUT)
                    except TimeoutError:
                        return {"ok": False, "error": "worker_timeout"}
                    finally:
                        if process.returncode is None:
                            os.killpg(process.pid, signal.SIGKILL)
                            await process.wait()
                if process.returncode != 0 or (root / "failure.json").exists():
                    return {"ok": False, "error": "blender_failed", "exit_code": process.returncode}
                files, total = {}, 0
                for name in FILE_TYPES:
                    path = root / name
                    if not path.is_file() or path.is_symlink():
                        return {"ok": False, "error": "artifact_invalid"}
                    total += path.stat().st_size
                    if total > MAX_ARTIFACT_TOTAL or path.stat().st_size == 0:
                        return {"ok": False, "error": "artifact_invalid"}
                    files[name] = base64.b64encode(path.read_bytes()).decode("ascii")
                return {"ok": True, "files": files, "blender_version": self.version}
        except OSError:
            return {"ok": False, "error": "worker_unavailable"}
        finally:
            if process and process.returncode is None:
                os.killpg(process.pid, signal.SIGKILL)
                await process.wait()
            self.busy = False

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            async with asyncio.timeout(5):
                line = await reader.readline()
            if len(line) > MAX_REQUEST or not line.endswith(b"\n"):
                return
            request = json.loads(line)
            if not isinstance(request, dict):
                return
            if request.get("op") == "health":
                result = {
                    "ok": bool(self.version),
                    "status": "busy" if self.busy else ("ok" if self.version else "unavailable"),
                    "blender_version": self.version,
                }
            elif request.get("op") == "execute":
                # Kill the whole process group when the requesting bridge disconnects.
                execution = asyncio.create_task(self.execute(request))
                disconnected = asyncio.create_task(reader.read(1))
                try:
                    done, _ = await asyncio.wait({execution, disconnected}, return_when=asyncio.FIRST_COMPLETED)
                    if execution not in done:
                        return
                    result = execution.result()
                finally:
                    execution.cancel()
                    disconnected.cancel()
                    await asyncio.gather(execution, disconnected, return_exceptions=True)
            else:
                result = {"ok": False, "error": "invalid_request"}
            encoded = json.dumps(result, ensure_ascii=True, allow_nan=False).encode() + b"\n"
            if len(encoded) <= MAX_RESPONSE:
                writer.write(encoded)
                await writer.drain()
        except (OSError, ValueError, TimeoutError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass


async def main():
    if os.name != "posix":
        raise SystemExit("Worker requires a networkless Linux container.")
    socket_path = Path(SOCKET)
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        if not stat.S_ISSOCK(socket_path.lstat().st_mode):
            raise SystemExit("Worker socket path is not a socket.")
        socket_path.unlink()
    worker = Worker()
    await worker.probe()
    server = await asyncio.start_unix_server(worker.handle, path=SOCKET, limit=MAX_REQUEST + 1)
    os.chmod(SOCKET, 0o660)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
