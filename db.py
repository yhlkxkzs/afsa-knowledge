# -*- coding: utf-8 -*-
"""
知识库存储：SQLite，支持 zh/en 双语（locale 列，主键 id+locale）。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import i18n

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "knowledge.db"

SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS knowledge (
  id TEXT NOT NULL,
  locale TEXT NOT NULL DEFAULT 'zh',
  category_id TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  content TEXT NOT NULL,
  fruit_type TEXT,
  disease_type TEXT,
  control_type TEXT,
  image_url TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (id, locale)
);

CREATE INDEX IF NOT EXISTS idx_category ON knowledge(category_id);
CREATE INDEX IF NOT EXISTS idx_locale ON knowledge(locale);
CREATE INDEX IF NOT EXISTS idx_fruit ON knowledge(fruit_type);
CREATE INDEX IF NOT EXISTS idx_disease ON knowledge(disease_type);
CREATE INDEX IF NOT EXISTS idx_control ON knowledge(control_type);
"""

READ_STATS_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_read_stats (
  user_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  locale TEXT NOT NULL DEFAULT 'zh',
  impression_count INTEGER NOT NULL DEFAULT 0,
  read_count INTEGER NOT NULL DEFAULT 0,
  last_impression_at TEXT,
  last_read_at TEXT,
  updated_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, item_id, locale)
);
CREATE INDEX IF NOT EXISTS idx_read_user ON knowledge_read_stats(user_id, locale);
"""


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def _migrate_legacy_table(conn: sqlite3.Connection) -> None:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge'")
    if cur.fetchone() is None:
        conn.executescript(SCHEMA_V2)
        conn.commit()
        return

    cols = _table_columns(conn, "knowledge")
    if "locale" in cols:
        conn.execute("UPDATE knowledge SET locale='zh' WHERE locale IS NULL OR locale=''")
        conn.commit()
        return

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge_legacy (
          id TEXT PRIMARY KEY,
          category_id TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL,
          content TEXT NOT NULL,
          fruit_type TEXT,
          disease_type TEXT,
          control_type TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          image_url TEXT
        );
        """
    )
    conn.execute("DELETE FROM knowledge_legacy")
    conn.execute(
        """
        INSERT INTO knowledge_legacy
        (id, category_id, title, summary, content, fruit_type, disease_type, control_type, created_at, image_url)
        SELECT id, category_id, title, summary, content, fruit_type, disease_type, control_type, created_at, image_url
        FROM knowledge
        """
    )
    conn.execute("DROP TABLE knowledge")
    conn.executescript(SCHEMA_V2)
    conn.execute(
        """
        INSERT INTO knowledge
        (id, locale, category_id, title, summary, content, fruit_type, disease_type, control_type, image_url, created_at)
        SELECT id, 'zh', category_id, title, summary, content, fruit_type, disease_type, control_type, image_url, created_at
        FROM knowledge_legacy
        """
    )
    conn.execute("DROP TABLE knowledge_legacy")
    conn.commit()


def init_db():
    conn = get_connection()
    try:
        _migrate_legacy_table(conn)
        conn.executescript(READ_STATS_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _row_to_item(row: sqlite3.Row, include_content: bool = False, locale: str = i18n.DEFAULT_LOCALE) -> dict[str, Any]:
    loc = i18n.normalize_locale(locale)
    fruit_id = row["fruit_type"]
    d = {
        "id": row["id"],
        "locale": row["locale"] if "locale" in row.keys() else loc,
        "category_id": row["category_id"],
        "title": row["title"],
        "summary": row["summary"],
        "fruit_types": [i18n.fruit_label(fruit_id, loc)] if fruit_id else [],
        "fruit_type_id": fruit_id or None,
        "disease_type": row["disease_type"] or None,
        "disease_type_name": i18n.disease_label(row["disease_type"], loc) if row["disease_type"] else None,
        "control_type": row["control_type"] or None,
        "control_type_name": i18n.control_label(row["control_type"], loc) if row["control_type"] else None,
    }
    if include_content:
        d["content"] = row["content"]
    if "image_url" in row.keys() and row["image_url"]:
        d["image_url"] = row["image_url"]
    return d


def list_items(
    category_id: str | None = None,
    fruit_type: str | None = None,
    disease_type: str | None = None,
    control_type: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    limit: int = 15,
    offset: int | None = None,
    exclude_ids: list[str] | None = None,
    random_order: bool = True,
    locale: str = i18n.DEFAULT_LOCALE,
) -> tuple[list[dict], bool]:
    loc = i18n.normalize_locale(locale)
    if exclude_ids:
        exclude_ids = [x.strip() for x in exclude_ids if x and x.strip()]
    if offset is None:
        offset = (page - 1) * limit
    fetch = limit + 1
    conn = get_connection()
    try:
        sql = """
          SELECT id, locale, category_id, title, summary, content, fruit_type, disease_type, control_type, image_url
          FROM knowledge WHERE locale = ?
        """
        params: list = [loc]
        if category_id and category_id.lower() != "all":
            sql += " AND category_id = ?"
            params.append(category_id)
        if fruit_type:
            sql += " AND fruit_type = ?"
            params.append(fruit_type)
        if disease_type:
            sql += " AND disease_type = ?"
            params.append(disease_type)
        if control_type:
            sql += " AND control_type = ?"
            params.append(control_type)
        if keyword and keyword.strip():
            k = f"%{keyword.strip()}%"
            sql += " AND (title LIKE ? OR summary LIKE ?)"
            params.extend([k, k])
        if exclude_ids:
            sql += " AND id NOT IN (" + ",".join("?" * len(exclude_ids)) + ")"
            params.extend(exclude_ids)
        if random_order:
            sql += " ORDER BY RANDOM() LIMIT ? OFFSET ?"
            params.extend([fetch, 0])
        else:
            sql += " ORDER BY id LIMIT ? OFFSET ?"
            params.extend([fetch, offset])
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    has_more = len(rows) > limit
    items = [_row_to_item(r, include_content=False, locale=loc) for r in rows[:limit]]
    return items, has_more


def get_item_by_id(item_id: str, locale: str = i18n.DEFAULT_LOCALE) -> dict | None:
    loc = i18n.normalize_locale(locale)
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, locale, category_id, title, summary, content, fruit_type, disease_type, control_type, image_url
            FROM knowledge WHERE id = ? AND locale = ?
            """,
            (item_id, loc),
        )
        row = cur.fetchone()
        if row is None and loc != i18n.DEFAULT_LOCALE:
            cur = conn.execute(
                """
                SELECT id, locale, category_id, title, summary, content, fruit_type, disease_type, control_type, image_url
                FROM knowledge WHERE id = ? AND locale = ?
                """,
                (item_id, i18n.DEFAULT_LOCALE),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return _row_to_item(row, include_content=True, locale=loc)
    finally:
        conn.close()


def get_filters_from_db(locale: str = i18n.DEFAULT_LOCALE) -> dict[str, list[dict]]:
    loc = i18n.normalize_locale(locale)
    conn = get_connection()
    try:
        fruit = set()
        disease = set()
        control = set()
        cur = conn.execute(
            "SELECT fruit_type, disease_type, control_type FROM knowledge WHERE locale = ?",
            (loc,),
        )
        for row in cur:
            if row["fruit_type"]:
                fid = row["fruit_type"]
                fruit.add((fid, i18n.fruit_label(fid, loc)))
            if row["disease_type"]:
                did = row["disease_type"]
                disease.add((did, i18n.disease_label(did, loc)))
            if row["control_type"]:
                cid = row["control_type"]
                control.add((cid, i18n.control_label(cid, loc)))
        return {
            "locale": loc,
            "fruitTypes": [{"id": i, "name": n} for i, n in sorted(fruit)],
            "diseaseTypes": [{"id": i, "name": n} for i, n in sorted(disease)],
            "controlTypes": [{"id": i, "name": n} for i, n in sorted(control)],
        }
    finally:
        conn.close()


def upsert_items(items: list[dict[str, Any]], locale: str = i18n.DEFAULT_LOCALE) -> int:
    loc = i18n.normalize_locale(locale)
    conn = get_connection()
    n = 0
    try:
        cur = conn.cursor()
        for e in items:
            cur.execute(
                """
                INSERT OR REPLACE INTO knowledge
                (id, locale, category_id, title, summary, content, fruit_type, disease_type, control_type, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    e["id"],
                    loc,
                    e["category_id"],
                    e["title"],
                    e["summary"],
                    e["content"],
                    e.get("fruit_type"),
                    e.get("disease_type"),
                    e.get("control_type"),
                    e.get("image_url"),
                ),
            )
            n += 1
        conn.commit()
    finally:
        conn.close()
    return n


def import_json_file(path: Path, locale: str = i18n.DEFAULT_LOCALE) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items") or payload
    if isinstance(items, dict):
        items = items.get("items") or []
    return upsert_items(items, locale=locale)


def fetch_candidates(
    *,
    category_id: str | None = None,
    fruit_type: str | None = None,
    disease_type: str | None = None,
    control_type: str | None = None,
    keyword: str | None = None,
    locale: str = i18n.DEFAULT_LOCALE,
) -> list[dict]:
    """All items matching filters (for weighted feed sampling)."""
    loc = i18n.normalize_locale(locale)
    conn = get_connection()
    try:
        sql = """
          SELECT id, locale, category_id, title, summary, content, fruit_type, disease_type, control_type, image_url
          FROM knowledge WHERE locale = ?
        """
        params: list = [loc]
        if category_id and category_id.lower() != "all":
            sql += " AND category_id = ?"
            params.append(category_id)
        if fruit_type:
            sql += " AND fruit_type = ?"
            params.append(fruit_type)
        if disease_type:
            sql += " AND disease_type = ?"
            params.append(disease_type)
        if control_type:
            sql += " AND control_type = ?"
            params.append(control_type)
        if keyword and keyword.strip():
            k = f"%{keyword.strip()}%"
            sql += " AND (title LIKE ? OR summary LIKE ?)"
            params.extend([k, k])
        sql += " ORDER BY id"
        cur = conn.execute(sql, params)
        return [_row_to_item(r, include_content=False, locale=loc) for r in cur.fetchall()]
    finally:
        conn.close()


def get_read_stats(user_id: str, locale: str = i18n.DEFAULT_LOCALE) -> dict[str, dict[str, int]]:
    loc = i18n.normalize_locale(locale)
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT item_id, impression_count, read_count
            FROM knowledge_read_stats WHERE user_id = ? AND locale = ?
            """,
            (user_id, loc),
        )
        out: dict[str, dict[str, int]] = {}
        for row in cur:
            out[row["item_id"]] = {
                "impression": int(row["impression_count"] or 0),
                "read": int(row["read_count"] or 0),
            }
        return out
    finally:
        conn.close()


def record_read_events(
    user_id: str,
    events: list[dict[str, Any]],
    *,
    locale: str = i18n.DEFAULT_LOCALE,
) -> dict[str, dict[str, int]]:
    """Increment impression/read counts. Returns full stats map for user."""
    from datetime import datetime, timezone

    loc = i18n.normalize_locale(locale)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cur = conn.cursor()
        for ev in events:
            item_id = str(ev.get("item_id") or "").strip()
            if not item_id:
                continue
            event = str(ev.get("event") or "impression").lower()
            cur.execute(
                """
                SELECT impression_count, read_count FROM knowledge_read_stats
                WHERE user_id = ? AND item_id = ? AND locale = ?
                """,
                (user_id, item_id, loc),
            )
            row = cur.fetchone()
            imp = int(row[0]) if row else 0
            reads = int(row[1]) if row else 0
            if event == "read":
                reads += 1
                last_read = now
                last_imp = None
            else:
                imp += 1
                last_imp = now
                last_read = None
            if row:
                if event == "read":
                    cur.execute(
                        """
                        UPDATE knowledge_read_stats
                        SET read_count = ?, last_read_at = ?, updated_at = ?
                        WHERE user_id = ? AND item_id = ? AND locale = ?
                        """,
                        (reads, last_read, now, user_id, item_id, loc),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE knowledge_read_stats
                        SET impression_count = ?, last_impression_at = ?, updated_at = ?
                        WHERE user_id = ? AND item_id = ? AND locale = ?
                        """,
                        (imp, last_imp, now, user_id, item_id, loc),
                    )
            else:
                cur.execute(
                    """
                    INSERT INTO knowledge_read_stats
                    (user_id, item_id, locale, impression_count, read_count, last_impression_at, last_read_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        item_id,
                        loc,
                        imp,
                        reads,
                        last_imp if event != "read" else 0,
                        last_read if event == "read" else None,
                        now,
                    ),
                )
        conn.commit()
    finally:
        conn.close()
    return get_read_stats(user_id, locale=loc)


def import_read_stats_from_personal_repo(
    user_id: str,
    stats: dict[str, dict[str, int]],
    *,
    locale: str = i18n.DEFAULT_LOCALE,
) -> int:
    """Merge read counts from personal repo snapshot (take max per field)."""
    loc = i18n.normalize_locale(locale)
    existing = get_read_stats(user_id, locale=loc)
    merged = existing
    for item_id, counts in stats.items():
        row = merged.setdefault(item_id, {"impression": 0, "read": 0})
        row["impression"] = max(row["impression"], int(counts.get("impression", 0)))
        row["read"] = max(row["read"], int(counts.get("read", 0)))
    conn = get_connection()
    n = 0
    try:
        cur = conn.cursor()
        for item_id, counts in merged.items():
            cur.execute(
                """
                INSERT INTO knowledge_read_stats (user_id, item_id, locale, impression_count, read_count, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(user_id, item_id, locale) DO UPDATE SET
                  impression_count = excluded.impression_count,
                  read_count = excluded.read_count,
                  updated_at = excluded.updated_at
                """,
                (user_id, item_id, loc, counts["impression"], counts["read"]),
            )
            n += 1
        conn.commit()
    finally:
        conn.close()
    return n
