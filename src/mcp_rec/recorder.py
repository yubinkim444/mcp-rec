"""Stdio recorder — spawn an MCP server as a subprocess and log every
JSON-RPC message that flows in both directions to a JSONL file."""

from __future__ import annotations

import json
import select
import subprocess
import sys
import time
from pathlib import Path


def _try_parse(line: bytes) -> dict | None:
    s = line.decode("utf-8", errors="replace").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {"_raw": s, "_unparsed": True}


def record(cmd: list[str], out_path: Path) -> int:
    """Run `cmd` as an MCP stdio server. Forward stdin/stdout transparently
    while logging every line-delimited JSON message to `out_path`.

    Returns the subprocess exit code.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    log = out_path.open("a", encoding="utf-8")

    def emit(direction: str, payload: dict | None) -> None:
        if payload is None:
            return
        log.write(json.dumps({
            "ts": time.time(), "dir": direction, "msg": payload,
        }) + "\n")
        log.flush()

    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr, bufsize=0,
    )
    assert proc.stdin and proc.stdout

    parent_in_fd = sys.stdin.buffer.fileno()
    child_out_fd = proc.stdout.fileno()

    parent_buf = b""
    child_buf = b""

    try:
        while True:
            if proc.poll() is not None and not child_buf and not parent_buf:
                break

            r, _, _ = select.select([parent_in_fd, child_out_fd], [], [], 0.1)

            if parent_in_fd in r:
                chunk = sys.stdin.buffer.read1(65536) if hasattr(sys.stdin.buffer, "read1") else sys.stdin.buffer.read(65536)
                if chunk:
                    parent_buf += chunk
                    try:
                        proc.stdin.write(chunk)
                        proc.stdin.flush()
                    except BrokenPipeError:
                        break
                    while b"\n" in parent_buf:
                        line, parent_buf = parent_buf.split(b"\n", 1)
                        emit("client->server", _try_parse(line))
                else:
                    try:
                        proc.stdin.close()
                    except Exception:
                        pass

            if child_out_fd in r:
                chunk = proc.stdout.read1(65536) if hasattr(proc.stdout, "read1") else proc.stdout.read(65536)
                if not chunk:
                    if proc.poll() is not None:
                        break
                    continue
                child_buf += chunk
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                while b"\n" in child_buf:
                    line, child_buf = child_buf.split(b"\n", 1)
                    emit("server->client", _try_parse(line))
    finally:
        log.close()
        try:
            proc.terminate()
        except Exception:
            pass

    return proc.wait()
