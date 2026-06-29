#!/usr/bin/env python3
"""
Pick high-quality representative images from LOCAL disease_recognition datasets
for knowledge items (disease/pest). Skips items already linked unless --force.

Matching rules (strict):
  - Dataset fruit must match item fruit_type
  - Dataset class must match item disease/pest label
  - Image path must fall under a matching class folder
  - Each source image is used at most once across all items
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import db
import paths
from knowledge_image_match import (
    IMAGE_EXTS,
    item_label_slug,
    iter_candidate_images,
    matching_classes,
)

DATA_DIR = paths.DATA_DIR
IMAGES_DIR = paths.images_dir()
ITEMS_PATH = paths.items_json("disease_pest", "zh")
ITEMS_EN_PATH = paths.items_json("disease_pest", "en")
REGISTRY_PATH = Path("/home/yuhanlin/APP/AFSA/data/disease_classification/manifest/registry.json")
INDEX_CACHE = paths.image_index_path()

MIN_SIDE = 512
MAX_CANDIDATES_PER_DS = 500


def build_image_index(datasets: list[dict]) -> dict[str, list[str]]:
    if INDEX_CACHE.is_file():
        cached = json.loads(INDEX_CACHE.read_text(encoding="utf-8"))
        if cached.get("version") == 2 and cached.get("entries"):
            return cached["entries"]

    entries: dict[str, list[str]] = {}
    for ds in datasets:
        did = ds.get("dataset_id")
        root = Path(ds.get("path") or "")
        if not did or not root.is_dir():
            continue
        paths: list[str] = []
        for p in root.rglob("*"):
            if p.suffix.lower() not in IMAGE_EXTS or not p.is_file():
                continue
            try:
                from PIL import Image

                with Image.open(p) as img:
                    w, h = img.size
                if min(w, h) >= MIN_SIDE:
                    paths.append(str(p))
            except Exception:
                continue
            if len(paths) >= MAX_CANDIDATES_PER_DS:
                break
        if paths:
            entries[did] = paths

    INDEX_CACHE.write_text(
        json.dumps({"version": 2, "entries": entries}, indent=2) + "\n",
        encoding="utf-8",
    )
    return entries


def load_items() -> list[dict]:
    payload = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    return payload.get("items") or []


def save_items(items: list[dict]) -> None:
    payload = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    payload["items"] = items
    payload["image_policy"] = "local_dataset_strict_v2"
    payload["image_updated_at"] = datetime.now(timezone.utc).isoformat()
    ITEMS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if ITEMS_EN_PATH.is_file():
        en_payload = json.loads(ITEMS_EN_PATH.read_text(encoding="utf-8"))
        zh_by_id = {x["id"]: x for x in items}
        for en_item in en_payload.get("items") or []:
            zh = zh_by_id.get(en_item.get("id"))
            if zh and zh.get("image_url"):
                en_item["image_url"] = zh["image_url"]
                if zh.get("image_source"):
                    en_item["image_source"] = zh["image_source"]
        en_payload["image_updated_at"] = payload["image_updated_at"]
        ITEMS_EN_PATH.write_text(json.dumps(en_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sharpness_score(path: Path) -> float:
    try:
        import numpy as np
        from PIL import Image

        img = Image.open(path).convert("L")
        w, h = img.size
        if min(w, h) < MIN_SIDE:
            return 0.0
        scale = MIN_SIDE / min(w, h)
        if scale < 1:
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        arr = np.asarray(img, dtype=np.float32)
        gx = float(np.abs(arr[:, 1:] - arr[:, :-1]).mean())
        gy = float(np.abs(arr[1:, :] - arr[:-1, :]).mean())
        return gx + gy
    except Exception:
        return float(path.stat().st_size) ** 0.5


def image_score(path: Path, tier_bonus: float) -> float:
    try:
        from PIL import Image

        with Image.open(path) as img:
            w, h = img.size
        if min(w, h) < MIN_SIDE:
            return 0.0
        return min(w, h) * 0.6 + sharpness_score(path) * 40 + tier_bonus
    except Exception:
        return 0.0


def pick_best_image(
    item: dict,
    datasets: list[dict],
    index: dict[str, list[str]],
    used_sources: set[str],
) -> tuple[Path | None, dict | None]:
    label = item_label_slug(item)
    if not label:
        return None, None

    best_path: Path | None = None
    best_score = 0.0
    best_meta: dict | None = None

    for ds in datasets:
        class_slugs = matching_classes(item, ds)
        if not class_slugs:
            continue
        tier_bonus = 120.0 if ds.get("scheme_12") else (60.0 if ds.get("tier") == "l3_fine" else 0.0)
        did = ds.get("dataset_id")
        for class_slug in class_slugs:
            for img in iter_candidate_images(ds, [class_slug], index):
                src_key = str(img.resolve())
                if src_key in used_sources:
                    continue
                sc = image_score(img, tier_bonus)
                if sc > best_score:
                    best_score = sc
                    best_path = img
                    best_meta = {
                        "dataset_id": did,
                        "label_slug": label,
                        "matched_class": class_slug,
                        "source_path": str(img),
                        "tier": ds.get("tier"),
                        "score": round(sc, 2),
                        "source": "local",
                    }
    return best_path, best_meta


def copy_item_image(item_id: str, src: Path) -> Path:
    out = IMAGES_DIR / f"{item_id}.jpg"
    try:
        from PIL import Image

        img = Image.open(src)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        w, h = img.size
        if min(w, h) > 900:
            ratio = 900 / min(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
        img.save(out, "JPEG", quality=90, optimize=True)
    except Exception:
        shutil.copy2(src, out.with_suffix(src.suffix))
        out = out.with_suffix(src.suffix)
    return out


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Assign HQ images from local datasets (strict matching)")
    p.add_argument("--force", action="store_true", help="Replace existing image_url")
    p.add_argument("--limit", type=int, default=0, help="Max items to process (0=all)")
    p.add_argument("--clear-wrong", action="store_true", help="Clear image_url when no strict match found")
    args = p.parse_args()

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    datasets = registry.get("datasets") or []
    print("building image index (v2, cached after first run)...")
    index = build_image_index(datasets)
    items = load_items()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    assigned = 0
    skipped = 0
    cleared = 0
    used_sources: set[str] = set()

    for item in items:
        if args.limit and assigned >= args.limit:
            break
        if item.get("category_id") not in {"disease", "pest"}:
            continue
        if item.get("image_url") and not args.force:
            skipped += 1
            continue

        src, meta = pick_best_image(item, datasets, index, used_sources)
        if not src or not meta:
            if args.clear_wrong or args.force:
                old = IMAGES_DIR / f"{item['id']}.jpg"
                if old.is_file():
                    old.unlink()
                item.pop("image_url", None)
                item.pop("image_source", None)
                cleared += 1
            else:
                skipped += 1
            continue

        used_sources.add(str(src.resolve()))
        item_id = item["id"]
        out = copy_item_image(item_id, src)
        item["image_url"] = f"/knowledge/images/{out.name}"
        item["image_source"] = meta
        assigned += 1
        if assigned <= 5 or assigned % 25 == 0:
            print(f"  [ok] {item_id} <- {meta['dataset_id']} ({meta['label_slug']})")

    save_items(items)
    db.init_db()
    db.import_json_file(ITEMS_PATH, locale="zh")
    if ITEMS_EN_PATH.is_file():
        db.import_json_file(ITEMS_EN_PATH, locale="en")
    print(f"assigned={assigned} skipped={skipped} cleared={cleared} unique_sources={len(used_sources)}")


if __name__ == "__main__":
    main()
