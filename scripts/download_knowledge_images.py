# -*- coding: utf-8 -*-
"""
将 knowledge_items.json 中的图片 URL 下载到 data/images/，并缩小尺寸以节省空间。
之后 API 返回相对路径 /knowledge/images/<id>.jpg，由后端本地提供，访问更快。
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
ITEMS_PATH = DATA_DIR / "knowledge_items.json"
MAPPING_PATH = DATA_DIR / "knowledge_image_urls.json"

# 可下载的图片扩展名 / Content-Type；其余用默认图
IMAGE_EXT_RE = re.compile(r"\.(jpe?g|png|gif|webp|bmp)$", re.I)
MAX_WIDTH = 600  # 缩图最大宽度，省空间
JPEG_QUALITY = 85


def get_default_mappings():
    if not MAPPING_PATH.exists():
        return {}, {}
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        m = json.load(f)
    return m.get("default_by_category", {}), m.get("default_by_fruit_type", {})


def download_image(url: str, out_path: Path) -> bool:
    """下载图片到 out_path，并用 PIL 缩放到 MAX_WIDTH 宽、JPEG 保存。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KnowledgeBaseBot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "image" not in content_type and not IMAGE_EXT_RE.search(url):
            return False
    except Exception as e:
        print(f"  [skip] {url[:60]}... -> {e}")
        return False

    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        w, h = img.size
        if w > MAX_WIDTH:
            ratio = MAX_WIDTH / w
            img = img.resize((MAX_WIDTH, int(h * ratio)), Image.Resampling.LANCZOS)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except Exception as e:
        print(f"  [resize/save] {out_path.name} -> {e}")
        return False


def main():
    import argparse
    p = argparse.ArgumentParser(description="下载知识库图片到本地并缩图")
    p.add_argument("--delay", type=float, default=1.2, help="每次请求间隔秒数，避免 429（默认 1.2）")
    p.add_argument("--force-replace", action="store_true", help="Re-download http(s) URLs even if local file exists (never replaces with generic defaults)")
    args = p.parse_args()
    delay = max(0.5, args.delay)

    if not ITEMS_PATH.exists():
        print(f"未找到 {ITEMS_PATH}")
        sys.exit(1)

    with open(ITEMS_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)
    items = payload.get("items", [])
    default_by_category, _default_by_fruit_type = get_default_mappings()

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    updated = 0
    for i, item in enumerate(items):
        item_id = item.get("id")
        if not item_id:
            continue
        url = (item.get("image_url") or "").strip()
        fruit_type = item.get("fruit_type") or "general"
        category_id = item.get("category_id", "general")
        # Local images are authoritative; never overwrite with generic defaults.
        if url.startswith("/knowledge/images/"):
            continue
        # Non-image http links: skip rather than substitute a shared default image.
        elif not url or not IMAGE_EXT_RE.search(url.split("?")[0]):
            continue
        out_path = IMAGES_DIR / f"{item_id}.jpg"
        if download_image(url, out_path):
            item["image_url"] = f"/knowledge/images/{item_id}.jpg"
            updated += 1
            if updated <= 5 or updated % 50 == 0:
                print(f"  ok {item_id}")
        if delay and i < len(items) - 1:
            import time
            time.sleep(delay)

    with open(ITEMS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"已下载并写入 {updated} 张图到 {IMAGES_DIR}，并更新 {ITEMS_PATH}")

    # 同步 DB
    sys.path.insert(0, str(PROJECT_ROOT))
    import db
    db.init_db()
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        for item in items:
            if item.get("image_url"):
                cur.execute("UPDATE knowledge SET image_url = ? WHERE id = ?", (item["image_url"], item["id"]))
        conn.commit()
        print("已同步 knowledge.db 中的 image_url")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
