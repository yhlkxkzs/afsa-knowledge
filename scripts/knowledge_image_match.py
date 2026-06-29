#!/usr/bin/env python3
"""Strict fruit + label matching for knowledge base image assignment."""

from __future__ import annotations

import re
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

PEST_HINTS = (
    "aphid", "mite", "borer", "thrip", "whitefly", "beetle", "moth", "fly",
    "hopper", "miner", "worm", "grub", "scale", "pest", "insect", "caterpillar",
)


def normalize_slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def tokenize(s: str) -> set[str]:
    return {t for t in re.split(r"[_\s\-./]+", (s or "").lower()) if len(t) > 2}


def is_healthy_label(slug: str) -> bool:
    s = slug.lower()
    return s in {"healthy", "health"} or s.endswith("_healthy") or s.startswith("healthy_")


def item_label_slug(item: dict) -> str | None:
    """Disease/pest slug from disease_type or item id (e.g. pest_apple_aphid_121 -> aphid)."""
    if item.get("disease_type"):
        return normalize_slug(str(item["disease_type"]))
    item_id = (item.get("id") or "").lower()
    fruit = (item.get("fruit_type") or "").lower()
    parts = item_id.split("_")
    if len(parts) < 4 or not parts[-1].isdigit():
        return None
    if parts[0] not in {"disease", "pest"}:
        return None
    if fruit and parts[1] != fruit:
        return None
    label_parts = parts[2:-1]
    return "_".join(label_parts) if label_parts else None


def dataset_fruit_tokens(ds: dict) -> set[str]:
    tokens: set[str] = set()
    for f in ds.get("fruits") or []:
        tokens.add(normalize_slug(str(f)))
    tokens |= tokenize(ds.get("dataset_id", ""))
    tokens |= tokenize(str(ds.get("path", "")))
    return {t for t in tokens if t and t != "general"}


def dataset_matches_fruit(fruit: str, ds: dict) -> bool:
    fruit = normalize_slug(fruit)
    if not fruit or fruit == "general":
        return True
    ds_fruits = {normalize_slug(str(f)) for f in (ds.get("fruits") or [])}
    if fruit in ds_fruits:
        return True
    ds_tokens = dataset_fruit_tokens(ds)
    return fruit in ds_tokens


def class_belongs_to_fruit(fruit: str, class_name: str, ds: dict) -> bool:
    """For multi-crop datasets, class folder must name the target crop."""
    fruit = normalize_slug(fruit)
    if not fruit:
        return True
    ds_fruits = {normalize_slug(str(f)) for f in (ds.get("fruits") or []) if f}
    if len(ds_fruits) == 1 and fruit in ds_fruits:
        return True
    class_slug = normalize_slug(class_name)
    if class_slug.startswith(f"{fruit}_"):
        return True
    if fruit in tokenize(class_slug):
        return True
    return False


GENERIC_LABEL_TOKENS = {
    "leaf", "spot", "rot", "mold", "rust", "virus", "blight", "disease", "wilt", "healthy", "normal",
}


def class_matches_label(label_slug: str, class_name: str, fruit: str = "") -> bool:
    label_slug = normalize_slug(label_slug)
    class_slug = normalize_slug(class_name)
    if not label_slug or not class_slug or is_healthy_label(class_slug):
        return False
    if label_slug == class_slug:
        return True

    label_tokens = tokenize(label_slug)
    class_tokens = tokenize(class_slug)
    distinctive = label_tokens - GENERIC_LABEL_TOKENS

    if not distinctive:
        if fruit:
            fruit = normalize_slug(fruit)
            expected = f"{fruit}_{label_slug}"
            if class_slug == expected or class_slug.endswith(f"_{label_slug}"):
                return True
        return class_slug == label_slug or class_slug.endswith(f"_{label_slug}")

    if distinctive <= class_tokens:
        return True

    compact_label = label_slug.replace("_", "")
    compact_class = class_slug.replace("_", "")
    if compact_label and (compact_label in compact_class or compact_class.endswith(compact_label)):
        return True

    if fruit:
        fruit = normalize_slug(fruit)
        prefixed = f"{fruit}_{label_slug}"
        if class_slug == prefixed or class_slug.startswith(prefixed + "_"):
            return True
        if f"{fruit}{compact_label}" in compact_class:
            return True

    return False


def matching_classes(item: dict, ds: dict) -> list[str]:
    """Dataset classes that match this knowledge item (fruit + label)."""
    fruit = (item.get("fruit_type") or "").lower()
    label = item_label_slug(item)
    if not label:
        return []
    if fruit and not dataset_matches_fruit(fruit, ds):
        return []
    matched: list[str] = []
    for cls in ds.get("classes") or []:
        if not class_belongs_to_fruit(fruit, str(cls), ds):
            continue
        if class_matches_label(label, str(cls), fruit):
            matched.append(normalize_slug(str(cls)))
    return matched


GENERIC_PATH_TOKENS = {
    "disease", "recognition", "database", "datasets", "images", "image",
    "train", "test", "valid", "data", "normal", "healthy", "leaf", "leaves",
    "jpg", "jpeg", "png", "webp", "bmp", "coco", "folder", "main",
}


def _path_scope(path: Path, dataset_root: Path | None = None) -> str:
    if dataset_root and dataset_root.is_dir():
        try:
            return str(path.relative_to(dataset_root))
        except ValueError:
            pass
    return f"{path.parent.name}/{path.name}"


def path_matches_label(path: Path, label_slug: str, dataset_root: Path | None = None) -> bool:
    label_slug = normalize_slug(label_slug)
    if not label_slug:
        return False
    scope = _path_scope(path, dataset_root)
    label_tokens = tokenize(label_slug)
    path_tokens = tokenize(scope)
    overlap = label_tokens & path_tokens
    meaningful = overlap - GENERIC_PATH_TOKENS
    if meaningful:
        return True
    compact_label = label_slug.replace("_", "")
    compact_scope = re.sub(r"[^a-z0-9]+", "", scope.lower())
    if compact_label and compact_label in compact_scope:
        return True
    return label_slug.lower() in scope.lower()


def path_matches_classes(path: Path, class_slugs: list[str], dataset_root: Path | None = None) -> bool:
    return any(path_matches_label(path, slug, dataset_root) for slug in class_slugs)


def iter_candidate_images(
    ds: dict,
    class_slugs: list[str],
    index: dict[str, list[str]],
    *,
    max_scan: int = 300,
):
    """Yield image paths whose folders match the given class slugs."""
    if not class_slugs:
        return
    did = ds.get("dataset_id") or ""
    seen: set[str] = set()

    root = Path(ds.get("path") or "")

    def _yield(path: Path) -> bool:
        key = str(path.resolve())
        if key in seen or not path.is_file():
            return False
        if path.suffix.lower() not in IMAGE_EXTS:
            return False
        if not path_matches_classes(path, class_slugs, root if root.is_dir() else None):
            return False
        seen.add(key)
        return True

    for img_str in index.get(did, []):
        p = Path(img_str)
        if _yield(p):
            yield p

    if not root.is_dir():
        return
    scanned = 0
    for p in root.rglob("*"):
        if p.suffix.lower() not in IMAGE_EXTS or not p.is_file():
            continue
        if not _yield(p):
            continue
        yield p
        scanned += 1
        if scanned >= max_scan:
            break
