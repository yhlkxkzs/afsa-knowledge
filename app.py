# -*- coding: utf-8 -*-
"""
知识库后台 API：按 docs 约定提供 filters、items、item 详情。
首屏默认 5 条，下拉加载每次 10 条（App 传 offset + limit）。
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request

import db
from api_handlers import handle_feed, handle_reads_get, handle_reads_import, handle_reads_post
from locale_util import resolve_locale

app = Flask(__name__)
DEFAULT_FIRST_PAGE_SIZE = 10
DEFAULT_LOAD_MORE_SIZE = 10


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.route("/knowledge/filters", methods=["GET", "OPTIONS"])
def filters():
    if request.method == "OPTIONS":
        return "", 204
    try:
        locale = resolve_locale(request)
        data = db.get_filters_from_db(locale=locale)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/knowledge/feed", methods=["GET", "OPTIONS"])
def knowledge_feed():
    if request.method == "OPTIONS":
        return "", 204
    try:
        return handle_feed()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/knowledge/reads", methods=["GET", "POST", "OPTIONS"])
def knowledge_reads():
    if request.method == "OPTIONS":
        return "", 204
    try:
        if request.method == "GET":
            return handle_reads_get()
        if request.args.get("import") == "1":
            return handle_reads_import()
        return handle_reads_post()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/knowledge/items", methods=["GET", "OPTIONS"])
def items():
    if request.method == "OPTIONS":
        return "", 204
    try:
        category_id = request.args.get("category_id")
        fruit_type = request.args.get("fruit_type")
        disease_type = request.args.get("disease_type")
        control_type = request.args.get("control_type")
        keyword = request.args.get("keyword")
        page = max(1, request.args.get("page", type=int) or 1)
        # 未传 limit 时默认 5 条（首屏）；传了 limit 则用传入值（下拉时传 10）
        limit_arg = request.args.get("limit", type=int)
        limit = max(1, min(100, limit_arg if limit_arg is not None else DEFAULT_FIRST_PAGE_SIZE))
        # 随机下发且不重复：App 传 exclude_ids=已收到的 id 列表（逗号分隔），本次返回的都不会在其中
        exclude_raw = request.args.get("exclude_ids") or request.args.get("exclude_ids[]")
        if exclude_raw:
            exclude_ids = [x.strip() for x in str(exclude_raw).split(",") if x.strip()]
        else:
            exclude_ids = []
        offset_arg = request.args.get("offset", type=int)
        offset = None if offset_arg is None else max(0, offset_arg)
        # random=1：该分类内随机排序后返回（首页 4 次请求每类 5/3 条用此参数）
        random_param = request.args.get("random", "").strip()
        random_order = random_param in ("1", "true", "True")
        locale = resolve_locale(request)

        items_list, has_more = db.list_items(
            category_id=category_id,
            fruit_type=fruit_type or None,
            disease_type=disease_type or None,
            control_type=control_type or None,
            keyword=keyword or None,
            page=page,
            limit=limit,
            offset=offset,
            exclude_ids=exclude_ids if exclude_ids else None,
            random_order=random_order,
            locale=locale,
        )
        resp = {"items": items_list, "has_more": has_more, "locale": locale}
        if offset is not None and not exclude_ids:
            resp["offset"] = offset
            if has_more:
                resp["next_offset"] = offset + len(items_list)
        return jsonify(resp)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/knowledge/items/<item_id>", methods=["GET", "OPTIONS"])
def item_detail(item_id):
    if request.method == "OPTIONS":
        return "", 204
    try:
        locale = resolve_locale(request)
        item = db.get_item_by_id(item_id, locale=locale)
        if item is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(item)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def main():
    db.init_db()
    port = int(os.environ.get("PORT", 32230))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"知识库 API: http://{host}:{port}")
    print("  GET /knowledge/filters  筛选选项")
    print("  GET /knowledge/feed  加权推荐流（首屏/下拉各10条）")
    print("  POST /knowledge/reads  记录阅读/曝光（同步个人仓 jsonl）")
    print("  GET /knowledge/items/<id>  详情（含 content）")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
