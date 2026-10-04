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

## Region PF (French Polynesia, including Bora Bora)

A code is tagged `PF` only when `data/french-polynesia-shipping.json` says the shop ships there directly (`method: direct`) and the code's terms do not exclude overseas territories ("France métropolitaine uniquement", "hors DOM-TOM", "hors outre-mer"). Shops reachable only through a forwarder keep their `FR` or `EU` tag. Travel codes for the islands (flights to PPT or BOB, hotels and tours in Bora Bora) are region `global` with the destination named in `applies_to`, so `find_codes(query="Bora Bora")` finds them.

## Region NZ (New Zealand)

A code is tagged `NZ` when the store is a New Zealand shop or storefront (`method: domestic` or `nz-storefront` in `data/new-zealand-shipping.json`), or the file says the shop ships to New Zealand directly, and the code's terms do not exclude it ("Australia only", "not valid in New Zealand", "in-store only"). On hosts with country storefronts (dell.com, nike.com, lego.com, asos.com, temu.com) a code is tagged `NZ` only if it was seen on the NZ storefront. A code on an Australian site that also serves NZ gets `["AU","NZ"]` only when the page shows it applies in both. Travel codes for New Zealand (flights, ferries, rentals, activities) are region `global` with New Zealand or the route named in `applies_to`, so `find_codes(query="New Zealand")` finds them.

## Region SJ (Svalbard)

A code is tagged `SJ` only when `data/svalbard-shipping.json` says the shop ships to Svalbard directly or is a local shop, and the code's terms do not exclude it ("gjelder ikke Svalbard", "sendes ikke til Svalbard og Jan Mayen", "kun fastlands-Norge"). Svalbard is outside Norway's VAT and customs area, so the file also records whether the shop deducts MVA for Svalbard addresses (`vat_deducted`). Travel codes for Svalbard (flights to LYR, hotels, tours, expedition cruises) are region `global` with Svalbard or the route named in `applies_to`, so `find_codes(query="Svalbard")` finds them.

## Category sweeps: PC hardware

Codes from `data/pc-hardware-stores.json` shops carry the sector in `applies_to` (one of case, cooler, psu, ssd, hdd, ram, gpu, motherboard, cpu, monitor, keyboard, mouse, headset, mini-pc, prebuilt, laptop, networking, cables-accessories, refurbished, or `sitewide` for a storewide code) and a `notes` field beginning `PC hardware:`, so `find_codes(query="PC hardware")` lists the category and `find_codes(query="ssd")` narrows it. `region` is the shop's delivery area, or the storefront the code was seen on for brand hosts with regional shops.

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

**Region GL:** a code is tagged GL only when `data/greenland-shipping.json` says the shop ships to Greenland and the code's terms don't exclude it.

## Run your own copy

1. Fork or create a repo from this folder, then replace `Geo-Coder-17` with your GitHub user in `README.md`, `AGENTS.md`, `llms.txt`, `schema.json`, `scripts/ledger.py`, `mcp/server.py` and `.github/ISSUE_TEMPLATE/*.yml`.
2. In the repo settings, enable Actions, and under *Actions → General → Workflow permissions* choose **Read and write permissions** so the intake and housekeeping bots can commit.
3. Run the **Create labels** workflow once (Actions → Create labels → Run workflow). Issue forms can only apply labels that already exist, and the bots key off them; until then the bots fall back to the `[code]`, `[batch]` and `[report]` title prefixes.
4. Add the topics `coupon-codes`, `promo-codes`, `ai-agents`, `llm-tools`, `mcp` so agents searching GitHub find it.
5. Optional: `pip install "mcp>=1.2"` and point your assistant at `python mcp/server.py` with `COUPON_SWARM_REPO=you/coupon-swarm`.

## License

Everything in this repo, data included, is released under [CC0 1.0](LICENSE): take it, mirror it, build on it, no attribution required.
