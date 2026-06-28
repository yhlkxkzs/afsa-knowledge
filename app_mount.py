# -*- coding: utf-8 -*-
"""
知识库子应用：路由为 /filters, /items, /items/<id>，供统一网关挂载到 /knowledge 下。
挂载后路径为 /knowledge/filters, /knowledge/items, /knowledge/items/<id>。
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import db
from locale_util import resolve_locale

IMAGES_DIR = Path(db.DATA_DIR) / "images"

DEFAULT_FIRST_PAGE_SIZE = 5
DEFAULT_LOAD_MORE_SIZE = 10


def create_knowledge_app():
    app = Flask("knowledge")

    @app.after_request
    def cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    @app.route("/filters", methods=["GET", "OPTIONS"])
    def filters():
        if request.method == "OPTIONS":
            return "", 204
        try:
            locale = resolve_locale(request)
            data = db.get_filters_from_db(locale=locale)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/items", methods=["GET", "OPTIONS"])
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
            limit_arg = request.args.get("limit", type=int)
            limit = max(1, min(100, limit_arg if limit_arg is not None else DEFAULT_FIRST_PAGE_SIZE))
            exclude_raw = request.args.get("exclude_ids") or request.args.get("exclude_ids[]")
            if exclude_raw:
                exclude_ids = [x.strip() for x in str(exclude_raw).split(",") if x.strip()]
            else:
                exclude_ids = []
            offset_arg = request.args.get("offset", type=int)
            offset = None if offset_arg is None else max(0, offset_arg)
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

    @app.route("/images/<path:filename>", methods=["GET", "OPTIONS"])
    def serve_image(filename):
        """本地图片：先下载到 data/images 后由此路由提供，响应更快。"""
        if request.method == "OPTIONS":
            return "", 204
        if not IMAGES_DIR.is_dir():
            return jsonify({"error": "images not configured"}), 404
        # 只允许文件名，防止路径穿越
        if ".." in filename or "/" in filename:
            return jsonify({"error": "invalid filename"}), 400
        try:
            return send_from_directory(IMAGES_DIR, filename, max_age=86400)
        except Exception:
            return jsonify({"error": "not found"}), 404

    @app.route("/items/<item_id>", methods=["GET", "OPTIONS"])
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

    return app
