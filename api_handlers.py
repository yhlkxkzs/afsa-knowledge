# -*- coding: utf-8 -*-
"""Shared Flask handlers for knowledge feed + read tracking."""

from __future__ import annotations

import json

from flask import jsonify, request

import db
import feed_util
from locale_util import resolve_locale

DEFAULT_FEED_LIMIT = feed_util.DEFAULT_FEED_LIMIT


def handle_feed():
    locale = resolve_locale(request)
    category_id = request.args.get("category_id")
    fruit_type = request.args.get("fruit_type")
    disease_type = request.args.get("disease_type")
    control_type = request.args.get("control_type")
    keyword = request.args.get("keyword")
    user_id = (request.args.get("user_id") or request.args.get("github_user") or "").strip()

    limit_arg = request.args.get("limit", type=int)
    limit = max(1, min(50, limit_arg if limit_arg is not None else DEFAULT_FEED_LIMIT))

    exclude_raw = request.args.get("exclude_ids") or request.args.get("exclude_ids[]")
    exclude_ids = {x.strip() for x in str(exclude_raw or "").split(",") if x.strip()}

    client_seen = feed_util.parse_seen_counts(request.args.get("seen_counts"))
    server_seen = db.get_read_stats(user_id, locale=locale) if user_id else {}
    seen = feed_util.merge_seen(server_seen, client_seen)

    candidates = db.fetch_candidates(
        category_id=category_id,
        fruit_type=fruit_type or None,
        disease_type=disease_type or None,
        control_type=control_type or None,
        keyword=keyword or None,
        locale=locale,
    )
    items = feed_util.weighted_sample(candidates, seen, limit, exclude_ids=exclude_ids)
    pool_left = len([c for c in candidates if c.get("id") not in exclude_ids and c.get("id") not in {i["id"] for i in items}])

    return jsonify(
        {
            "items": items,
            "has_more": pool_left > 0,
            "locale": locale,
            "feed_mode": "weighted",
            "limit": limit,
            "seen_counts": seen,
            "weight_formula": "1 / (1 + 0.55*impression + 1.0*read)",
        }
    )


def handle_reads_post():
    locale = resolve_locale(request)
    body = request.get_json(silent=True) or {}
    user_id = str(body.get("user_id") or body.get("github_user") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    events = body.get("events") or []
    if not isinstance(events, list):
        return jsonify({"error": "events must be a list"}), 400

    stats = db.record_read_events(user_id, events, locale=locale)
    repo_path, repo_lines = feed_util.personal_repo_lines(user_id, events, locale=locale)

    return jsonify(
        {
            "ok": True,
            "user_id": user_id,
            "locale": locale,
            "seen_counts": stats,
            "personal_repo_sync": {
                "path": repo_path,
                "append_lines": repo_lines,
                "sidecar_hint": {
                    "schema_version": 1,
                    "data_tier": "log",
                    "retention_days": 90,
                    "task_type": "knowledge_read_log",
                },
            },
        }
    )


def handle_reads_get():
    locale = resolve_locale(request)
    user_id = (request.args.get("user_id") or request.args.get("github_user") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    stats = db.get_read_stats(user_id, locale=locale)
    return jsonify({"user_id": user_id, "locale": locale, "seen_counts": stats})


def handle_reads_import():
    """POST body: { user_id, seen_counts: { id: { impression, read } } } from personal repo restore."""
    locale = resolve_locale(request)
    body = request.get_json(silent=True) or {}
    user_id = str(body.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    raw = body.get("seen_counts")
    if isinstance(raw, str):
        stats = feed_util.parse_seen_counts(raw)
    elif isinstance(raw, dict):
        stats = feed_util.parse_seen_counts(json.dumps(raw))
    else:
        return jsonify({"error": "seen_counts required"}), 400
    n = db.import_read_stats_from_personal_repo(user_id, stats, locale=locale)
    return jsonify({"ok": True, "merged": n, "seen_counts": db.get_read_stats(user_id, locale=locale)})
