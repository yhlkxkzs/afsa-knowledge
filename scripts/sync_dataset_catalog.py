#!/usr/bin/env python3
"""
Build / update dataset_catalog.json from local registry + import tracker.
External entries are appended by crawl_roboflow_catalog.py (never duplicates local ids).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / "data" / "dataset_catalog.json"
LOCAL_REGISTRY = Path("/home/yuhanlin/APP/AFSA/data/disease_classification/manifest/registry.json")
IMPORT_TRACKER = Path("/home/yuhanlin/Database/datasets/API/dataset_import_tracker.json")


def load_json(path: Path) -> dict | list:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_id(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def main() -> None:
    catalog = load_json(CATALOG_PATH)
    if not isinstance(catalog, dict):
        catalog = {}

    registry = load_json(LOCAL_REGISTRY)
    tracker = load_json(IMPORT_TRACKER)
    if not isinstance(tracker, dict):
        tracker = {}

    local_entries: list[dict] = []
    seen: set[str] = set()
    for ds in registry.get("datasets") or []:
        did = ds.get("dataset_id")
        if not did:
            continue
        key = normalize_id(did)
        if key in seen:
            continue
        seen.add(key)
        local_entries.append(
            {
                "dataset_id": did,
                "normalized_id": key,
                "source": "local",
                "path": ds.get("path"),
                "tier": ds.get("tier"),
                "scheme_12": bool(ds.get("scheme_12")),
                "classes": ds.get("classes") or [],
                "fruits": ds.get("fruits") or [],
                "imported_at": tracker.get(did) or tracker.get(key),
            }
        )

    external = catalog.get("external_sources") or []
    ext_seen = {normalize_id(x.get("dataset_id", "")) for x in external}

    catalog.update(
        {
            "version": 1,
            "description": catalog.get("description")
            or "Unified dataset catalog: local + external crawled sources",
            "local_registry_path": str(LOCAL_REGISTRY),
            "local_import_tracker_path": str(IMPORT_TRACKER),
            "local_datasets": local_entries,
            "local_count": len(local_entries),
            "external_sources": external,
            "external_count": len(external),
            "all_normalized_ids": sorted(seen | ext_seen),
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {CATALOG_PATH}: local={len(local_entries)} external={len(external)}")


if __name__ == "__main__":
    main()
