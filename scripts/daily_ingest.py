#!/usr/bin/env python3
"""
Daily ingest: pick >=10 disease/pest types (deprioritize last 2 days),
collect 5-10 HQ images per type from local datasets, generate zh/en text from labels.

Run on maintainer machine (local paths) or self-hosted runner.
GitHub-hosted runner: selects types + writes text; images only if paths exist / already in repo.

Usage:
  python3 scripts/daily_ingest.py
  python3 scripts/daily_ingest.py --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingest_lib import (
    CONFIG_PATH,
    TypeCandidate,
    append_history,
    build_bilingual_content,
    collect_images_for_type,
    copy_gallery_images,
    iter_types_from_catalog,
    load_catalog,
    load_history,
    load_json,
    select_daily_types,
    stable_item_id,
    upsert_knowledge_items,
)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Daily disease/pest knowledge ingest")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    cfg = load_json(CONFIG_PATH)
    catalog = load_catalog()
    history = load_history()
    candidates = iter_types_from_catalog(catalog)
    if not candidates:
        print("[error] no type candidates in catalog; run sync_dataset_catalog.py first")
        sys.exit(1)

    min_types = int(cfg.get("min_types_per_day", 10))
    min_img = int(cfg.get("min_images_per_type", 5))
    max_img = int(cfg.get("max_images_per_type", 10))
    batch: list[dict] = []
    skipped: list[str] = []
    tried: set[str] = set()
    ingested_keys: list[str] = []

    while len(batch) < min_types:
        need = min_types - len(batch)
        picks = select_daily_types(candidates, cfg, history, count=need, exclude=tried)
        if not picks:
            break
        for cand in picks:
            tried.add(cand.type_key)
            imgs = collect_images_for_type(cand, min_n=min_img, max_n=max_img)
            if len(imgs) < min_img:
                skipped.append(cand.type_key)
                print(f"[skip] {cand.type_key}: only {len(imgs)} images (need {min_img})")
                continue

            item_id = stable_item_id(cand)
            gallery = copy_gallery_images(item_id, imgs) if not args.dry_run else []
            gallery_count = len(imgs) if args.dry_run else len(gallery)
            if gallery_count < min_img:
                skipped.append(cand.type_key)
                print(f"[skip] {cand.type_key}: gallery copy failed ({gallery_count})")
                continue

            title_zh, title_en, summary_zh, summary_en, content_zh, content_en = build_bilingual_content(cand)
            disease_type = cand.label_slug if cand.category_id == "disease" else None
            batch.append(
                {
                    "id": item_id,
                    "category_id": cand.category_id,
                    "title_zh": title_zh,
                    "title_en": title_en,
                    "summary_zh": summary_zh,
                    "summary_en": summary_en,
                    "content_zh": content_zh,
                    "content_en": content_en,
                    "fruit_type": cand.fruit_type if cand.fruit_type != "general" else None,
                    "disease_type": disease_type,
                    "control_type": "chemical",
                    "image_url": (gallery[0] if gallery else f"/knowledge/images/{item_id}_1.jpg") if not args.dry_run else None,
                    "image_gallery": gallery if not args.dry_run else [f"(dry-run:{i+1})" for i in range(gallery_count)],
                    "image_source": {
                        "dataset_id": cand.dataset_id,
                        "label_slug": cand.label_slug,
                        "source": "local",
                        "gallery_count": gallery_count,
                    },
                    "ingest_type_key": cand.type_key,
                }
            )
            ingested_keys.append(cand.type_key)
            print(f"[ok] {cand.type_key} images={gallery_count}")
            if len(batch) >= min_types:
                break

    print(f"target={min_types} ingested={len(batch)} skipped={len(skipped)} tried={len(tried)}")

    if args.dry_run:
        print(f"dry-run: would upsert {len(batch)} items, skipped {len(skipped)}")
        return

    if batch:
        upsert_knowledge_items(batch)
    append_history(
        ingested_keys,
        {"ingested": len(batch), "skipped": skipped, "item_ids": [b["id"] for b in batch]},
    )
    print(f"done: ingested={len(batch)} skipped={len(skipped)}")


if __name__ == "__main__":
    main()
