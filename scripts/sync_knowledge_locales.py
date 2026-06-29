#!/usr/bin/env python3
"""Import zh/en knowledge JSON files into knowledge.db; mirror image fields zh -> en."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import db

DATA = PROJECT_ROOT / "data"


def mirror_image_fields() -> int:
    zh_path = DATA / "knowledge_items.json"
    en_path = DATA / "knowledge_items_en.json"
    if not zh_path.is_file() or not en_path.is_file():
        return 0
    zh_payload = json.loads(zh_path.read_text(encoding="utf-8"))
    en_payload = json.loads(en_path.read_text(encoding="utf-8"))
    zh_by_id = {x["id"]: x for x in zh_payload.get("items") or []}
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
    mirrored = mirror_image_fields()
    if mirrored:
        print(f"mirrored image fields on {mirrored} en item field(s)")
    db.init_db()
    zh_path = DATA / "knowledge_items.json"
    en_path = DATA / "knowledge_items_en.json"
    n_zh = db.import_json_file(zh_path, locale="zh") if zh_path.is_file() else 0
    n_en = db.import_json_file(en_path, locale="en") if en_path.is_file() else 0
    print(f"synced zh={n_zh} en={n_en} -> {db.DB_PATH}")


if __name__ == "__main__":
    main()
