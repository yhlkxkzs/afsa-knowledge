#!/usr/bin/env python3
"""Import zh/en knowledge JSON files into knowledge.db."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import db

DATA = PROJECT_ROOT / "data"


def main() -> None:
    db.init_db()
    zh_path = DATA / "knowledge_items.json"
    en_path = DATA / "knowledge_items_en.json"
    n_zh = db.import_json_file(zh_path, locale="zh") if zh_path.is_file() else 0
    n_en = db.import_json_file(en_path, locale="en") if en_path.is_file() else 0
    print(f"synced zh={n_zh} en={n_en} -> {db.DB_PATH}")


if __name__ == "__main__":
    main()
