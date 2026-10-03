"""Daily housekeeping: expire past-due codes, downgrade stale ones, regenerate CODES.md.

Usage: python scripts/expire.py
Prints what changed. Exit code is always 0; the workflow commits only if files changed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger as L  # noqa: E402


def main() -> int:
    data = L.load_ledger()
    changes = L.apply_housekeeping(data)
    L.save_ledger(data)
    L.CODES_MD.write_text(L.render_codes_md(data), encoding="utf-8")
    for c in changes:
        print(c)
    print(f"{len(changes)} status change(s); CODES.md regenerated for {data['updated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
