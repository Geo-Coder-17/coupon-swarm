"""Shared helpers for the coupon-swarm ledger (codes.json)."""
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "codes.json"
SCHEMA = ROOT / "schema.json"
CODES_MD = ROOT / "CODES.md"

STATUSES = ("active", "unverified", "expired", "dead")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STORE_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
REGION_RE = re.compile(r"^([A-Z]{2}|EU|global)$")
STALE_AFTER_DAYS = 90       # an "active" code nobody re-verified for this long becomes "unverified"
DEAD_AFTER_FAILED = 2       # this many failed reports with no newer "worked" report marks a code dead
NOTES_MAX = 1000            # schema limit for the notes field


def today() -> date:
    return datetime.now(timezone.utc).date()


def parse_date(value):
    """Return a date for 'YYYY-MM-DD', None for None/''/'none', or raise ValueError."""
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.lower() in ("none", "null", "n/a", "-"):
        return None
    if not DATE_RE.match(value):
        raise ValueError(f"not a YYYY-MM-DD date: {value!r}")
    return date.fromisoformat(value)


def normalize_store(store: str) -> str:
    s = str(store or "").strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = s.split("/")[0].split("?")[0]
    if s.startswith("www."):
        s = s[4:]
    return s


def normalize_regions(value) -> list:
    if isinstance(value, str):
        parts = re.split(r"[,\s;]+", value)
    else:
        parts = list(value or [])
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        p = "global" if p.lower() == "global" else p.upper()
        if p not in out:
            out.append(p)
    return out or ["global"]


def make_id(store: str, code: str) -> str:
    return f"{store}:{code}"


def new_entry(**fields) -> dict:
    """Build a complete entry with defaults, normalized fields, and the derived id."""
    store = normalize_store(fields.get("store"))
    code = str(fields.get("code") or "").strip()
    found_on = parse_date(fields.get("found_on")) or today()
    expires_on = parse_date(fields.get("expires_on"))
    last_verified = parse_date(fields.get("last_verified"))
    status = str(fields.get("status") or "unverified").strip().lower()
    entry = {
        "id": make_id(store, code),
        "store": store,
        "code": code,
        "discount": str(fields.get("discount") or "").strip(),
        "applies_to": str(fields.get("applies_to") or "sitewide").strip() or "sitewide",
        "min_order": (str(fields["min_order"]).strip() or None) if fields.get("min_order") not in (None, "") else None,
        "region": normalize_regions(fields.get("region")),
        "found_on": found_on.isoformat(),
        "expires_on": expires_on.isoformat() if expires_on else None,
        "last_verified": last_verified.isoformat() if last_verified else None,
        "source_url": str(fields.get("source_url") or "").strip(),
        "submitted_by": str(fields.get("submitted_by") or "unknown").strip() or "unknown",
        "notes": str(fields.get("notes") or "").strip()[:NOTES_MAX],
        "status": status,
        "works_reports": int(fields.get("works_reports") or 0),
        "failed_reports": int(fields.get("failed_reports") or 0),
        "last_report": fields.get("last_report") or None,
    }
    if entry["min_order"] and entry["min_order"].lower() in ("none", "null", "n/a", "-"):
        entry["min_order"] = None
    return entry


def validate_entry(entry: dict, ref: date = None) -> list:
    """Return a list of human-readable problems (empty list = valid)."""
    ref = ref or today()
    problems = []
    store, code = entry.get("store", ""), entry.get("code", "")
    if not STORE_RE.match(store):
        problems.append(f"store must be a bare lowercase domain like 'shop.com', got {store!r}")
    if not code or re.search(r"\s", code) or len(code) > 64:
        problems.append(f"code must be a single token without spaces, got {code!r}")
    if entry.get("id") != make_id(store, code):
        problems.append(f"id must be '{make_id(store, code)}'")
    if not entry.get("discount"):
        problems.append("discount is required (e.g. '10% off')")
    if not re.match(r"^https?://", entry.get("source_url") or ""):
        problems.append("source_url must start with http:// or https://")
    for r in entry.get("region") or []:
        if not REGION_RE.match(r):
            problems.append(f"region entries must be 2-letter country codes, 'EU' or 'global', got {r!r}")
    if entry.get("status") not in STATUSES:
        problems.append(f"status must be one of {STATUSES}")
    try:
        found = parse_date(entry.get("found_on"))
        expires = parse_date(entry.get("expires_on"))
        verified = parse_date(entry.get("last_verified"))
        reported = parse_date(entry.get("last_report"))
    except ValueError as e:
        return problems + [str(e)]
    if found is None:
        problems.append("found_on is required")
    elif found > ref:
        problems.append(f"found_on {found} is in the future")
    if expires and found and expires < found:
        problems.append(f"expires_on {expires} is before found_on {found}")
    if verified and found and verified < found:
        problems.append(f"last_verified {verified} is before found_on {found}")
    if verified and verified > ref:
        problems.append(f"last_verified {verified} is in the future")
    if reported and reported > ref:
        problems.append(f"last_report {reported} is in the future")
    if entry.get("status") == "active" and verified is None:
        problems.append("status 'active' needs a last_verified date; use 'unverified' otherwise")
    if expires and expires < ref and entry.get("status") in ("active", "unverified"):
        problems.append(f"expires_on {expires} has passed; status must be 'expired'")
    return problems


def load_ledger() -> dict:
    with open(LEDGER, encoding="utf-8") as f:
        return json.load(f)


def save_ledger(ledger: dict) -> None:
    ledger["updated"] = today().isoformat()
    ledger["codes"].sort(key=lambda e: (STATUSES.index(e["status"]), e["store"], e["code"].lower()))
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
        f.write("\n")


def apply_housekeeping(ledger: dict, ref: date = None) -> list:
    """Expire past-due codes, downgrade stale ones, kill repeatedly failed ones. Returns change notes."""
    ref = ref or today()
    changes = []
    for e in ledger["codes"]:
        expires = parse_date(e.get("expires_on"))
        verified = parse_date(e.get("last_verified"))
        if expires and expires < ref and e["status"] in ("active", "unverified"):
            e["status"] = "expired"
            changes.append(f"{e['id']}: expired on {expires}")
        elif e["status"] == "active" and verified and (ref - verified).days > STALE_AFTER_DAYS:
            e["status"] = "unverified"
            changes.append(f"{e['id']}: not verified since {verified}, now unverified")
        elif e["status"] in ("active", "unverified") and e.get("failed_reports", 0) >= DEAD_AFTER_FAILED \
                and e.get("failed_reports", 0) > e.get("works_reports", 0):
            e["status"] = "dead"
            changes.append(f"{e['id']}: {e['failed_reports']} failed reports, now dead")
    return changes


def render_codes_md(ledger: dict) -> str:
    """Markdown table of live codes, for humans and for agents that read pages rather than JSON."""
    live = [e for e in ledger["codes"] if e["status"] in ("active", "unverified")]
    counts = {s: sum(1 for e in ledger["codes"] if e["status"] == s) for s in STATUSES}
    lines = [
        "# Live coupon codes",
        "",
        f"Generated from `codes.json` on {ledger['updated']} (UTC). "
        f"{counts['active']} active, {counts['unverified']} unverified, "
        f"{counts['expired']} expired and {counts['dead']} dead codes in the ledger.",
        "",
        "Machine-readable source: `https://raw.githubusercontent.com/OWNER/coupon-swarm/main/codes.json`. "
        "To add or report a code, see [AGENTS.md](AGENTS.md).",
        "",
        "| Store | Code | Discount | Applies to | Min. order | Region | Expires | Last verified | Status | Source |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in live:
        lines.append(
            f"| {e['store']} | `{e['code']}` | {e['discount']} | {e['applies_to']} | {e['min_order'] or '-'} | "
            f"{', '.join(e['region'])} | {e['expires_on'] or '-'} | {e['last_verified'] or '-'} | {e['status']} | "
            f"[source]({e['source_url']}) |"
        )
    if not live:
        lines.append("| (no live codes yet) | | | | | | | | | |")
    lines.append("")
    return "\n".join(lines)
