#!/usr/bin/env python3
"""
Knowledge ingest: bootstrap 20 types, then every 2 days add 7-9 types (7-9 images each).

Usage:
  python3 scripts/daily_ingest.py              # auto: bootstrap or interval update
  python3 scripts/daily_ingest.py --bootstrap  # force initial 20 types
  python3 scripts/daily_ingest.py --force      # ignore 2-day interval
  python3 scripts/daily_ingest.py --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingest_lib import (
    CONFIG_PATH,
    append_history,
    build_bilingual_content,
    collect_images_for_type,
    copy_gallery_images,
    existing_ingest_type_keys,
    iter_types_from_catalog,
    load_catalog,
    load_history,
    load_json,
    mark_bootstrap_done,
    resolve_run_plan,
    select_daily_types,
    should_skip_interval,
    stable_item_id,
    upsert_knowledge_items,
)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Bootstrap / bi-daily disease/pest knowledge ingest")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--bootstrap", action="store_true", help="Force initial bootstrap batch")
    p.add_argument("--force", action="store_true", help="Run even if within update_interval_days")
    args = p.parse_args()

    cfg = load_json(CONFIG_PATH)
    history = load_history()

    if should_skip_interval(history, cfg) and not args.force and not args.bootstrap:
        interval = int(cfg.get("update_interval_days", 2))
        print(f"[skip] last run within {interval} days; use --force to run anyway")
        return

    plan = resolve_run_plan(cfg, history, force_bootstrap=args.bootstrap)
    mode = "bootstrap" if plan["bootstrap"] else "update"
    min_types = plan["type_target"]
    min_img = plan["min_images"]
    max_img = plan["max_images"]
    print(f"mode={mode} target_types={min_types} images={min_img}-{max_img}")

    catalog = load_catalog()
    candidates = iter_types_from_catalog(catalog)
    already = existing_ingest_type_keys()
    candidates = [c for c in candidates if c.type_key not in already]
    if not candidates:
        print("[error] no new type candidates left in catalog")
        sys.exit(1)

    batch: list[dict] = []
    skipped: list[str] = []
    tried: set[str] = set()
    ingested_keys: list[str] = []
    used_sources: set[str] = set()

    while len(batch) < min_types:
        need = min_types - len(batch)
        picks = select_daily_types(candidates, cfg, history, count=need, exclude=tried)
        if not picks:
            break
        for cand in picks:
            tried.add(cand.type_key)
            imgs = collect_images_for_type(
                cand, min_n=min_img, max_n=max_img, used_sources=used_sources
            )
            if len(imgs) < min_img:
                skipped.append(cand.type_key)
                print(f"[skip] {cand.type_key}: only {len(imgs)} images (need {min_img})")
                continue

            item_id = stable_item_id(cand)
            if not args.dry_run:
                gallery, cover = copy_gallery_images(item_id, imgs)
                gallery_count = len(gallery)
                for src in imgs:
                    used_sources.add(str(src.resolve()))
            else:
                gallery, cover = [], None
                gallery_count = len(imgs)

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
                    "image_url": cover or (gallery[0] if gallery else None),
                    "image_gallery": gallery,
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
        {
            "ingested": len(batch),
            "skipped": skipped,
            "item_ids": [b["id"] for b in batch],
            "mode": mode,
            "bootstrap": plan["bootstrap"],
        },
    )
    if plan["bootstrap"] and len(batch) > 0:
        mark_bootstrap_done(cfg, load_history())
    print(f"done: mode={mode} ingested={len(batch)} skipped={len(skipped)}")


if __name__ == "__main__":
    main()
