#!/usr/bin/env python3
"""
One-time migration:
  data/knowledge_items*.json  ->  disease_pest / control / general
  Drop disease/pest entries without image_url.
  Move images -> disease_pest/images/, catalog -> catalog/
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import paths

OLD_ZH = paths.DATA_DIR / "knowledge_items.json"
OLD_EN = paths.DATA_DIR / "knowledge_items_en.json"
OLD_IMAGES = paths.DATA_DIR / "images"


def _load_items(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("items") or []


def _write_items(path: Path, items: list[dict], meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"count": len(items), "items": items, **meta}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _split(items: list[dict], *, require_image: bool) -> tuple[list, list, list]:
    disease_pest: list[dict] = []
    control: list[dict] = []
    general: list[dict] = []
    for item in items:
        cat = item.get("category_id")
        if cat in ("disease", "pest"):
            if require_image and not item.get("image_url"):
                continue
            disease_pest.append(item)
        elif cat == "control":
            control.append(item)
        elif cat == "general":
            general.append(item)
    return disease_pest, control, general


def _move_images(kept_ids: set[str]) -> int:
    dst = paths.images_dir()
    dst.mkdir(parents=True, exist_ok=True)
    moved = 0
    if not OLD_IMAGES.is_dir():
        return 0
    for p in OLD_IMAGES.iterdir():
        if not p.is_file() or p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        name = p.name
        ok = any(name == f"{iid}.jpg" or name.startswith(f"{iid}_") for iid in kept_ids)
        if not ok:
            continue
        out = dst / name
        shutil.copy2(p, out)
        moved += 1
    return moved


def main() -> None:
    zh_items = _load_items(OLD_ZH)
    en_items = _load_items(OLD_EN)
    en_by_id = {i["id"]: i for i in en_items}

    dp_zh, ctrl_zh, gen_zh = _split(zh_items, require_image=True)
    dp_en = [en_by_id[i["id"]] for i in dp_zh if i["id"] in en_by_id]
    _, ctrl_en, gen_en = _split(en_items, require_image=False)

    kept_ids = {i["id"] for i in dp_zh}
    moved = _move_images(kept_ids)

    _write_items(
        paths.items_json("disease_pest", "zh"),
        dp_zh,
        {
            "domain": "disease_pest",
            "locale": "zh",
            "policy": "image_required",
            "source": "local datasets + ingest pipeline",
        },
    )
    _write_items(
        paths.items_json("disease_pest", "en"),
        dp_en,
        {
            "domain": "disease_pest",
            "locale": "en",
            "policy": "image_required",
            "source": "mirrored from disease_pest/zh",
        },
    )
    _write_items(
        paths.items_json("control", "zh"),
        ctrl_zh,
        {"domain": "control", "locale": "zh", "policy": "text_search", "source": "agronomy templates"},
    )
    _write_items(
        paths.items_json("control", "en"),
        [en_by_id[i["id"]] for i in ctrl_zh if i["id"] in en_by_id],
        {"domain": "control", "locale": "en", "policy": "text_search"},
    )
    _write_items(
        paths.items_json("general", "zh"),
        gen_zh,
        {"domain": "general", "locale": "zh", "policy": "text_search", "source": "agronomy templates"},
    )
    _write_items(
        paths.items_json("general", "en"),
        [en_by_id[i["id"]] for i in gen_zh if i["id"] in en_by_id],
        {"domain": "general", "locale": "en", "policy": "text_search"},
    )

    # catalog + ingest
    paths.CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("dataset_catalog.json", "local_image_index.json", "ingest_search_seeds.json"):
        src = paths.DATA_DIR / name
        if src.is_file():
            shutil.copy2(src, paths.CATALOG_DIR / name)
    for name in ("ingest_config.json", "ingest_history.json"):
        src = paths.DATA_DIR / name
        if src.is_file():
            shutil.copy2(src, paths.DISEASE_PEST_DIR / name)

    import db

    db.rebuild_all_from_data()

    print(
        f"migrated disease_pest={len(dp_zh)} control={len(ctrl_zh)} general={len(gen_zh)} "
        f"images_copied={moved} removed_disease_pest_without_image="
        f"{sum(1 for i in zh_items if i.get('category_id') in ('disease','pest')) - len(dp_zh)}"
    )


if __name__ == "__main__":
    main()
