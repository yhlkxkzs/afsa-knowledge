#!/usr/bin/env python3
"""
Pick high-quality representative images from LOCAL disease_recognition datasets
for knowledge items (disease/pest). Skips items already linked unless --force.

Quality score: resolution + sharpness (Laplacian variance) + tier bonus.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import db

DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
ITEMS_PATH = DATA_DIR / "knowledge_items.json"
REGISTRY_PATH = Path("/home/yuhanlin/APP/AFSA/data/disease_classification/manifest/registry.json")
LABELMAP_PATH = Path(
    "/home/yuhanlin/APP/AFSA/tasks/disease_classification/exports/yolo8m_seg/labelmap.json"
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MIN_SIDE = 512
MAX_CANDIDATES = 40
INDEX_CACHE = DATA_DIR / "local_image_index.json"


def build_image_index(datasets: list[dict]) -> dict[str, list[str]]:
    if INDEX_CACHE.is_file():
        cached = json.loads(INDEX_CACHE.read_text(encoding="utf-8"))
        if cached.get("version") == 1 and cached.get("entries"):
            return cached["entries"]

    entries: dict[str, list[str]] = {}
    for ds in datasets:
        did = ds.get("dataset_id")
        root = Path(ds.get("path") or "")
        if not did or not root.is_dir():
            continue
        paths: list[str] = []
        for p in root.rglob("*"):
            if p.suffix.lower() in IMAGE_EXTS and p.is_file():
                try:
                    from PIL import Image

                    with Image.open(p) as img:
                        w, h = img.size
                    if min(w, h) >= MIN_SIDE:
                        paths.append(str(p))
                except Exception:
                    continue
                if len(paths) >= MAX_CANDIDATES:
                    break
        if paths:
            entries[did] = paths

    INDEX_CACHE.write_text(
        json.dumps({"version": 1, "entries": entries}, indent=2) + "\n",
        encoding="utf-8",
    )
    return entries


def load_items() -> list[dict]:
    payload = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    return payload.get("items") or []


def save_items(items: list[dict]) -> None:
    payload = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    payload["items"] = items
    payload["image_policy"] = "local_dataset_hq_v1"
    payload["image_updated_at"] = datetime.now(timezone.utc).isoformat()
    ITEMS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
        gx = np.abs(arr[:, 1:] - arr[:, :-1]).mean()
        gy = np.abs(arr[1:, :] - arr[:-1, :]).mean()
        return float(gx + gy)
    except Exception:
        return float(path.stat().st_size) ** 0.5


def image_score(path: Path, tier_bonus: float) -> float:
    try:
        from PIL import Image

        with Image.open(path) as img:
            w, h = img.size
        if min(w, h) < MIN_SIDE:
            return 0.0
        res = min(w, h)
        sharp = sharpness_score(path)
        return res * 0.6 + sharp * 40 + tier_bonus
    except Exception:
        return 0.0


def tokenize(s: str) -> set[str]:
    return {t for t in re.split(r"[_\s\-./]+", (s or "").lower()) if len(t) > 2}


def dataset_matches(item: dict, ds: dict) -> bool:
    fruit = (item.get("fruit_type") or "").lower()
    dis = (item.get("disease_type") or "").lower()
    title = (item.get("title") or "").lower()
    tokens = tokenize(fruit) | tokenize(dis) | tokenize(title)
    if not tokens:
        return False
    ds_tokens = tokenize(ds.get("dataset_id", ""))
    ds_tokens |= tokenize(" ".join(ds.get("classes") or []))
    ds_tokens |= tokenize(" ".join(ds.get("fruits") or []))
    ds_tokens |= tokenize(str(ds.get("path", "")))
    overlap = tokens & ds_tokens
    if fruit and fruit in ds_tokens:
        return True
    if dis and dis in ds_tokens:
        return True
    return len(overlap) >= 2


def pick_best_image(
    item: dict, datasets: list[dict], index: dict[str, list[str]]
) -> tuple[Path | None, dict | None]:
    best_path: Path | None = None
    best_score = 0.0
    best_meta: dict | None = None
    for ds in datasets:
        if not dataset_matches(item, ds):
            continue
        tier_bonus = 120.0 if ds.get("scheme_12") else (60.0 if ds.get("tier") == "l3_fine" else 0.0)
        did = ds.get("dataset_id")
        for img_str in index.get(did or "", []):
            img = Path(img_str)
            sc = image_score(img, tier_bonus)
            if sc > best_score:
                best_score = sc
                best_path = img
                best_meta = {
                    "dataset_id": did,
                    "source_path": str(img),
                    "tier": ds.get("tier"),
                    "score": round(sc, 2),
                    "source": "local",
                }
    return best_path, best_meta


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Assign HQ images from local datasets")
    p.add_argument("--force", action="store_true", help="Replace existing image_url")
    p.add_argument("--limit", type=int, default=0, help="Max items to process (0=all)")
    args = p.parse_args()

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    datasets = registry.get("datasets") or []
    print("building image index (cached after first run)...")
    index = build_image_index(datasets)
    items = load_items()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    assigned = 0
    skipped = 0
    for i, item in enumerate(items):
        if args.limit and assigned >= args.limit:
            break
        if item.get("category_id") not in {"disease", "pest"}:
            continue
        if item.get("image_url") and not args.force:
            skipped += 1
            continue
        src, meta = pick_best_image(item, datasets, index)
        if not src or not meta:
            skipped += 1
            continue
        item_id = item["id"]
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
        item["image_url"] = f"/knowledge/images/{out.name}"
        item["image_source"] = meta
        assigned += 1

    save_items(items)
    db.init_db()
    db.import_json_file(ITEMS_PATH, locale="zh")
    print(f"assigned={assigned} skipped={skipped} -> {IMAGES_DIR}")


if __name__ == "__main__":
    main()
