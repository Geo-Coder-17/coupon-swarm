"""Merge one or more JSON files of entries into codes.json (batch deposit).

Usage: python scripts/merge.py intake/*.json
       python scripts/merge.py --dry-run batch.json

Each input file holds a JSON array of entry objects (or a single object) in the
format described in AGENTS.md. Entries are normalized, validated, deduplicated
against the ledger (a re-deposit of a known code refreshes its dates and source),
then written back sorted. Invalid entries are listed and skipped; the exit code is
1 if any were skipped, so a CI step can refuse a batch with problems.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger as L  # noqa: E402
from intake import deposit  # noqa: E402


def main(argv: list) -> int:
    dry_run = "--dry-run" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__)
        return 2
    ledger = L.load_ledger()
    total_added, total_updated, total_rejected = [], [], []
    for name in files:
        with open(name, encoding="utf-8") as f:
            data = json.load(f)
        entries = data if isinstance(data, list) else [data]
        added, updated, rejected = deposit(entries, "merge.py", ledger)
        total_added += added
        total_updated += updated
        total_rejected += [(name, ident, problems) for ident, problems in rejected]
        print(f"{name}: {len(entries)} entries, {len(added)} added, {len(updated)} updated, {len(rejected)} rejected")
    for name, ident, problems in total_rejected:
        print(f"  rejected {ident} from {name}:")
        for p in problems:
            print(f"    - {p}")
    if dry_run:
        print("dry run: ledger not written")
    else:
        L.apply_housekeeping(ledger)
        L.save_ledger(ledger)
        L.CODES_MD.write_text(L.render_codes_md(ledger), encoding="utf-8")
        print(f"codes.json now holds {len(ledger['codes'])} entries; CODES.md regenerated")
    return 1 if total_rejected else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
