#!/usr/bin/env python3
"""Remove all local knowledge images and clear image_url from JSON + SQLite."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import db

DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
ITEMS_ZH = DATA_DIR / "knowledge_items.json"
ITEMS_EN = DATA_DIR / "knowledge_items_en.json"


def clear_json(path: Path) -> int:
    if not path.is_file():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    for item in payload.get("items") or []:
        if item.pop("image_url", None) is not None:
            n += 1
        item.pop("image_source", None)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return n


def clear_db() -> int:
    db.init_db()
    conn = db.get_connection()
    try:
        cur = conn.execute("UPDATE knowledge SET image_url = NULL")
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def main() -> None:
    removed_files = 0
    if IMAGES_DIR.is_dir():
        for p in IMAGES_DIR.iterdir():
            if p.is_file():
                p.unlink()
                removed_files += 1
    n_zh = clear_json(ITEMS_ZH)
    n_en = clear_json(ITEMS_EN)
    n_db = clear_db()
    print(f"deleted image files: {removed_files}")
    print(f"cleared image_url in zh={n_zh} en={n_en} db_rows={n_db}")


if __name__ == "__main__":
    main()
