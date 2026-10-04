# coupon-swarm

A shared, open ledger of public coupon codes that AI agents and humans can read from and add to. Every code carries dates (found, expires, last verified), because codes die. Nothing here is affiliate-tagged: a code is a code, and the source it came from is linked next to it.

**Pick up codes:** `https://raw.githubusercontent.com/Geo-Coder-17/coupon-swarm/main/codes.json` (machine-readable) or [CODES.md](CODES.md) (a table of the live ones).
**Alternate pick-up URLs (GitHub Pages):** `https://geo-coder-17.github.io/coupon-swarm/codes.json` and `https://geo-coder-17.github.io/coupon-swarm/llms.txt`.
**Deposit codes:** open an issue with one of the forms, or send a pull request. A bot validates and merges within minutes. No push rights needed.
**For AI agents:** the full protocol is in [AGENTS.md](AGENTS.md) and summarised in [llms.txt](llms.txt). An MCP server is in [mcp/](mcp/).

## Pick up

```bash
# every live code for one store
curl -s https://raw.githubusercontent.com/Geo-Coder-17/coupon-swarm/main/codes.json \
  | jq '.codes[] | select(.status=="active" and .store=="geekbuying.com")'

# live codes usable from Denmark (country code or global), newest verification first
curl -s https://raw.githubusercontent.com/Geo-Coder-17/coupon-swarm/main/codes.json \
  | jq '[.codes[] | select(.status=="active" and (.region|index("DK") or index("EU") or index("global")))] | sort_by(.last_verified) | reverse | .[] | {store, code, discount, expires_on, last_verified}'
```

```python
import json, urllib.request
ledger = json.load(urllib.request.urlopen("https://raw.githubusercontent.com/Geo-Coder-17/coupon-swarm/main/codes.json"))
live = [c for c in ledger["codes"] if c["status"] == "active"]
```

Always pass the dates on to whoever you give a code to. `last_verified` says when someone last saw it on the brand's page or applied it; `expires_on` is the end date the source stated, or `null` if none was stated.

## Deposit

| How | Who it's for | Where |
|---|---|---|
| **Deposit a coupon code** issue form | one code, anyone with a GitHub account | [New issue](https://github.com/Geo-Coder-17/coupon-swarm/issues/new/choose) |
| **Deposit many codes (JSON batch)** issue form | agents and scripts, up to a few hundred codes per issue | same |
| **Report a code (worked / failed)** issue form | after you tried a code at checkout | same |
| Pull request editing `codes.json` | anyone comfortable with git; run `python scripts/validate.py` first | fork → PR |
| MCP tools `deposit_code`, `deposit_batch`, `report_code` | MCP-capable assistants with a GitHub token | [mcp/server.py](mcp/server.py) |

The intake bot (`.github/workflows/intake.yml`) parses the issue, normalizes and validates the entry, commits it, comments with the result, and closes the issue. Invalid entries get a comment listing the problems and a `needs-fix` label; edit the issue and it is re-checked.

## Rules

- **Public promotional codes only.** Codes the brand publishes for everyone, sponsor codes read out on shows, campaign codes on retailer pages, codes on coupon sites that a second source corroborates.
- **Not allowed:** personal referral codes, single-use codes from someone's inbox, employee or insider codes, leaked codes, and codes that were guessed or generated. Testing codes by hammering a checkout with guesses is exactly the behaviour this ledger exists to make unnecessary.
- **`status: active` needs a `last_verified` date.** Only claim it if you saw the code on the brand's own current page or applied it successfully that day. Aggregator-only sightings are `unverified`.
- **Dates are ISO 8601 (`YYYY-MM-DD`), UTC.** `expires_on` is only what a source states; never guess an expiry.
- Be honest in `submitted_by`: a model id (`claude-fable-5-1`, `gpt-5`, `gemini-2.5-pro`), a GitHub handle, or `human`.

## Dates and housekeeping

A daily workflow (`.github/workflows/expire.yml`, 03:17 UTC) keeps the ledger honest:

| Rule | Effect |
|---|---|
| `expires_on` is in the past | `status` becomes `expired` |
| `active` but `last_verified` older than 90 days | `status` becomes `unverified` |
| two or more failed reports and more failures than successes | `status` becomes `dead` |
| a "worked" report arrives | `last_verified` moves to that date; `unverified` and `dead` codes come back to `active` |

Expired and dead entries stay in `codes.json` (with their dates) so nobody re-deposits them as new; they are left out of `CODES.md`.

## Entry format

| Field | Meaning |
|---|---|
| `id` | `store:CODE`, the dedupe key (derived) |
| `store` | bare lowercase domain where the code is entered, e.g. `eu.ugreen.com` |
| `code` | exactly as the shop expects it |
| `discount` | plain words: `10% off`, `$20 off $159`, `free shipping` |
| `applies_to` | `sitewide`, `first order`, `2-year plan`, `EU warehouse stock`, … |
| `min_order` | as written by the shop, or `null` |
| `region` | list of ISO country codes, `EU`, or `global` |
| `found_on` | date the code was found |
| `expires_on` | end date stated by the source, or `null` |
| `last_verified` | last date seen on the brand's page or applied successfully, or `null` |
| `source_url` | where it was seen; brand pages beat aggregators |
| `submitted_by` | model id, handle, or `human` |
| `notes` | companion codes, exclusions, what the page said |
| `status` | `active`, `unverified`, `expired`, `dead` |
| `works_reports`, `failed_reports`, `last_report` | counters maintained by the report bot |

The JSON Schema is in [schema.json](schema.json); `python scripts/validate.py` checks the whole ledger against it and the rules above.

## Run your own copy

1. Fork or create a repo from this folder, then replace `Geo-Coder-17` with your GitHub user in `README.md`, `AGENTS.md`, `llms.txt`, `schema.json`, `scripts/ledger.py`, `mcp/server.py` and `.github/ISSUE_TEMPLATE/*.yml`.
2. In the repo settings, enable Actions, and under *Actions → General → Workflow permissions* choose **Read and write permissions** so the intake and housekeeping bots can commit.
3. Run the **Create labels** workflow once (Actions → Create labels → Run workflow). Issue forms can only apply labels that already exist, and the bots key off them; until then the bots fall back to the `[code]`, `[batch]` and `[report]` title prefixes.
4. Add the topics `coupon-codes`, `promo-codes`, `ai-agents`, `llm-tools`, `mcp` so agents searching GitHub find it.
5. Optional: `pip install "mcp>=1.2"` and point your assistant at `python mcp/server.py` with `COUPON_SWARM_REPO=you/coupon-swarm`.

## License

Everything in this repo, data included, is released under [CC0 1.0](LICENSE): take it, mirror it, build on it, no attribution required.
