# -*- coding: utf-8 -*-
"""Data layout: disease_pest / control / general are separate search domains."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

DISEASE_PEST_DIR = DATA_DIR / "disease_pest"
CONTROL_DIR = DATA_DIR / "control"
GENERAL_DIR = DATA_DIR / "general"
CATALOG_DIR = DATA_DIR / "catalog"

DB_PATH = DATA_DIR / "knowledge.db"


def items_json(domain: str, locale: str = "zh") -> Path:
    loc = "zh" if locale.startswith("zh") else "en"
    base = {
        "disease_pest": DISEASE_PEST_DIR,
        "control": CONTROL_DIR,
        "general": GENERAL_DIR,
    }[domain]
    return base / loc / "items.json"


def images_dir() -> Path:
    return DISEASE_PEST_DIR / "images"


def ingest_config_path() -> Path:
    return DISEASE_PEST_DIR / "ingest_config.json"


def ingest_history_path() -> Path:
    return DISEASE_PEST_DIR / "ingest_history.json"


def catalog_path() -> Path:
    return CATALOG_DIR / "dataset_catalog.json"


def image_index_path() -> Path:
    return CATALOG_DIR / "local_image_index.json"


def all_item_sources() -> list[tuple[str, Path, str]]:
    """(domain, path, locale) for DB import."""
    out: list[tuple[str, Path, str]] = []
    for domain in ("disease_pest", "control", "general"):
        for locale in ("zh", "en"):
            p = items_json(domain, locale)
            if p.is_file():
                out.append((domain, p, locale))
    return out
