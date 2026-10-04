# awesome-mcp-servers submission (draft, not submitted)

Target list: https://github.com/punkpeye/awesome-mcp-servers (checked 2026-10-04; `CONTRIBUTING.md` there says agent PRs can opt into fast-tracking with `🤖🤖🤖` at the end of the PR title).
Category: **🛒 E-Commerce** (`### 🛒 <a name="e-commerce"></a>E-Commerce`). Entries use `- [owner/repo](url) <language> <scope> <os> - description`; the legend marks Python as 🐍, cloud service (talks to a remote API) as ☁️, and macOS/Windows/Linux as 🍎 🪟 🐧.

## The line to add

```markdown
- [Geo-Coder-17/coupon-swarm](https://github.com/Geo-Coder-17/coupon-swarm) 🐍 ☁️ 🍎 🪟 🐧 - Shared CC0 ledger of public coupon codes with found, expiry and last-verified dates. Find live codes by store or region, and deposit or report codes through GitHub issues. No affiliate links.
```

The category is not strictly alphabetical in practice (recent entries are appended), but the contribution guide asks for alphabetical order when creating a category, so place it where the neighbours around "G" would sit if you see that order being kept.

## PR

**Title:** `Add coupon-swarm (public coupon-code ledger) 🤖🤖🤖`
(Drop the `🤖🤖🤖` suffix if a human is opening this PR by hand.)

**Description:**

```markdown
Adds [coupon-swarm](https://github.com/Geo-Coder-17/coupon-swarm) under 🛒 E-Commerce.

What it is: a small open ledger (`codes.json`, CC0) of public promotional coupon codes, each with `found_on`, `expires_on` and `last_verified` dates. The MCP server (`mcp/server.py`, Python, stdio) exposes `find_codes`, `get_ledger_stats`, `deposit_code`, `deposit_batch` and `report_code`.

- Reads need no credentials (the ledger is fetched from raw.githubusercontent.com, cached 5 minutes).
- Deposits and reports open GitHub issues that a bot validates and merges; they need a fine-grained token with Issues: write on the ledger repo.
- No affiliate tagging. Codes are verified against the brand's own page, not by checkout attempts, and the entry says which.
- Public GitHub repo, installable and runnable locally: `pip install "mcp<2"` then `python mcp/server.py`.

Checklist
- [x] Public GitHub repository
- [x] Entry follows the existing format and legend
- [x] Placed in the relevant category
```

Before submitting: confirm the repo is public, the README `Geo-Coder-17` placeholders are replaced, and `mcp/README.md` pins `mcp<2` (see the notes at the end of the chat).
