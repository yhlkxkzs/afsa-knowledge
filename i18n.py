# -*- coding: utf-8 -*-
"""Bilingual labels for knowledge filters and content generation."""

from __future__ import annotations

SUPPORTED_LOCALES = ("zh", "en")
DEFAULT_LOCALE = "zh"

FRUIT_LABELS: dict[str, dict[str, str]] = {
    "apple": {"zh": "苹果", "en": "Apple"},
    "pear": {"zh": "梨", "en": "Pear"},
    "peach": {"zh": "桃", "en": "Peach"},
    "grape": {"zh": "葡萄", "en": "Grape"},
    "citrus": {"zh": "柑橘", "en": "Citrus"},
    "mango": {"zh": "芒果", "en": "Mango"},
    "strawberry": {"zh": "草莓", "en": "Strawberry"},
    "watermelon": {"zh": "西瓜", "en": "Watermelon"},
    "tomato": {"zh": "番茄", "en": "Tomato"},
    "cucumber": {"zh": "黄瓜", "en": "Cucumber"},
    "pepper": {"zh": "辣椒", "en": "Pepper"},
    "eggplant": {"zh": "茄子", "en": "Eggplant"},
    "cabbage": {"zh": "白菜", "en": "Cabbage"},
    "spinach": {"zh": "菠菜", "en": "Spinach"},
    "lettuce": {"zh": "生菜", "en": "Lettuce"},
    "potato": {"zh": "马铃薯", "en": "Potato"},
    "rice": {"zh": "水稻", "en": "Rice"},
    "wheat": {"zh": "小麦", "en": "Wheat"},
    "corn": {"zh": "玉米", "en": "Corn"},
    "soybean": {"zh": "大豆", "en": "Soybean"},
    "cotton": {"zh": "棉花", "en": "Cotton"},
    "peanut": {"zh": "花生", "en": "Peanut"},
    "sugarcane": {"zh": "甘蔗", "en": "Sugarcane"},
    "general": {"zh": "通用", "en": "General"},
}

DISEASE_LABELS: dict[str, dict[str, str]] = {
    "anthracnose": {"zh": "炭疽病", "en": "Anthracnose"},
    "scab": {"zh": "黑星病", "en": "Scab"},
    "brown_rot": {"zh": "褐腐病", "en": "Brown Rot"},
    "downy_mildew": {"zh": "霜霉病", "en": "Downy Mildew"},
    "brown_spot": {"zh": "褐斑病", "en": "Brown Spot"},
    "powdery_mildew": {"zh": "白粉病", "en": "Powdery Mildew"},
    "gray_mold": {"zh": "灰霉病", "en": "Gray Mold"},
    "leaf_spot": {"zh": "叶斑病", "en": "Leaf Spot"},
    "rust": {"zh": "锈病", "en": "Rust"},
    "late_blight": {"zh": "晚疫病", "en": "Late Blight"},
    "early_blight": {"zh": "早疫病", "en": "Early Blight"},
    "root_rot": {"zh": "根腐病", "en": "Root Rot"},
    "bacterial_wilt": {"zh": "青枯病", "en": "Bacterial Wilt"},
    "soft_rot": {"zh": "软腐病", "en": "Soft Rot"},
    "virus": {"zh": "病毒病", "en": "Virus Disease"},
    "rice_blast": {"zh": "稻瘟病", "en": "Rice Blast"},
    "fusarium_head_blight": {"zh": "赤霉病", "en": "Fusarium Head Blight"},
    "sheath_blight": {"zh": "纹枯病", "en": "Sheath Blight"},
    "smut": {"zh": "黑穗病", "en": "Smut"},
    "scab_wheat": {"zh": "赤霉病", "en": "Scab"},
    "bacterial_blight": {"zh": "细菌性角斑病", "en": "Bacterial Blight"},
    "leaf_curl": {"zh": "缩叶病", "en": "Leaf Curl"},
    "citrus_scab": {"zh": "疮痂病", "en": "Citrus Scab"},
    "canker": {"zh": "溃疡病", "en": "Canker"},
    "greening": {"zh": "黄龙病", "en": "Greening"},
    "black_rot": {"zh": "黑腐病", "en": "Black Rot"},
    "bacterial_spot": {"zh": "细菌性斑点病", "en": "Bacterial Spot"},
    "leaf_mold": {"zh": "叶霉病", "en": "Leaf Mold"},
    "fusarium_wilt": {"zh": "枯萎病", "en": "Fusarium Wilt"},
    "verticillium_wilt": {"zh": "黄萎病", "en": "Verticillium Wilt"},
    "mosaic": {"zh": "花叶病", "en": "Mosaic Virus"},
    "striped_virus": {"zh": "条纹叶枯病", "en": "Striped Virus"},
    "southern_rust": {"zh": "南方锈病", "en": "Southern Rust"},
    "stalk_rot": {"zh": "茎腐病", "en": "Stalk Rot"},
    "ear_rot": {"zh": "穗腐病", "en": "Ear Rot"},
    "aphid": {"zh": "蚜虫", "en": "Aphid"},
    "mite": {"zh": "红蜘蛛", "en": "Spider Mite"},
    "fruit_borer": {"zh": "食心虫", "en": "Fruit Borer"},
    "scale": {"zh": "介壳虫", "en": "Scale Insect"},
    "thrips": {"zh": "蓟马", "en": "Thrips"},
    "whitefly": {"zh": "粉虱", "en": "Whitefly"},
    "leafhopper": {"zh": "叶蝉", "en": "Leafhopper"},
    "leaf_miner": {"zh": "潜叶蛾", "en": "Leaf Miner"},
    "moth": {"zh": "蛾类", "en": "Moth"},
    "beetle": {"zh": "甲虫", "en": "Beetle"},
    "planthopper": {"zh": "稻飞虱", "en": "Planthopper"},
    "stem_borer": {"zh": "二化螟", "en": "Stem Borer"},
    "corn_borer": {"zh": "玉米螟", "en": "Corn Borer"},
    "cutworm": {"zh": "地老虎", "en": "Cutworm"},
    "pieris": {"zh": "菜青虫", "en": "Cabbage Worm"},
    "diamond_back_moth": {"zh": "小菜蛾", "en": "Diamondback Moth"},
    "fruit_fly": {"zh": "实蝇", "en": "Fruit Fly"},
    "grub": {"zh": "蛴螬", "en": "Grub"},
    "borer": {"zh": "螟虫", "en": "Borer"},
}

CONTROL_LABELS: dict[str, dict[str, str]] = {
    "agricultural": {"zh": "农业防治", "en": "Agricultural Control"},
    "physical": {"zh": "物理防治", "en": "Physical Control"},
    "biological": {"zh": "生物防治", "en": "Biological Control"},
    "chemical": {"zh": "化学防治", "en": "Chemical Control"},
}

CATEGORY_LABELS: dict[str, dict[str, str]] = {
    "disease": {"zh": "病害", "en": "Disease"},
    "pest": {"zh": "虫害", "en": "Pest"},
    "control": {"zh": "防治", "en": "Control"},
    "general": {"zh": "通用", "en": "General"},
}


def normalize_locale(raw: str | None) -> str:
    if not raw:
        return DEFAULT_LOCALE
    code = raw.strip().lower().replace("_", "-").split("-")[0]
    return code if code in SUPPORTED_LOCALES else DEFAULT_LOCALE


def label(table: dict[str, dict[str, str]], key: str | None, locale: str) -> str:
    if not key:
        return ""
    loc = normalize_locale(locale)
    info = table.get(key) or {}
    return info.get(loc) or info.get("en") or key.replace("_", " ").title()


def fruit_label(key: str | None, locale: str) -> str:
    return label(FRUIT_LABELS, key, locale)


def disease_label(key: str | None, locale: str) -> str:
    return label(DISEASE_LABELS, key, locale)


def control_label(key: str | None, locale: str) -> str:
    return label(CONTROL_LABELS, key, locale)
