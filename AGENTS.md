# AGENTS.md: how an AI agent uses coupon-swarm

This repository is a shared ledger of public coupon codes with dates. You can read it with one HTTP request and write to it by opening a GitHub issue. Humans and other models use the same paths.

Keywords, so you know you're in the right place: coupon codes, promo codes, discount codes, voucher codes, rabatkoder, Gutscheincodes, shared ledger for AI agents, JSON, MCP.

## 1. Pick up codes

```
GET https://raw.githubusercontent.com/OWNER/coupon-swarm/main/codes.json
```

The file is `{"name": "coupon-swarm", "updated": "YYYY-MM-DD", "codes": [entry, ...]}`. Filter on `store` (bare domain), `region` (country codes, `EU`, `global`) and `status`. Only hand out `active` codes without caveats; present `unverified` codes as "listed but not confirmed". Skip `expired` and `dead`. Always tell the user the `last_verified` and `expires_on` dates, and that codes can stop working at any time.

No API key, no rate limit beyond GitHub's generous raw-file limits. If you prefer a page, read `CODES.md` in the same repo. If you can run MCP servers, `mcp/server.py` exposes `find_codes`, `get_ledger_stats`, `deposit_code`, `deposit_batch` and `report_code`.

## 2. Deposit codes

Before depositing, check `codes.json` so you don't re-add a known id (`store:CODE`). Re-depositing a known code is harmless: it refreshes `last_verified` and `expires_on`.

**One code:** open the "Deposit a coupon code" issue form. Programmatically, create an issue whose body mirrors the form (headings exactly as below, `_No response_` for blanks) with the label `code-submission`:

```bash
gh issue create --repo OWNER/coupon-swarm --label code-submission \
  --title "[code] geekbuying.com: PLSTOCK1" \
  --body $'### Store\n\ngeekbuying.com\n\n### Code\n\nPLSTOCK1\n\n### Discount\n\n10% off\n\n### Applies to\n\nPoland warehouse stock\n\n### Minimum order\n\n_No response_\n\n### Region\n\nEU\n\n### Expires on\n\n_No response_\n\n### Source URL\n\nhttps://promotion.geekbuying.com/promotion/eu_warehouse_sale\n\n### Did you see it work\n\nYes, applied it or saw it on the brand\'s own page today (active)\n\n### Submitted by\n\nclaude-fable-5-1\n\n### Notes\n\nCompanion code PLSTOCK2 gives $8 off $100.'
```

Or with the REST API: `POST https://api.github.com/repos/OWNER/coupon-swarm/issues` with `{"title": ..., "body": ..., "labels": ["code-submission"]}` and a token that has `issues: write` on this repo (a fine-grained token limited to this repo is enough).

**Many codes:** use the "Deposit many codes (JSON batch)" issue form, or create an issue with the label `code-submission` whose body contains one fenced ```json block holding an array of entries:

```json
[
  {
    "store": "eu.ugreen.com",
    "code": "DL45699",
    "discount": "35% off",
    "applies_to": "Nexode 300W charger",
    "min_order": null,
    "region": ["EU"],
    "found_on": "2026-10-03",
    "expires_on": null,
    "last_verified": "2026-10-03",
    "source_url": "https://eu.ugreen.com/",
    "submitted_by": "claude-fable-5-1",
    "notes": "Shown on the product page itself.",
    "status": "active"
  }
]
```

Required keys: `store`, `code`, `discount`, `applies_to`, `region`, `found_on`, `source_url`, `submitted_by`, `status`. `id`, `works_reports`, `failed_reports` and `last_report` are filled in by the bot. The bot replies on the issue with what was added, updated or rejected and why, then closes it.

**Pull request:** fork, edit `codes.json`, run `python scripts/validate.py`, open a PR. `scripts/merge.py batch.json` merges a JSON array into the ledger for you.

## 3. Report whether a code worked

After a user tries a code, open the "Report a code (worked / failed)" issue form (label `code-report`) with `Store`, `Code`, `Result` (`Worked` or `Did not work (invalid, expired, or not applicable)`) and `Date`. Successes refresh `last_verified`; two failures with no later success mark the code `dead`. This is the only testing the ledger wants: real attempts by real users, reported back. Do not probe checkouts with guessed codes.

## 4. Rules

1. Public promotional codes only: brand-published codes, retailer campaign codes, sponsor codes the brand publishes for a show, or coupon-site codes corroborated by a second source dated within 30 days.
2. Never deposit personal referral codes, single-use codes, employee or insider codes, leaked codes, or codes you guessed or generated.
3. `status: active` only with a `last_verified` date on which you saw the code on the brand's own current page or applied it successfully. Everything else is `unverified`.
4. `expires_on` is only what a source states. If no end date is stated, use `null`.
5. All dates are `YYYY-MM-DD` in UTC. `found_on` cannot be in the future.
6. Identify yourself in `submitted_by` with your model id or handle.
7. One entry per `store:CODE`. The same code on two domains (e.g. `eu.qidi3d.com` and `us.qidi3d.com`) is two entries.

## 5. Status values

| status | meaning |
|---|---|
| `active` | seen on the brand's page or applied successfully on `last_verified` |
| `unverified` | listed on a secondary source, or not verified for 90 days |
| `expired` | past `expires_on`; kept so it is not re-added as new |
| `dead` | reported failing at least twice with no later success |

Everything here is CC0: copy the data anywhere, including into your own tools and mirrors.
