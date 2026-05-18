"""Stdio replayer — speak MCP on stdio by replaying a previously-recorded
JSONL session. Incoming requests are matched against the recording by
(method, params) and the corresponding server response is returned with
the caller's id rewritten in."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def _hash(method: str, params) -> str:
    blob = json.dumps([method, params], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _build_index(session_path: Path) -> tuple[dict[str, list[dict]], list[dict]]:
    """Return (request_response_pairs_by_hash, server_notifications).

    The pairs are queued so repeated identical requests pop their responses
    in original order.
    """
    pairs: dict[str, list[dict]] = {}
    notifications: list[dict] = []
    pending: dict[int | str, tuple[str, dict]] = {}  # request id -> (hash, request msg)

    with session_path.open("r", encoding="utf-8") as f:
        for raw in f:
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg = entry.get("msg") or {}
            if msg.get("_unparsed"):
                continue
            direction = entry.get("dir")
            mid = msg.get("id")
            method = msg.get("method")
            if direction == "client->server" and mid is not None and method:
                pending[mid] = (_hash(method, msg.get("params")), msg)
            elif direction == "server->client":
                if mid is not None and mid in pending:
                    h, _req = pending.pop(mid)
                    pairs.setdefault(h, []).append(msg)
                elif mid is None and method:
                    notifications.append(msg)
    return pairs, notifications


def replay(session_path: Path) -> int:
    if not session_path.exists():
        print(f"mcp-rec: session file not found: {session_path}", file=sys.stderr)
        return 2

    pairs, notifications = _build_index(session_path)
    queues = {h: list(rs) for h, rs in pairs.items()}

    # Replay any server-initiated notifications first (init banners, capability dumps, etc.)
    for n in notifications:
        sys.stdout.write(json.dumps(n) + "\n")
        sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        mid = req.get("id")
        method = req.get("method")
        if mid is None:
            # Client notification — no response expected.
            continue

        h = _hash(method, req.get("params"))
        queue = queues.get(h)
        if queue:
            recorded = queue.pop(0)
            resp = dict(recorded)
            resp["id"] = mid
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        else:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"mcp-rec: no recorded response for method={method}"},
            }) + "\n")
            sys.stdout.flush()
    return 0
