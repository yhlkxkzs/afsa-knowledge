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

import paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = paths.DATA_DIR
CONFIG_PATH = paths.ingest_config_path()
HISTORY_PATH = paths.ingest_history_path()
CATALOG_PATH = paths.catalog_path()
IMAGES_DIR = paths.images_dir()
ITEMS_ZH = paths.items_json("disease_pest", "zh")
ITEMS_EN = paths.items_json("disease_pest", "en")

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
    """Match pest words on tokens. ``pestalotiopsis`` contains the letters pest but is a fungus."""
    tokens = [t for t in normalize_slug(slug).split("_") if t]
    fungus = {"pestalotiopsis", "pestalotiopsi"}
    for token in tokens:
        if token in fungus:
            continue
        if any(hint in token for hint in PEST_HINTS):
            return True
    return False


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


INDEX_CACHE = paths.image_index_path()


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


# Tokens that are folder noise, not a disease name. Dropped before translation.
_NOISE_TOKENS = {
    "leaf", "leaves", "image", "images", "img", "disease", "diseases",
    "fruit", "fruits", "damage", "damaged", "symptom", "symptoms",
    "the", "of", "and", "with", "on", "in", "s", "a",
}
# Dataset typos and aliases folded onto a phrase key.
_SLUG_ALIASES = {
    "altenaria": "alternaria",
    "alcium": "calcium",
    "anthrax": "anthracnose",
    "pestalotiopsi": "pestalotiopsis",
    "blackspot": "black_spot",
    "thrip": "thrips",
    "mites": "mite",
}
_NUTRIENT_ZH = {
    "potassium": "钾",
    "calcium": "钙",
    "nitrogen": "氮",
    "magnesium": "镁",
    "iron": "铁",
    "zinc": "锌",
    "boron": "硼",
}
# Longer keys are tried first. Overrides i18n where the quiz name differs.
_PHRASE_ZH_EXTRA = {
    "yellow_sigatoka": "黄条叶斑病",
    "diplodia_rot": "焦腐病",
    "algal_leaf_spot": "藻斑病",
    "sooty_mold": "煤污病",
    "leaf_blight": "叶枯病",
    "flea_beetle": "跳甲",
    "pestalotiopsis": "拟盘多毛孢叶斑病",
    "black_spot": "黑斑病",
    "alternaria": "链格孢病",
    "earworm": "棉铃虫",
    "insect_pest": "害虫",
    "spider_mite": "叶螨",
    "mite": "叶螨",
    "thrips": "蓟马",
    "anthracnose": "炭疽病",
    "powdery_mildew": "白粉病",
    "downy_mildew": "霜霉病",
    "gray_mold": "灰霉病",
    "brown_spot": "褐斑病",
    "leaf_spot": "叶斑病",
    "black_rot": "黑腐病",
    "bacterial_wilt": "青枯病",
    "brown_rot": "褐腐病",
    "root_rot": "根腐病",
    "soft_rot": "软腐病",
    "fruit_rot": "果腐病",
    "rot": "腐烂病",
    "scab": "黑星病",
    "rust": "锈病",
    "canker": "溃疡病",
    "greening": "黄龙病",
    "aphid": "蚜虫",
    "beetle": "甲虫",
}


def _phrase_zh_table() -> dict[str, str]:
    import i18n

    table = {key: names["zh"] for key, names in i18n.DISEASE_LABELS.items() if names.get("zh")}
    table.update(_PHRASE_ZH_EXTRA)
    return table


def _fruit_zh(fruit_type: str) -> str:
    import i18n

    fruit = normalize_slug(fruit_type)
    zh = i18n.fruit_label(fruit, "zh")
    if not zh or zh in {"通用", "General"} or re.search(r"[A-Za-z]", zh):
        return ""
    return zh


def compose_zh_title(fruit_type: str, label_slug: str) -> tuple[str, str]:
    """Chinese card title and kind: disease, pest, deficiency, or unusable.

    New cards stay out of the quiz until a person checks the cover. This only
    stops English filenames and nutrient labels from being stored as disease names.
    """
    fruit_zh = _fruit_zh(fruit_type)
    raw_tokens = [t for t in normalize_slug(label_slug).split("_") if t]
    aliased: list[str] = []
    for token in raw_tokens:
        aliased.extend(_SLUG_ALIASES.get(token, token).split("_"))
    for token in aliased:
        if token in _NUTRIENT_ZH:
            name = f"{fruit_zh}缺{_NUTRIENT_ZH[token]}" if fruit_zh else f"缺{_NUTRIENT_ZH[token]}"
            return name, "deficiency"

    fruit_tokens = {normalize_slug(fruit_type)}
    if normalize_slug(fruit_type) in {"lychee", "litchi"}:
        fruit_tokens.update({"lychee", "litchi"})
    # Keep words like "leaf" until phrase matching, so algal_leaf_spot stays intact.
    tokens = [t for t in aliased if t not in fruit_tokens]
    table = _phrase_zh_table()
    bits: list[str] = []
    i = 0
    while i < len(tokens):
        found_n = 0
        found_zh = ""
        for n in range(len(tokens) - i, 0, -1):
            key = "_".join(tokens[i:i + n])
            if key in table:
                found_n = n
                found_zh = table[key]
                break
        if found_n:
            if found_zh:
                bits.append(found_zh)
            i += found_n
        elif tokens[i] in _NOISE_TOKENS:
            i += 1
        else:
            i += 1
    if not bits:
        return "", "unusable"
    title = f"{fruit_zh}{''.join(bits)}" if fruit_zh else "".join(bits)
    if fruit_zh and title.startswith(fruit_zh + fruit_zh):
        title = title[len(fruit_zh):]
    kind = "pest" if is_pest_label(label_slug) else "disease"
    return title, kind


def compose_en_title(fruit_type: str, label_slug: str) -> str:
    import i18n

    fruit = i18n.fruit_label(fruit_type, "en")
    if fruit in {"General", ""}:
        fruit = ""
    tokens = []
    for token in normalize_slug(label_slug).split("_"):
        token = _SLUG_ALIASES.get(token, token)
        if token in _NOISE_TOKENS or token == normalize_slug(fruit_type):
            continue
        if token in _NUTRIENT_ZH:
            return f"{fruit} {token} deficiency".strip()
        tokens.append(token.replace("_", " "))
    name = " ".join(tokens).strip()
    return f"{fruit} {name}".strip()


def _color_fractions(path: Path) -> dict[str, float]:
    import numpy as np
    from PIL import Image

    img = Image.open(path).convert("RGB")
    img.thumbnail((160, 160))
    arr = np.asarray(img, dtype=np.int16)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    total = float(arr.shape[0] * arr.shape[1]) or 1.0
    dark = (r < 70) & (g < 70) & (b < 70)
    yellow = (r > 150) & (g > 140) & (b < 110)
    orange = (r > 160) & (g > 70) & (g < 170) & (b < 90) & (r > g + 20)
    brown = (r > 90) & (r < 190) & (g > 40) & (g < 140) & (b < 100) & (r > g) & (g >= b)
    pale = (r > 170) & (g > 170) & (b > 160) & (np.abs(r - g) < 25)
    green = (g > r + 12) & (g > b + 8) & (g > 60)
    return {
        "dark": float(dark.sum()) / total,
        "yellow": float(yellow.sum()) / total,
        "orange": float(orange.sum()) / total,
        "brown": float(brown.sum()) / total,
        "pale": float(pale.sum()) / total,
        "green": float(green.sum()) / total,
    }


def symptom_score(path: Path) -> float:
    """Higher when the frame has spots, scorch, or mold rather than a plain green leaf."""
    try:
        f = _color_fractions(path)
    except Exception:
        return 0.0
    return f["dark"] * 3.0 + f["brown"] * 2.0 + f["orange"] * 2.2 + f["yellow"] * 1.4 + f["pale"] * 1.6


_CAPTIONS = {
    "dark": ("叶面或果面有深色病斑。", "Dark spots on the leaf or fruit."),
    "orange": ("叶面有橙黄色斑点。", "Orange-yellow spots on the leaf."),
    "yellow": ("叶片有黄化或黄色条斑。", "Yellowing or yellow streaks on the leaf."),
    "brown": ("叶缘或叶面有褐色枯斑。", "Brown scorch on the leaf edge or blade."),
    "pale": ("表面有浅色霉层或粉状物。", "Pale mold or powder on the surface."),
    "green": ("叶片大体青绿，病斑不明显。", "Leaf looks mostly green, with no clear lesion."),
    "unclear": ("病斑不够清楚。", "The lesion is not clear."),
}


def visible_caption(path: Path) -> tuple[str, str]:
    """One sentence about the cover. New cards stay quiz_priority=skip until a person checks it."""
    try:
        f = _color_fractions(path)
    except Exception:
        return _CAPTIONS["unclear"]
    # Only name a lesion when the color is specific. Shadow and white backgrounds stay "不清楚".
    if f["green"] > 0.42 and (f["dark"] + f["brown"] + f["orange"]) < 0.12:
        return _CAPTIONS["green"]
    if f["pale"] > 0.35 and f["brown"] < 0.08 and f["orange"] < 0.05:
        return _CAPTIONS["unclear"]
    if f["orange"] >= 0.08 and f["orange"] >= f["brown"]:
        return _CAPTIONS["orange"]
    if f["brown"] >= 0.12:
        return _CAPTIONS["brown"]
    if f["yellow"] >= 0.15 and f["green"] > 0.12:
        return _CAPTIONS["yellow"]
    if f["dark"] > 0.12 and f["brown"] > 0.05:
        return _CAPTIONS["dark"]
    if f["pale"] >= 0.1 and f["green"] < 0.35 and f["brown"] >= 0.06:
        return _CAPTIONS["pale"]
    return _CAPTIONS["unclear"]


def crop_foot(img: Any) -> Any:
    """Cut off a foot or hand along the bottom edge. Leave fruit and leaf colors alone."""
    import numpy as np

    arr = np.asarray(img.convert("RGB"), dtype=np.int16)
    height, width = arr.shape[:2]
    if height < 80:
        return img
    band = arr[int(height * 0.80):]
    r, g, b = band[:, :, 0], band[:, :, 1], band[:, :, 2]
    skin = (r > 145) & (g > 100) & (b > 70) & (r > g) & (r > b) & ((r - g) < 55) & (g > b)
    if float(skin.mean()) < 0.04:
        return img
    return img.crop((0, 0, width, int(height * 0.82)))


def choose_cover(gallery_urls: list[str]) -> tuple[str | None, str, str]:
    """Pick the gallery frame with the clearest spots and describe it."""
    best_url = gallery_urls[0] if gallery_urls else None
    best_score = -1.0
    for url in gallery_urls:
        name = url.rsplit("/", 1)[-1]
        path = IMAGES_DIR / name
        if not path.is_file():
            continue
        score = symptom_score(path)
        if score > best_score:
            best_score = score
            best_url = url
    if not best_url:
        return None, _CAPTIONS["unclear"][0], _CAPTIONS["unclear"][1]
    path = IMAGES_DIR / best_url.rsplit("/", 1)[-1]
    summary_zh, summary_en = visible_caption(path)
    return best_url, summary_zh, summary_en


def build_bilingual_content(cand: TypeCandidate) -> tuple[str, str, str, str, str, str, str]:
    """Return title_zh, title_en, summary_zh, summary_en, content_zh, content_en, kind.

    summary/content are replaced after the cover image is chosen. kind is
    disease, pest, deficiency, or unusable.
    """
    title_zh, kind = compose_zh_title(cand.fruit_type, cand.label_slug)
    title_en = compose_en_title(cand.fruit_type, cand.label_slug)
    if kind == "unusable":
        return "", title_en, "", "", "", "", kind
    summary_zh, summary_en = _CAPTIONS["unclear"]
    if kind == "deficiency":
        summary_zh = "这是缺素症状，不按病害考核。"
        summary_en = "Nutrient deficiency, not quizzed as a disease."
    content_zh = summary_zh
    content_en = summary_en
    return title_zh, title_en, summary_zh, summary_en, content_zh, content_en, kind


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
            else:
                img = img.convert("RGB")
            img = crop_foot(img)
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
            old = by_id.get(row["id"])
            # A card already gated for the quiz keeps its checked title, cover, and priority.
            if old and old.get("quiz_priority") in {"skip", "normal", "hard"}:
                continue
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
            loc_row.setdefault("quiz_priority", "skip")
            by_id[row["id"]] = loc_row
        payload["items"] = list(by_id.values())
        payload["count"] = len(payload["items"])
        save_json(path, payload)

    import db

    db.init_db()
    db.import_json_file(ITEMS_ZH, locale="zh")
    db.import_json_file(ITEMS_EN, locale="en")
    db.rebuild_all_from_data()


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
