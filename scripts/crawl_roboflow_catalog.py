#!/usr/bin/env python3
"""
Record external dataset candidates (e.g. Roboflow Universe) without re-importing locals.

Usage:
  python3 scripts/crawl_roboflow_catalog.py --add manual_entry.json
  python3 scripts/crawl_roboflow_catalog.py --list-new urls.txt

Each external record:
  dataset_id, source_url, platform, status, crawled_at, normalized_id
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "data" / "dataset_catalog.json"
CRAWL_LOG = PROJECT_ROOT / "data" / "external_crawl_log.jsonl"


def normalize_id(raw: str) -> str:
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def load_catalog() -> dict:
    if CATALOG_PATH.is_file():
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {"external_sources": [], "local_datasets": []}


def all_known_ids(catalog: dict) -> set[str]:
    ids: set[str] = set()
    for ds in catalog.get("local_datasets") or []:
        ids.add(normalize_id(ds.get("dataset_id", "")))
        ids.add(normalize_id(ds.get("normalized_id", "")))
    for ds in catalog.get("external_sources") or []:
        ids.add(normalize_id(ds.get("dataset_id", "")))
        ids.add(normalize_id(ds.get("normalized_id", "")))
    for x in catalog.get("all_normalized_ids") or []:
        ids.add(normalize_id(x))
    ids.discard("")
    return ids


def append_log(entry: dict) -> None:
    CRAWL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CRAWL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def add_external(record: dict, *, dry_run: bool = False) -> str:
    catalog = load_catalog()
    known = all_known_ids(catalog)
    did = record.get("dataset_id") or record.get("name") or record.get("url", "")
    nid = normalize_id(record.get("normalized_id") or did)
    if nid in known:
        append_log({"action": "skip_duplicate", "normalized_id": nid, "record": record})
        return "duplicate"

    entry = {
        "dataset_id": did,
        "normalized_id": nid,
        "platform": record.get("platform", "roboflow"),
        "source_url": record.get("url") or record.get("source_url"),
        "status": record.get("status", "catalogued"),
        "license": record.get("license"),
        "notes": record.get("notes"),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
    }
    if dry_run:
        append_log({"action": "dry_run_add", "entry": entry})
        return "would_add"

    external = catalog.setdefault("external_sources", [])
    external.append(entry)
    catalog["external_count"] = len(external)
    catalog["last_external_crawl_at"] = entry["crawled_at"]
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    append_log({"action": "added", "entry": entry})
    return "added"


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Register external datasets without duplicating local pool")
    p.add_argument("--add", type=Path, help="JSON file with one external dataset record")
    p.add_argument("--sync-local", action="store_true", help="Refresh local section via sync_dataset_catalog.py")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.sync_local:
        from sync_dataset_catalog import main as sync_main

        sync_main()

    if args.add:
        record = json.loads(args.add.read_text(encoding="utf-8"))
        status = add_external(record, dry_run=args.dry_run)
        print(status)
        return

    print("Use --add <file.json> or --sync-local. See data/dataset_catalog.json")


if __name__ == "__main__":
    main()
