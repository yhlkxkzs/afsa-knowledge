#!/usr/bin/env python3
"""Shared logic for daily disease/pest knowledge ingest."""

from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = DATA_DIR / "ingest_config.json"
HISTORY_PATH = DATA_DIR / "ingest_history.json"
CATALOG_PATH = DATA_DIR / "dataset_catalog.json"
IMAGES_DIR = DATA_DIR / "images"
ITEMS_ZH = DATA_DIR / "knowledge_items.json"
ITEMS_EN = DATA_DIR / "knowledge_items_en.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
PEST_HINTS = (
    "aphid", "mite", "borer", "thrip", "whitefly", "beetle", "moth", "fly",
    "hopper", "miner", "worm", "grub", "scale", "pest", "insect", "caterpillar",
)


@dataclass(frozen=True)
class TypeCandidate:
    category_id: str  # disease | pest
    type_key: str
    fruit_type: str
    label_slug: str
    dataset_id: str
    dataset_path: str | None
    tier: str | None
    scheme_12: bool


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def is_pest_label(slug: str) -> bool:
    s = slug.lower()
    return any(h in s for h in PEST_HINTS)


def is_healthy_label(slug: str) -> bool:
    s = slug.lower()
    if s in {"healthy", "health", "normal"}:
        return True
    if "healthy" in s or "normal_leaf" in s or s.endswith("_normal") or "_normal_" in s:
        return True
    return s.endswith("_healthy") or s.startswith("healthy_")


def registry_path() -> Path:
    env = os.environ.get("AFSA_REGISTRY_PATH", "").strip()
    if env:
        return Path(env)
    cfg = load_json(CONFIG_PATH)
    return Path(cfg.get("default_registry_path", ""))


def load_catalog() -> dict:
    if CATALOG_PATH.is_file():
        return load_json(CATALOG_PATH)
    # fallback build from registry if on maintainer machine
    reg = registry_path()
    if reg.is_file():
        from sync_dataset_catalog import main as _sync  # noqa: F401

        import subprocess

        subprocess.run(["python3", str(PROJECT_ROOT / "scripts" / "sync_dataset_catalog.py")], check=False)
    return load_json(CATALOG_PATH)


def iter_types_from_catalog(catalog: dict) -> list[TypeCandidate]:
    out: list[TypeCandidate] = []
    seen: set[str] = set()
    for ds in catalog.get("local_datasets") or []:
        fruits = ds.get("fruits") or ["general"]
        classes = ds.get("classes") or []
        path = ds.get("path")
        for cls in classes:
            slug = normalize_slug(str(cls))
            if not slug or is_healthy_label(slug):
                continue
            cat = "pest" if is_pest_label(slug) else "disease"
            for fruit in fruits:
                fruit = normalize_slug(str(fruit)) or "general"
                key = f"{cat}:{fruit}:{slug}"
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    TypeCandidate(
                        category_id=cat,
                        type_key=key,
                        fruit_type=fruit,
                        label_slug=slug,
                        dataset_id=str(ds.get("dataset_id", "")),
                        dataset_path=path,
                        tier=ds.get("tier"),
                        scheme_12=bool(ds.get("scheme_12")),
                    )
                )
    return out


def load_history() -> dict:
    h = load_json(HISTORY_PATH)
    if not h.get("days"):
        h = {"version": 1, "days": []}
    return h


def bootstrap_completed(history: dict, cfg: dict) -> bool:
    if history.get("bootstrap_completed"):
        return True
    return bool(cfg.get("bootstrap_completed"))


def days_since_last_run(history: dict) -> int | None:
    raw = history.get("last_run_at")
    if not raw:
        return None
    try:
        last = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - last).days
    except ValueError:
        return None


def resolve_run_plan(cfg: dict, history: dict, *, force_bootstrap: bool = False) -> dict:
    bootstrap = force_bootstrap or not bootstrap_completed(history, cfg)
    if bootstrap:
        type_target = int(cfg.get("bootstrap_types", 20))
    else:
        lo = int(cfg.get("min_types_per_run", 7))
        hi = int(cfg.get("max_types_per_run", 9))
        type_target = random.randint(lo, hi)
    min_img = int(cfg.get("min_images_per_type", 7))
    max_img = int(cfg.get("max_images_per_type", 9))
    return {
        "bootstrap": bootstrap,
        "type_target": type_target,
        "min_images": min_img,
        "max_images": max_img,
    }


def should_skip_interval(history: dict, cfg: dict) -> bool:
    if not bootstrap_completed(history, cfg):
        return False
    interval = int(cfg.get("update_interval_days", 2))
    elapsed = days_since_last_run(history)
    if elapsed is None:
        return False
    return elapsed < interval


def existing_ingest_type_keys() -> set[str]:
    keys: set[str] = set()
    for path in (ITEMS_ZH,):
        payload = load_json(path)
        for item in payload.get("items") or []:
            if item.get("ingest_type_key"):
                keys.add(str(item["ingest_type_key"]))
            item_id = item.get("id") or ""
            parts = item_id.split("_")
            if len(parts) >= 3 and parts[0] in {"disease", "pest"}:
                keys.add(f"{parts[0]}:{parts[1]}:{'_'.join(parts[2:])}")
    history = load_history()
    for row in history.get("days") or []:
        keys.update(row.get("type_keys") or [])
    return keys


def mark_bootstrap_done(cfg: dict, history: dict) -> None:
    cfg["bootstrap_completed"] = True
    save_json(CONFIG_PATH, cfg)
    history["bootstrap_completed"] = True
    history["bootstrap_completed_at"] = datetime.now(timezone.utc).isoformat()
    save_json(HISTORY_PATH, history)


def recent_type_keys(history: dict, days: int = 2) -> set[str]:
    """Types covered in the last N calendar days (inclusive)."""
    today = date.today()
    keys: set[str] = set()
    for row in history.get("days") or []:
        try:
            d = date.fromisoformat(str(row.get("date"))[:10])
        except ValueError:
            continue
        if (today - d).days <= days:
            keys.update(row.get("type_keys") or [])
    return keys


def type_selection_weight(
    candidate: TypeCandidate,
    history: dict,
    cfg: dict,
) -> float:
    penalty_days = int(cfg.get("recency_penalty_days", 2))
    recent = recent_type_keys(history, penalty_days)
    if candidate.type_key in recent:
        return float(cfg.get("recency_weight", 0.12))
    # covered older than penalty window but within week
    week_keys: set[str] = set()
    today = date.today()
    for row in history.get("days") or []:
        try:
            d = date.fromisoformat(str(row.get("date"))[:10])
        except ValueError:
            continue
        if penalty_days < (today - d).days <= 7:
            week_keys.update(row.get("type_keys") or [])
    if candidate.type_key in week_keys:
        return float(cfg.get("recent_week_weight", 0.45))
    return float(cfg.get("fresh_weight", 1.0))


def select_daily_types(
    candidates: list[TypeCandidate],
    cfg: dict,
    history: dict,
    *,
    count: int | None = None,
    exclude: set[str] | None = None,
) -> list[TypeCandidate]:
    min_n = count if count is not None else int(cfg.get("min_types_per_run", cfg.get("min_types_per_day", 7)))
    exclude = exclude or set()
    pool = [c for c in candidates if c.type_key not in exclude]
    if not pool:
        return []

    ratio = cfg.get("disease_pest_ratio") or [0.7, 0.3]
    dis_target = max(1, int(min_n * float(ratio[0])))
    pest_target = max(1, min_n - dis_target)

    diseases = [c for c in pool if c.category_id == "disease"]
    pests = [c for c in pool if c.category_id == "pest"]

    def weighted_pick(source: list[TypeCandidate], n: int) -> list[TypeCandidate]:
        picked: list[TypeCandidate] = []
        remaining = list(source)
        for _ in range(min(n, len(remaining))):
            weights = [type_selection_weight(c, history, cfg) for c in remaining]
            total = sum(weights)
            if total <= 0:
                break
            r = random.random() * total
            acc = 0.0
            idx = 0
            for i, w in enumerate(weights):
                acc += w
                if r <= acc:
                    idx = i
                    break
            picked.append(remaining.pop(idx))
        return picked

    chosen = weighted_pick(diseases, dis_target) + weighted_pick(pests, pest_target)
    if len(chosen) < min_n:
        rest = [c for c in pool if c not in chosen]
        chosen.extend(weighted_pick(rest, min_n - len(chosen)))
    return chosen[: min(min_n, len(chosen))]


def tokenize(s: str) -> set[str]:
    return {t for t in re.split(r"[_\s\-./]+", (s or "").lower()) if len(t) > 2}


def image_quality_score(path: Path, tier_bonus: float) -> float:
    try:
        import numpy as np
        from PIL import Image

        with Image.open(path) as img:
            w, h = img.size
        if min(w, h) < 512:
            return 0.0
        gray = Image.open(path).convert("L")
        if min(w, h) > 512:
            gray = gray.resize((512, int(h * 512 / w)), Image.Resampling.LANCZOS)
        arr = np.asarray(gray, dtype=np.float32)
        sharp = float(np.abs(arr[:, 1:] - arr[:, :-1]).mean() + np.abs(arr[1:, :] - arr[:-1, :]).mean())
        return min(w, h) * 0.6 + sharp * 40 + tier_bonus
    except Exception:
        return 0.0


INDEX_CACHE = DATA_DIR / "local_image_index.json"


def load_image_index() -> dict[str, list[str]]:
    if not INDEX_CACHE.is_file():
        return {}
    cached = load_json(INDEX_CACHE)
    if cached.get("version") == 1 and cached.get("entries"):
        return cached["entries"]
    return {}


def path_matches_label(path: Path, label_slug: str, dataset_root: Path | None = None) -> bool:
    import sys

    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from knowledge_image_match import path_matches_label as _match

    return _match(path, label_slug, dataset_root)


def collect_images_for_type(
    cand: TypeCandidate,
    *,
    min_n: int,
    max_n: int,
    used_sources: set[str] | None = None,
) -> list[Path]:
    """Strict fruit+label images from dataset class folders (same rules as App)."""
    import sys

    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from knowledge_image_match import iter_candidate_images, matching_classes

    used = used_sources or set()
    catalog = load_catalog()
    ds = next((d for d in (catalog.get("local_datasets") or []) if d.get("dataset_id") == cand.dataset_id), None)
    if not ds:
        return []

    item = {
        "fruit_type": cand.fruit_type,
        "disease_type": cand.label_slug,
        "category_id": cand.category_id,
        "id": stable_item_id(cand),
    }
    class_slugs = matching_classes(item, ds)
    if not class_slugs:
        return []

    tier_bonus = 120.0 if cand.scheme_12 else (60.0 if cand.tier == "l3_fine" else 0.0)
    index = load_image_index()
    scored: list[tuple[float, Path]] = []
    for class_slug in class_slugs:
        for p in iter_candidate_images(ds, [class_slug], index):
            src_key = str(p.resolve())
            if src_key in used:
                continue
            sc = image_quality_score(p, tier_bonus)
            if sc > 0:
                scored.append((sc, p))
            if len(scored) >= max_n * 12:
                break

    scored.sort(key=lambda x: -x[0])
    seen: set[str] = set()
    picked: list[Path] = []
    for _, p in scored:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        picked.append(p)
        if len(picked) >= max_n:
            break
    if len(picked) < min_n:
        return []
    return picked[:max_n]


def stable_item_id(cand: TypeCandidate) -> str:
    return f"{cand.category_id}_{cand.fruit_type}_{cand.label_slug}"


def build_bilingual_content(cand: TypeCandidate) -> tuple[str, str, str, str, str, str]:
    """Return title_zh, title_en, summary_zh, summary_en, content_zh, content_en."""
    import i18n

    fruit_zh = i18n.fruit_label(cand.fruit_type, "zh")
    fruit_en = i18n.fruit_label(cand.fruit_type, "en")
    if cand.category_id == "pest":
        name_zh = i18n.disease_label(cand.label_slug, "zh") or cand.label_slug.replace("_", " ")
        name_en = i18n.disease_label(cand.label_slug, "en") or cand.label_slug.replace("_", " ").title()
        title_zh = f"{fruit_zh}{name_zh}" if fruit_zh != "通用" else name_zh
        title_en = f"{fruit_en} {name_en}".strip() if fruit_en != "General" else name_en
        summary_zh = f"{title_zh}：为害特点、识别要点与综合防治。"
        summary_en = f"{title_en}: damage symptoms, identification, and integrated control."
        content_zh = (
            f"【为害特点】\n{title_zh}可取食嫩梢、叶片或果实，造成卷曲、斑点、蛀孔或传播病毒。\n\n"
            f"【识别要点】\n根据为害状、虫态与发生期识别；本条目配图来自数据集标注类别「{cand.label_slug}」。\n\n"
            f"【防治要点】\n农业防治（清园、轮作）+ 物理诱杀 + 生物防治 + 适期用药轮换。"
        )
        content_en = (
            f"[Damage]\n{title_en} may feed on shoots, leaves, or fruit, causing curling, spotting, bore holes, or virus transmission.\n\n"
            f"[Identification]\nIdentify by damage patterns, life stage, and timing; images align with dataset label `{cand.label_slug}`.\n\n"
            f"[Management]\nCombine sanitation, monitoring, biological control, and targeted pesticides with rotation."
        )
    else:
        name_zh = cand.label_slug.replace("_", " ")
        # try i18n disease parts
        parts = cand.label_slug.split("_")
        zh_bits: list[str] = []
        for p in parts:
            if p in i18n.FRUIT_LABELS:
                zh_bits.append(i18n.fruit_label(p, "zh"))
            else:
                d = i18n.disease_label(p, "zh")
                if d and d != p:
                    zh_bits.append(d)
        if zh_bits:
            name_zh = "".join(zh_bits)
        name_en = cand.label_slug.replace("_", " ").title()
        title_zh = f"{fruit_zh}{name_zh}" if fruit_zh not in ("通用", fruit_en) else name_zh
        title_en = f"{fruit_en} {name_en}".strip()
        summary_zh = f"{title_zh}：症状识别、发生规律与防治要点。"
        summary_en = f"{title_en}: symptoms, epidemiology, and management."
        content_zh = (
            f"【症状识别】\n{title_zh}可在叶片、果实或茎部形成病斑、霉层或腐烂；配图对应标注类别「{cand.label_slug}」。\n\n"
            f"【发生规律】\n高温高湿、通风不良、连作易加重；病菌多随风雨与农事传播。\n\n"
            f"【防治要点】\n清园减菌源；改善通风与肥水；选用登记药剂并注意安全间隔期。"
        )
        content_en = (
            f"[Symptoms]\n{title_en} may cause leaf spots, fruit lesions, mold, or rot; images match label `{cand.label_slug}`.\n\n"
            f"[Epidemiology]\nFavored by warm, humid conditions and poor airflow; spreads via rain, wind, and tools.\n\n"
            f"[Management]\nSanitation, cultural practices, resistant varieties when available, and labeled fungicides/pesticides."
        )
    return title_zh, title_en, summary_zh, summary_en, content_zh, content_en


def copy_gallery_images(item_id: str, sources: list[Path]) -> tuple[list[str], str | None]:
    """Copy gallery images; also write cover as {item_id}.jpg for App."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    cover_url: str | None = None

    def _save(src: Path, out: Path) -> bool:
        try:
            from PIL import Image

            img = Image.open(src)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            w, h = img.size
            if min(w, h) > 900:
                r = 900 / min(w, h)
                img = img.resize((int(w * r), int(h * r)), Image.Resampling.LANCZOS)
            img.save(out, "JPEG", quality=90, optimize=True)
            return True
        except Exception:
            return False

    for i, src in enumerate(sources):
        out = IMAGES_DIR / (f"{item_id}.jpg" if i == 0 else f"{item_id}_{i + 1}.jpg")
        if _save(src, out):
            url = f"/knowledge/images/{out.name}"
            urls.append(url)
            if i == 0:
                cover_url = url

    return urls, cover_url


def upsert_knowledge_items(
    batch: list[dict],
) -> None:
    for path, locale_key in ((ITEMS_ZH, "zh"), (ITEMS_EN, "en")):
        payload = load_json(path)
        items: list[dict] = payload.get("items") or []
        by_id = {x["id"]: x for x in items}
        for row in batch:
            loc_row = dict(row)
            if locale_key == "zh":
                loc_row["title"] = row["title_zh"]
                loc_row["summary"] = row["summary_zh"]
                loc_row["content"] = row["content_zh"]
            else:
                loc_row["title"] = row["title_en"]
                loc_row["summary"] = row["summary_en"]
                loc_row["content"] = row["content_en"]
            loc_row.pop("title_zh", None)
            loc_row.pop("title_en", None)
            loc_row.pop("summary_zh", None)
            loc_row.pop("summary_en", None)
            loc_row.pop("content_zh", None)
            loc_row.pop("content_en", None)
            by_id[row["id"]] = loc_row
        payload["items"] = list(by_id.values())
        payload["count"] = len(payload["items"])
        save_json(path, payload)

    import db

    db.init_db()
    db.import_json_file(ITEMS_ZH, locale="zh")
    db.import_json_file(ITEMS_EN, locale="en")


def append_history(type_keys: list[str], meta: dict) -> None:
    history = load_history()
    today = date.today().isoformat()
    days = history.setdefault("days", [])
    days = [d for d in days if d.get("date") != today]
    days.append({"date": today, "type_keys": type_keys, **meta})
    history["days"] = days[-90:]
    history["last_run_at"] = datetime.now(timezone.utc).isoformat()
    if meta.get("bootstrap"):
        history["bootstrap_completed"] = True
    save_json(HISTORY_PATH, history)
