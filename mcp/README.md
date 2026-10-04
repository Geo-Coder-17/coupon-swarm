# coupon-swarm MCP server

Gives any MCP-capable assistant (Claude Desktop, Claude Code, Cursor, Windsurf, Zed, …) five tools:

| Tool | Needs a token | What it does |
|---|---|---|
| `find_codes(store, region, status, query)` | no | live codes from the public ledger |
| `get_ledger_stats()` | no | counts per status, number of stores, last update |
| `deposit_code(...)` | yes | opens a "Deposit a coupon code" issue |
| `deposit_batch(entries, submitted_by)` | yes | opens a JSON-batch issue |
| `report_code(store, code, worked)` | yes | opens a "Report a code" issue |

Reads come straight from `raw.githubusercontent.com` (cached 5 minutes). Writes go through GitHub issues, which the repo's intake workflow turns into commits, so the token only needs `issues: write` on this one repo (a fine-grained personal access token scoped to the repo is ideal).

## Setup

```bash
pip install "mcp>=1.2"
```

Claude Desktop / Claude Code (`claude mcp add`), or any client's MCP config:

```json
{
  "mcpServers": {
    "coupon-swarm": {
      "command": "python",
      "args": ["/path/to/coupon-swarm/mcp/server.py"],
      "env": {
        "COUPON_SWARM_REPO": "Geo-Coder-17/coupon-swarm",
        "GITHUB_TOKEN": "github_pat_..."
      }
    }
  }
}
```

Leave out `GITHUB_TOKEN` for a read-only setup.
