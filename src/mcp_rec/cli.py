"""mcp-rec CLI — record and replay MCP servers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .recorder import record
from .replayer import replay


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcp-rec",
        description="Record and replay MCP servers (VCR for the Model Context Protocol).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="Spawn an MCP stdio server and record every message.")
    rec.add_argument("-o", "--out", default="mcp-session.jsonl",
                     help="Output JSONL path (default: mcp-session.jsonl).")
    rec.add_argument("command", nargs=argparse.REMAINDER,
                     help="The MCP server command to wrap (after `--`).")

    rep = sub.add_parser("replay", help="Replay a recorded JSONL as if it were an MCP server.")
    rep.add_argument("session", help="Path to a previously recorded JSONL.")

    args = parser.parse_args(argv)

    if args.cmd == "record":
        cmd = args.command
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            print("mcp-rec: missing command. Usage: mcp-rec record -- <cmd> [args...]", file=sys.stderr)
            return 2
        return record(cmd, Path(args.out))

    if args.cmd == "replay":
        return replay(Path(args.session))

    return 2


if __name__ == "__main__":
    sys.exit(main())
