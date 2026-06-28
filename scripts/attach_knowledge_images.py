# -*- coding: utf-8 -*-
"""
为知识库条目挂接图片 URL：从 data/knowledge_image_urls.json 的 by_title 查表；
可选 --fetch 时对未匹配的条目用 Wikimedia Commons API 按 search_en 或标题搜图。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
sys.path.insert(0, str(PROJECT_ROOT))

import db

COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def fetch_commons_image_url(search_term: str) -> str | None:
    """用 Commons API 按关键词搜一张图，返回直接图片 URL。"""
    try:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": search_term,
            "gsrnamespace": 6,
            "gsrlimit": 1,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 400,
            "format": "json",
        }
        url = COMMONS_API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "KnowledgeBaseBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None
        page = next(iter(pages.values()))
        info = page.get("imageinfo", [{}])[0]
        return info.get("url") or info.get("thumburl")
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser(description="为知识条目标注 image_url")
    p.add_argument("--fetch", action="store_true", help="对未在 by_title 中的条目尝试 Commons API 搜图（较慢）")
    args = p.parse_args()

    mapping_path = DATA_DIR / "knowledge_image_urls.json"
    items_path = DATA_DIR / "knowledge_items.json"
    if not items_path.exists():
        print(f"未找到 {items_path}")
        return
    with open(items_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    items = payload.get("items", [])
    if not mapping_path.exists():
        by_title = {}
        search_en = {}
        default_by_category = {}
    else:
        with open(mapping_path, "r", encoding="utf-8") as f:
            m = json.load(f)
        by_title = m.get("by_title", {})
        search_en = m.get("search_en", {})
        default_by_category = m.get("default_by_category", {})

    default_fallback = default_by_category.get("general") or "https://upload.wikimedia.org/wikipedia/commons/9/90/Single_apple.jpg"

    updated = 0
    for item in items:
        title = item.get("title", "")
        if item.get("image_url"):
            continue
        url = by_title.get(title)
        if not url and args.fetch:
            search_term = search_en.get(title) or title.replace("（", " ").replace("）", " ")
            url = fetch_commons_image_url(search_term)
            if url:
                time.sleep(0.35)
        if not url:
            category_id = item.get("category_id", "general")
            url = default_by_category.get(category_id) or default_fallback
        if url:
            item["image_url"] = url
            updated += 1

    with open(items_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"已为 {updated} 条挂接 image_url，写入 {items_path}")

    db.init_db()
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        n_db = 0
        for item in items:
            if not item.get("image_url"):
                continue
            cur.execute("UPDATE knowledge SET image_url = ? WHERE id = ?", (item["image_url"], item["id"]))
            n_db += 1
        conn.commit()
        print(f"已同步 DB：{n_db} 条 image_url")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
