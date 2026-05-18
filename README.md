# mcp-rec

> **VCR for the Model Context Protocol.** Record any MCP server's traffic to a
> JSONL file, then replay it deterministically — for tests, bug reports, or
> running your client offline.

[![PyPI](https://img.shields.io/pypi/v/mcp-rec)](https://pypi.org/project/mcp-rec/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![MCP](https://img.shields.io/badge/MCP-tooling-7c3aed)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green)]()

---

## Why

MCP servers are great until they aren't:

- Your server passes locally but fails for someone else — and you have no way to share the exact session that broke.
- You want CI tests for your MCP server but you can't pin upstream API responses.
- You want to demo your agent offline.
- You want to bisect "when did this tool start returning empty results?" against a recording.

`mcp-rec` solves all four by acting as a transparent proxy: it sits between
your MCP client and any stdio MCP server, forwards every byte, and writes a
JSONL transcript. Later you can replay that transcript as if it were the
real server.

---

## Install

```bash
pip install mcp-rec
# or
uvx mcp-rec --help
```

Zero dependencies. Pure Python ≥3.10.

---

## Record

Point your MCP client at `mcp-rec record` instead of your usual server command:

```jsonc
// claude_desktop_config.json
{
  "mcpServers": {
    "filesystem": {
      "command": "mcp-rec",
      "args": [
        "record",
        "-o", "/tmp/filesystem-session.jsonl",
        "--",
        "npx", "-y", "@modelcontextprotocol/server-filesystem", "/some/path"
      ]
    }
  }
}
```

Use your client normally. Every JSON-RPC message in both directions is appended
to the JSONL file:

```json
{"ts": 1750000001.23, "dir": "client->server", "msg": {"jsonrpc":"2.0","id":1,"method":"tools/list"}}
{"ts": 1750000001.45, "dir": "server->client", "msg": {"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}}
```

---

## Replay

Replace the real server with `mcp-rec replay <jsonl>` in your client config:

```jsonc
{
  "mcpServers": {
    "filesystem": {
      "command": "mcp-rec",
      "args": ["replay", "/tmp/filesystem-session.jsonl"]
    }
  }
}
```

Incoming requests are matched against the recording by `(method, params)`
and the corresponding response is returned with the caller's id rewritten
in. Repeated identical requests pop their responses in original order.

Unknown methods return a JSON-RPC `-32601` error so your client can tell
the recording doesn't cover them.

---

## Use cases

| Workflow | How mcp-rec helps |
|----------|-------------------|
| **Bug report** | Record the failing session, attach the JSONL — anyone can reproduce. |
| **CI tests** | Replay against your client to assert behavior without hitting upstream APIs. |
| **Offline demo** | Record once, demo anywhere without the upstream service. |
| **Regression bisect** | Diff two recordings to find when the server's output changed. |
| **Stress test the client** | Replay to verify the client handles all your tool's response shapes. |

---

## Limitations

- **stdio transport only** for now. SSE/HTTP transports are on the roadmap.
- **Notifications** (server-initiated, no id) are replayed once at startup,
  not interleaved with the request stream.
- The matcher is exact-match on `(method, params)`. If your params include
  timestamps or random IDs you'll get a `-32601` on replay — strip those
  fields in your client tests, or open an issue and we'll add a matcher
  config.

---

## Companion projects

- **[ai-first-scraper-mcp](https://github.com/yubinkim444/ai-first-scraper-mcp)** — sample MCP server you can record against.

---

## License

MIT © yubinkim444
