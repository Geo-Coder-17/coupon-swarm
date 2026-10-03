"""coupon-swarm MCP server: lets any MCP-capable assistant pick up and deposit coupon codes.

Tools
  find_codes(store=None, region=None, status="active", query=None)  -> matching ledger entries
  get_ledger_stats()                                                  -> counts per status and last update
  deposit_code(...)                                                   -> opens a "Deposit a coupon code" issue
  deposit_batch(entries)                                              -> opens a JSON-batch issue
  report_code(store, code, worked, date=None, notes="")               -> opens a "Report a code" issue

Reading needs no credentials: the ledger is fetched from the public raw GitHub URL.
Depositing and reporting open GitHub issues, which the repo's intake workflow turns
into ledger commits; that needs a GitHub token with "issues: write" on the repo
(a fine-grained token scoped to this one repo is enough) in the GITHUB_TOKEN env var.

Configuration (env vars, all optional):
  COUPON_SWARM_REPO   owner/name of the ledger repo        (default: OWNER/coupon-swarm)
  COUPON_SWARM_URL    raw URL of codes.json                 (default derived from the repo)
  GITHUB_TOKEN        token used for deposits and reports

Run:  python mcp/server.py            (stdio transport, for Claude Desktop, Cursor, etc.)
Needs: pip install mcp
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP

REPO = os.environ.get("COUPON_SWARM_REPO", "OWNER/coupon-swarm")
LEDGER_URL = os.environ.get("COUPON_SWARM_URL", f"https://raw.githubusercontent.com/{REPO}/main/codes.json")
API = "https://api.github.com"
CACHE_SECONDS = 300
_cache = {"at": 0.0, "data": None}

mcp = FastMCP("coupon-swarm", instructions=(
    "Shared ledger of public coupon codes with found/expiry/verification dates. "
    "Use find_codes before telling a user a code; use report_code after the user tries one; "
    "use deposit_code or deposit_batch for new public promotional codes you have seen on a credible page. "
    "Never deposit personal referral codes, single-use codes, or guessed codes."
))


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _fetch_ledger() -> dict:
    if _cache["data"] is not None and time.time() - _cache["at"] < CACHE_SECONDS:
        return _cache["data"]
    req = urllib.request.Request(LEDGER_URL, headers={"User-Agent": "coupon-swarm-mcp"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    _cache.update(at=time.time(), data=data)
    return data


def _github(method: str, path: str, payload: Optional[dict] = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set; deposits and reports open GitHub issues and need a token with issues:write")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{API}{path}", data=body, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "coupon-swarm-mcp",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from e


def _form_body(fields: list) -> str:
    """Render fields the way GitHub renders an issue form, so scripts/intake.py can parse it."""
    parts = []
    for label, value in fields:
        value = value if value not in (None, "") else "_No response_"
        parts.append(f"### {label}\n\n{value}")
    return "\n\n".join(parts) + "\n"


def _norm_store(store: str) -> str:
    s = store.strip().lower()
    s = re.sub(r"^https?://", "", s).split("/")[0]
    return s[4:] if s.startswith("www.") else s


@mcp.tool()
def find_codes(store: Optional[str] = None, region: Optional[str] = None,
               status: str = "active", query: Optional[str] = None, limit: int = 50) -> list:
    """Find coupon codes in the shared ledger.

    store: bare domain, e.g. 'geekbuying.com' (matches subdomains too). region: 'DK', 'EU', 'US', 'global'.
    status: 'active', 'unverified', 'any' (expired and dead codes are never returned). query: free text
    matched against store, discount, applies_to and notes. Each result carries found_on, expires_on and
    last_verified dates; tell the user how old the verification is.
    """
    data = _fetch_ledger()
    today = _today()
    out = []
    for e in data.get("codes", []):
        if e["status"] in ("expired", "dead"):
            continue
        if status != "any" and e["status"] != status:
            continue
        if e.get("expires_on") and e["expires_on"] < today:
            continue
        if store and not (e["store"] == _norm_store(store) or e["store"].endswith("." + _norm_store(store))):
            continue
        if region and region.upper() not in [r.upper() for r in e["region"]] and "global" not in e["region"]:
            continue
        if query:
            hay = " ".join([e["store"], e["discount"], e["applies_to"], e.get("notes") or ""]).lower()
            if query.lower() not in hay:
                continue
        out.append({k: e[k] for k in ("store", "code", "discount", "applies_to", "min_order", "region",
                                       "found_on", "expires_on", "last_verified", "status",
                                       "works_reports", "failed_reports", "source_url", "notes")})
        if len(out) >= limit:
            break
    return out


@mcp.tool()
def get_ledger_stats() -> dict:
    """Counts per status, number of stores, and when the ledger was last updated."""
    data = _fetch_ledger()
    counts = {}
    for e in data.get("codes", []):
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    return {"updated": data.get("updated"), "counts": counts,
            "stores": len({e["store"] for e in data.get("codes", [])}),
            "source": LEDGER_URL, "repo": f"https://github.com/{REPO}"}


@mcp.tool()
def deposit_code(store: str, code: str, discount: str, applies_to: str, region: str,
                 source_url: str, submitted_by: str, min_order: Optional[str] = None,
                 expires_on: Optional[str] = None, seen_on_brand_page_today: bool = False,
                 notes: str = "") -> dict:
    """Deposit one public promotional code. Opens an issue that a bot turns into a ledger entry.

    region: comma-separated country codes, 'EU' or 'global'. expires_on: YYYY-MM-DD if the source states it.
    seen_on_brand_page_today: true only if you saw the code on the brand's own current page or applied it
    successfully today; otherwise it is filed as 'unverified'. Never deposit referral, single-use or guessed codes.
    """
    body = _form_body([
        ("Store", _norm_store(store)), ("Code", code.strip()), ("Discount", discount), ("Applies to", applies_to),
        ("Minimum order", min_order), ("Region", region), ("Expires on", expires_on), ("Source URL", source_url),
        ("Did you see it work", "Yes, applied it or saw it on the brand's own page today (active)"
         if seen_on_brand_page_today else "No, found it on a secondary source (unverified)"),
        ("Submitted by", submitted_by), ("Notes", notes),
    ])
    issue = _github("POST", f"/repos/{REPO}/issues", {
        "title": f"[code] {_norm_store(store)}: {code.strip()}", "body": body, "labels": ["code-submission"]})
    return {"issue_url": issue.get("html_url"), "note": "A bot validates the entry and comments on the issue within a few minutes."}


@mcp.tool()
def deposit_batch(entries: list, submitted_by: str) -> dict:
    """Deposit many codes at once. entries: list of objects with keys store, code, discount, applies_to,
    region (list), found_on, source_url, status ('active' only with last_verified), and optionally
    min_order, expires_on, last_verified, notes. Opens one JSON-batch issue."""
    for e in entries:
        e.setdefault("submitted_by", submitted_by)
        e.setdefault("found_on", _today())
        e.setdefault("status", "unverified")
    body = ("### JSON entries\n\n```json\n" + json.dumps(entries, indent=2, ensure_ascii=False) + "\n```\n\n"
            "### Rules\n\n- [X] Every code here is a public promotional code, and I have not attempted purchases to test them.\n")
    issue = _github("POST", f"/repos/{REPO}/issues", {
        "title": f"[batch] {len(entries)} codes from {submitted_by}", "body": body, "labels": ["code-submission"]})
    return {"issue_url": issue.get("html_url"), "entries": len(entries)}


@mcp.tool()
def report_code(store: str, code: str, worked: bool, date_tried: Optional[str] = None, notes: str = "") -> dict:
    """Report that a listed code worked or failed when applied. Two failures with no later success mark it dead."""
    date_tried = date_tried or _today()
    date.fromisoformat(date_tried)  # raises on a bad date
    body = _form_body([
        ("Store", _norm_store(store)), ("Code", code.strip()),
        ("Result", "Worked" if worked else "Did not work (invalid, expired, or not applicable)"),
        ("Date", date_tried), ("Notes", notes),
    ])
    issue = _github("POST", f"/repos/{REPO}/issues", {
        "title": f"[report] {_norm_store(store)}: {code.strip()}", "body": body, "labels": ["code-report"]})
    return {"issue_url": issue.get("html_url")}


if __name__ == "__main__":
    mcp.run()
