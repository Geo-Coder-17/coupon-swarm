"""Validate codes.json against schema.json and the ledger rules. Exit 1 on any problem.

Usage: python scripts/validate.py [path/to/codes.json]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger as L  # noqa: E402


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else L.LEDGER
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    problems = []

    try:
        import jsonschema
        with open(L.SCHEMA, encoding="utf-8") as f:
            schema = json.load(f)
        for err in sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in err.path) or "(root)"
            problems.append(f"schema: {where}: {err.message}")
    except ImportError:
        print("note: jsonschema not installed, running rule checks only", file=sys.stderr)

    seen = {}
    for i, entry in enumerate(data.get("codes", [])):
        for p in L.validate_entry(entry):
            problems.append(f"codes[{i}] {entry.get('id', '?')}: {p}")
        if entry.get("id") in seen:
            problems.append(f"codes[{i}] {entry['id']}: duplicate of codes[{seen[entry['id']]}]")
        seen[entry.get("id")] = i

    if problems:
        print(f"{len(problems)} problem(s) in {path}:")
        for p in problems:
            print(" -", p)
        return 1
    print(f"{path}: {len(data.get('codes', []))} entries, all valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
