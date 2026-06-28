# -*- coding: utf-8 -*-
"""Weighted knowledge feed: lower probability for items seen more often."""

from __future__ import annotations

import json
import random
from typing import Any

# weight = 1 / (1 + IMPRESSION_DECAY * impressions + READ_DECAY * reads)
IMPRESSION_DECAY = 0.55
READ_DECAY = 1.0
MIN_WEIGHT = 0.02
DEFAULT_FEED_LIMIT = 10


def parse_seen_counts(raw: str | None) -> dict[str, dict[str, int]]:
    """Parse JSON: { item_id: { impression: n, read: m } } or { item_id: n }."""
    if not raw or not str(raw).strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, int]] = {}
    for item_id, val in data.items():
        key = str(item_id).strip()
        if not key:
            continue
        if isinstance(val, dict):
            out[key] = {
                "impression": int(val.get("impression") or val.get("impressions") or 0),
                "read": int(val.get("read") or val.get("reads") or 0),
            }
        else:
            out[key] = {"impression": int(val or 0), "read": 0}
    return out


def item_weight(counts: dict[str, int] | None) -> float:
    counts = counts or {}
    imp = max(0, int(counts.get("impression", 0)))
    reads = max(0, int(counts.get("read", 0)))
    w = 1.0 / (1.0 + IMPRESSION_DECAY * imp + READ_DECAY * reads)
    return max(MIN_WEIGHT, w)


def weighted_sample(
    candidates: list[dict[str, Any]],
    seen: dict[str, dict[str, int]],
    limit: int,
    *,
    exclude_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    exclude_ids = exclude_ids or set()
    pool = [c for c in candidates if c.get("id") not in exclude_ids]
    if not pool:
        return []
    limit = min(limit, len(pool))
    picked: list[dict[str, Any]] = []
    remaining = list(pool)
    for _ in range(limit):
        weights = [item_weight(seen.get(str(c.get("id")), {})) for c in remaining]
        total = sum(weights)
        if total <= 0:
            break
        r = random.random() * total
        acc = 0.0
        chosen_idx = 0
        for i, w in enumerate(weights):
            acc += w
            if r <= acc:
                chosen_idx = i
                break
        picked.append(remaining.pop(chosen_idx))
    return picked


def merge_seen(
    base: dict[str, dict[str, int]], extra: dict[str, dict[str, int]]
) -> dict[str, dict[str, int]]:
    out = {k: dict(v) for k, v in base.items()}
    for item_id, counts in extra.items():
        row = out.setdefault(item_id, {"impression": 0, "read": 0})
        row["impression"] = max(row["impression"], int(counts.get("impression", 0)))
        row["read"] = max(row["read"], int(counts.get("read", 0)))
    return out


def personal_repo_lines(
    user_id: str,
    events: list[dict[str, Any]],
    *,
    locale: str = "zh",
) -> tuple[str, list[str]]:
    """Return (relative path, jsonl lines) for user personal repo."""
    from datetime import datetime, timezone

    month = datetime.now(timezone.utc).strftime("%Y-%m")
    rel_path = f"logs/knowledge_reads/{month}.jsonl"
    lines: list[str] = []
    now = datetime.now(timezone.utc).isoformat()
    for ev in events:
        line = {
            "schema_version": 1,
            "app": "afsa_mobile",
            "data_tier": "log",
            "retention_days": 90,
            "user_id": user_id,
            "locale": locale,
            "item_id": ev.get("item_id"),
            "event": ev.get("event", "impression"),
            "category_id": ev.get("category_id"),
            "recorded_at": ev.get("at") or now,
        }
        lines.append(json.dumps(line, ensure_ascii=False))
    return rel_path, lines
