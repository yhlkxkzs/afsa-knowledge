#!/usr/bin/env python3
"""Import all domain JSON files into knowledge.db; mirror disease_pest images zh -> en."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import db
import paths


def mirror_disease_pest_images() -> int:
    zh_path = paths.items_json("disease_pest", "zh")
    en_path = paths.items_json("disease_pest", "en")
    if not zh_path.is_file() or not en_path.is_file():
        return 0
    zh_by_id = {x["id"]: x for x in json.loads(zh_path.read_text(encoding="utf-8")).get("items") or []}
    en_payload = json.loads(en_path.read_text(encoding="utf-8"))
    n = 0
    for item in en_payload.get("items") or []:
        zh = zh_by_id.get(item.get("id"))
        if not zh:
            continue
        for key in ("image_url", "image_gallery", "image_source", "ingest_type_key"):
            if zh.get(key) != item.get(key):
                if zh.get(key) is None:
                    item.pop(key, None)
                else:
                    item[key] = zh[key]
                n += 1
    en_payload["count"] = len(en_payload.get("items") or [])
    en_path.write_text(json.dumps(en_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return n


def main() -> None:
    mirrored = mirror_disease_pest_images()
    if mirrored:
        print(f"mirrored {mirrored} image field(s) on disease_pest/en")
    counts = db.rebuild_all_from_data()
    print(f"rebuilt DB {counts} -> {db.DB_PATH}")


if __name__ == "__main__":
    main()
