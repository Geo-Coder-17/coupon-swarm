"""Turn a GitHub issue into ledger changes.

Three kinds of issue body are understood:
  1. The "Deposit a coupon code" issue form (label: code-submission).
  2. The "Report a code" issue form (label: code-report) -> bumps works/failed counters.
  3. A fenced ```json block containing one entry object or an array of entries
     (for agents depositing many codes at once; label: code-submission).

Environment: ISSUE_BODY, ISSUE_NUMBER, ISSUE_AUTHOR, ISSUE_LABELS (comma-separated).
Writes 'result' and 'message' to $GITHUB_OUTPUT (or prints them when run locally).
result is one of: added, updated, reported, rejected.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger as L  # noqa: E402

# Issue-form heading -> entry field. Headings must match the labels in .github/ISSUE_TEMPLATE/*.yml.
FIELD_MAP = {
    "store": "store",
    "code": "code",
    "discount": "discount",
    "applies to": "applies_to",
    "minimum order": "min_order",
    "region": "region",
    "expires on": "expires_on",
    "source url": "source_url",
    "did you see it work": "verified_choice",
    "submitted by": "submitted_by",
    "notes": "notes",
    "result": "report_result",
    "date": "report_date",
}


def parse_form(body: str) -> dict:
    """Parse '### Heading\\n\\nvalue' sections of a rendered GitHub issue form."""
    fields = {}
    for m in re.finditer(r"^###\s+(.+?)\s*\n(.*?)(?=^###\s|\Z)", body, re.S | re.M):
        heading = m.group(1).strip().lower()
        value = m.group(2).strip()
        if value == "_No response_":
            value = ""
        key = FIELD_MAP.get(heading)
        if key:
            fields[key] = value
    return fields


def parse_json_block(body: str):
    m = re.search(r"```json\s*(.*?)```", body, re.S | re.I)
    if not m:
        return None
    data = json.loads(m.group(1))
    return data if isinstance(data, list) else [data]


def deposit(entries_in: list, author: str, ledger: dict) -> tuple:
    added, updated, rejected = [], [], []
    by_id = {e["id"]: e for e in ledger["codes"]}
    for raw in entries_in:
        raw = dict(raw)
        raw.setdefault("submitted_by", author)
        # The form offers a yes/no on verification; map it onto status + last_verified.
        choice = str(raw.pop("verified_choice", "") or "").lower()
        if choice.startswith("yes"):
            raw.setdefault("last_verified", L.today().isoformat())
            raw.setdefault("status", "active")
        elif choice.startswith("no"):
            raw.setdefault("status", "unverified")
        entry = L.new_entry(**raw)
        problems = L.validate_entry(entry)
        if problems:
            rejected.append((entry["id"], problems))
            continue
        if entry["id"] in by_id:
            old = by_id[entry["id"]]
            # Re-deposit of a known code: treat as a fresh sighting.
            old["last_verified"] = entry["last_verified"] or old["last_verified"]
            old["expires_on"] = entry["expires_on"] or old["expires_on"]
            if entry["status"] == "active" or not old["source_url"]:   # keep the better (verified) source
                old["source_url"] = entry["source_url"] or old["source_url"]
            if entry["status"] == "active" and old["status"] != "expired":
                old["status"] = "active"
            if entry["notes"] and entry["notes"] not in old["notes"]:
                old["notes"] = (old["notes"] + " | " + entry["notes"]).strip(" |")[:L.NOTES_MAX]
            updated.append(entry["id"])
        else:
            ledger["codes"].append(entry)
            by_id[entry["id"]] = entry
            added.append(entry["id"])
    return added, updated, rejected


def report(fields: dict, ledger: dict) -> tuple:
    store = L.normalize_store(fields.get("store"))
    code = str(fields.get("code") or "").strip()
    target = next((e for e in ledger["codes"] if e["id"] == L.make_id(store, code)), None)
    if target is None:
        return None, f"No entry `{L.make_id(store, code)}` in the ledger. Deposit it first, then report on it."
    result = str(fields.get("report_result") or "").lower()
    when = L.parse_date(fields.get("report_date")) or L.today()
    if "work" in result and "not" not in result and "didn" not in result and "fail" not in result:
        target["works_reports"] += 1
        target["last_verified"] = max(filter(None, [target["last_verified"], when.isoformat()]))
        if target["status"] in ("unverified", "dead"):
            target["status"] = "active"
        verdict = "worked"
    else:
        target["failed_reports"] += 1
        verdict = "failed"
    target["last_report"] = when.isoformat()
    return target["id"], f"Recorded that `{target['id']}` {verdict} on {when}. Now {target['works_reports']} worked / {target['failed_reports']} failed."


def write_output(result: str, message: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"result={result}\n")
            f.write("message<<EOF\n" + message + "\nEOF\n")
    print(f"result={result}\n{message}")


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    author = os.environ.get("ISSUE_AUTHOR", "unknown")
    labels = [l.strip() for l in os.environ.get("ISSUE_LABELS", "").split(",") if l.strip()]
    ledger = L.load_ledger()

    if "code-report" in labels:
        fields = parse_form(body)
        ident, msg = report(fields, ledger)
        if ident is None:
            write_output("rejected", msg)
            return 0
        L.apply_housekeeping(ledger)
        L.save_ledger(ledger)
        L.CODES_MD.write_text(L.render_codes_md(ledger), encoding="utf-8")
        write_output("reported", msg)
        return 0

    entries_in = parse_json_block(body)
    if entries_in is None:
        fields = parse_form(body)
        if not fields.get("code"):
            write_output("rejected", "Could not find a code in this issue. Use the issue form, or include a ```json block with an entry.")
            return 0
        entries_in = [fields]

    added, updated, rejected = deposit(entries_in, author, ledger)
    if added or updated:
        L.apply_housekeeping(ledger)
        L.save_ledger(ledger)
        L.CODES_MD.write_text(L.render_codes_md(ledger), encoding="utf-8")

    lines = []
    if added:
        lines.append("Added: " + ", ".join(f"`{i}`" for i in added))
    if updated:
        lines.append("Updated existing: " + ", ".join(f"`{i}`" for i in updated))
    for ident, problems in rejected:
        lines.append(f"Rejected `{ident}`:\n" + "\n".join(f"  - {p}" for p in problems))
    if added or updated:
        lines.append("\nThanks. The code now shows in CODES.md and codes.json.")
        result = "added" if added else "updated"
    else:
        lines.append("\nNothing was added. Edit this issue to fix the problems above; it will be re-checked automatically.")
        result = "rejected"
    write_output(result, "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
