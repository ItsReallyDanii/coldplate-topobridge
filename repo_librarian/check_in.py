#!/usr/bin/env python3
"""Minimal check-in utility for repo_librarian.

Subcommands:
- validate: validate catalog JSONL entries against catalog.schema.json
- check-in: append one entry to catalog.jsonl using explicit fields

No discovery logic. No physics or semantic inference.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def _load_json(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(path: Path) -> List[Dict]:
    entries: List[Dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {idx}: {e}")
    return entries


def _validate_enum(value: str, allowed: List[str], field: str) -> None:
    if value not in allowed:
        raise ValueError(f"Invalid {field}: '{value}'. Allowed: {allowed}")


def _validate_entry(entry: Dict, schema: Dict) -> None:
    required = set(schema.get("required", []))
    props = schema.get("properties", {})

    missing = [k for k in required if k not in entry]
    if missing:
        raise ValueError(f"Missing required keys: {missing}")

    if schema.get("additionalProperties") is False:
        unknown = [k for k in entry.keys() if k not in props]
        if unknown:
            raise ValueError(f"Unknown keys not allowed: {unknown}")

    for key, p in props.items():
        if key not in entry or "enum" not in p:
            continue
        _validate_enum(entry[key], p["enum"], key)

    auth = entry.get("authority", {})
    auth_schema = props.get("authority", {}).get("properties", {})
    for key, p in auth_schema.items():
        if "enum" in p:
            if key not in auth:
                raise ValueError(f"authority missing '{key}'")
            _validate_enum(auth[key], p["enum"], f"authority.{key}")

    evidence = entry.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("evidence must be a non-empty list")
    for i, ev in enumerate(evidence):
        if "file" not in ev or "lines" not in ev:
            raise ValueError(f"evidence[{i}] missing file/lines")



def cmd_validate(args: argparse.Namespace) -> int:
    schema = _load_json(Path(args.schema))
    entries = _load_jsonl(Path(args.catalog))

    if not entries:
        print("FAIL: catalog has no entries")
        return 1

    for i, entry in enumerate(entries, start=1):
        try:
            _validate_entry(entry, schema)
        except ValueError as e:
            print(f"FAIL: entry #{i} ({entry.get('entry_id', 'unknown')}): {e}")
            return 1

    print(f"PASS: validated {len(entries)} catalog entries")
    return 0


def cmd_check_in(args: argparse.Namespace) -> int:
    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog not found: {catalog_path}")

    evidence = [{"file": args.evidence_file, "lines": args.evidence_lines}]
    entry = {
        "entry_id": args.entry_id,
        "title": args.title,
        "object_type": args.object_type,
        "path": args.path,
        "authority": {
            "lifecycle": args.lifecycle,
            "validation": args.validation,
            "status": args.status,
        },
        "claim": args.claim,
        "evidence": evidence,
        "caveats": [args.caveat] if args.caveat else [],
        "novelty": args.novelty,
        "recency": args.recency,
        "credibility": args.credibility,
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    with open(catalog_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")

    print(f"APPENDED: {args.entry_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="repo_librarian catalog utility")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate catalog entries")
    p_val.add_argument("--catalog", default="repo_librarian/catalog.jsonl")
    p_val.add_argument("--schema", default="repo_librarian/catalog.schema.json")
    p_val.set_defaults(func=cmd_validate)

    p_add = sub.add_parser("check-in", help="Append one catalog entry")
    p_add.add_argument("--catalog", default="repo_librarian/catalog.jsonl")
    p_add.add_argument("--entry-id", required=True)
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--object-type", required=True)
    p_add.add_argument("--path", required=True)
    p_add.add_argument("--lifecycle", required=True)
    p_add.add_argument("--validation", required=True)
    p_add.add_argument("--status", required=True)
    p_add.add_argument("--claim", required=True)
    p_add.add_argument("--evidence-file", required=True)
    p_add.add_argument("--evidence-lines", required=True)
    p_add.add_argument("--caveat", default="")
    p_add.add_argument("--novelty", default="low")
    p_add.add_argument("--recency", default="unknown")
    p_add.add_argument("--credibility", default="medium")
    p_add.set_defaults(func=cmd_check_in)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
