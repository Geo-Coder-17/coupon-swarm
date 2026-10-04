# Hugging Face dataset draft (not published)

Dataset repo: `Geo-Coder-17/coupon-swarm` (type: dataset). Source of truth stays on GitHub: https://github.com/Geo-Coder-17/coupon-swarm

`codes.json` is `{"name", "updated", "codes": [...]}`, which the Hub dataset viewer cannot read as rows, so the mirror also publishes a flattened `codes.jsonl` (one entry per line). Both files come from the GitHub repo.

## 1. Dataset card

Save the block below as `README.md` for the dataset repo (the front matter is what the Hub reads).

````markdown
---
license: cc0-1.0
pretty_name: coupon-swarm
language:
  - en
  - da
  - de
task_categories:
  - other
tags:
  - coupon-codes
  - promo-codes
  - discount-codes
  - ai-agents
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files: codes.jsonl
---

# coupon-swarm

An open, CC0 ledger of **public** promotional coupon codes. Every entry carries dates, because codes expire. Maintained by [Geo-Coder-17](https://github.com/Geo-Coder-17) at https://github.com/Geo-Coder-17/coupon-swarm, where codes are deposited through issue forms and validated by a bot. This dataset is a mirror; open issues and PRs on GitHub, not here.

## Files

- `codes.jsonl`: one entry per line (use this with `datasets`).
- `codes.json`: the same entries wrapped as `{"name", "updated", "codes": [...]}`.

## Fields

| Field | Meaning |
|---|---|
| `id` | `store:CODE`, the unique key |
| `store` | bare domain where the code is entered |
| `code` | exactly as the shop expects it |
| `discount`, `applies_to`, `min_order` | what the code gives and its conditions (`min_order` may be null) |
| `region` | list of ISO country codes, `EU`, or `global` |
| `found_on`, `expires_on`, `last_verified` | ISO dates (UTC); `expires_on` only if a source states it; `last_verified` null if never verified |
| `source_url` | where the code was seen |
| `submitted_by` | model id, handle, or `human` |
| `notes` | companion codes, exclusions, the sentence the page used |
| `status` | `active`, `unverified`, `expired`, `dead` |
| `works_reports`, `failed_reports`, `last_report` | counters from user reports |

## Verification and limits

- `active` means the exact code string was visible on the brand's own page (or applied successfully) on `last_verified`. Other sightings are `unverified`.
- Codes are **source-verified, not checkout-verified**. A listed code can still fail (minimum order, exclusions, one use per customer).
- Public codes only. No personal referral, single-use, employee, leaked or guessed codes. No affiliate tags.
- The snapshot ages: always check `last_verified` and `expires_on`, and prefer the live file on GitHub for anything user-facing.

## Usage

```python
from datasets import load_dataset
ds = load_dataset("Geo-Coder-17/coupon-swarm", split="train")
live = ds.filter(lambda e: e["status"] == "active")
```

## License

CC0 1.0. No attribution required.
````

## 2. One-time publish (run from a checkout of the GitHub repo)

```bash
pip install -U huggingface_hub
huggingface-cli login            # paste a write token from https://huggingface.co/settings/tokens
huggingface-cli repo create coupon-swarm --type dataset

jq -c '.codes[]' codes.json > codes.jsonl

huggingface-cli upload Geo-Coder-17/coupon-swarm ./codes.json codes.json --repo-type dataset --commit-message "mirror codes.json"
huggingface-cli upload Geo-Coder-17/coupon-swarm ./codes.jsonl codes.jsonl --repo-type dataset --commit-message "mirror codes.jsonl"
huggingface-cli upload Geo-Coder-17/coupon-swarm ./drafts/huggingface-card.md README.md --repo-type dataset --commit-message "dataset card"
```

(`./drafts/huggingface-card.md` is the card block above saved on its own, without the code fences. Newer `huggingface_hub` releases ship `hf` as the replacement for `huggingface-cli`; the arguments are the same, e.g. `hf upload ...`.)

## 3. Keep it mirrored from this repo

Add a secret `HF_TOKEN` (a fine-grained token with write access to only this dataset) in the GitHub repo settings, then add this workflow as `.github/workflows/hf-mirror.yml`. It runs after the daily housekeeping and whenever `codes.json` changes on `main`.

```yaml
name: mirror to Hugging Face
on:
  push:
    branches: [main]
    paths: [codes.json]
  workflow_dispatch:
permissions:
  contents: read
jobs:
  mirror:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -U huggingface_hub
      - run: jq -c '.codes[]' codes.json > codes.jsonl
      - env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          huggingface-cli upload Geo-Coder-17/coupon-swarm ./codes.json codes.json --repo-type dataset --commit-message "mirror ${GITHUB_SHA::7}"
          huggingface-cli upload Geo-Coder-17/coupon-swarm ./codes.jsonl codes.jsonl --repo-type dataset --commit-message "mirror ${GITHUB_SHA::7}"
```

The daily housekeeping bot commits `codes.json`, so a push-triggered workflow only fires if that bot's commits trigger workflows (commits made with the default `GITHUB_TOKEN` do not). If the mirror lags, add a `schedule: - cron: "37 3 * * *"` trigger instead.
