#!/usr/bin/env python3
"""Build knowledge_items_en.json from Chinese knowledge_items.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import i18n

ZH_PATH = PROJECT_ROOT / "data" / "knowledge_items.json"
OUT_PATH = PROJECT_ROOT / "data" / "knowledge_items_en.json"


def _disease_title(item: dict) -> str:
    fruit = i18n.fruit_label(item.get("fruit_type"), "en")
    disease = i18n.disease_label(item.get("disease_type"), "en")
    if fruit and disease:
        return f"{fruit} {disease}"
    if disease:
        return disease
    return item.get("title", "Disease")


def _pest_title(item: dict) -> str:
    fruit = i18n.fruit_label(item.get("fruit_type"), "en")
    pest = i18n.disease_label(item.get("disease_type"), "en")
    if fruit and pest and fruit != "General":
        return f"{fruit} {pest}"
    return pest or item.get("title", "Pest")


def _control_title(item: dict) -> str:
    return i18n.control_label(item.get("control_type"), "en") or item.get("title", "Control")


def _general_title(item: dict) -> str:
    mapping = {
        "general_fertilizer": "Fertilizer Management",
        "general_pruning": "Pruning Management",
        "general_irrigation": "Irrigation Management",
        "general_orchard_core": "Orchard Management Essentials",
        "general_rotation": "Crop Rotation",
        "general_seedling": "Seedling Management",
        "general_greenhouse": "Greenhouse Management",
        "general_soil": "Soil Management",
        "general_variety": "Variety and Resistance",
        "general_safety": "Pesticide Safety",
        "general_weeding": "Weed Control",
        "general_frost": "Frost Protection",
        "general_harvest": "Harvest and Storage",
        "general_green_control": "Integrated Pest Management",
    }
    return mapping.get(item.get("id", ""), item.get("title", "General Topic"))


def _disease_content(item: dict) -> str:
    fruit = i18n.fruit_label(item.get("fruit_type"), "en")
    disease = i18n.disease_label(item.get("disease_type"), "en")
    subject = f"{fruit} {disease}".strip() or "This disease"
    return (
        f"[Symptoms]\n"
        f"{subject} may cause leaf spots, fruit lesions, mold, or rot depending on humidity and crop stage.\n\n"
        f"[Epidemiology]\n"
        f"Pathogens often overwinter in infected plant debris or soil and spread by rain, wind, tools, or insects. "
        f"Warm, humid conditions and poor ventilation increase severity.\n\n"
        f"[Management]\n"
        f"• Sanitation: remove infected leaves, fruit, and branches.\n"
        f"• Cultural: improve spacing and airflow; balanced fertilization; resistant varieties when available.\n"
        f"• Chemical: apply registered protectants before infection and curative products at early onset; rotate modes of action and observe pre-harvest intervals."
    )


def _pest_content(item: dict) -> str:
    pest = i18n.disease_label(item.get("disease_type"), "en") or "This pest"
    return (
        f"[Damage]\n"
        f"{pest} feeds on tender shoots, leaves, or fruit, causing curling, discoloration, honeydew, or direct fruit damage.\n\n"
        f"[Identification]\n"
        f"Inspect new growth and undersides of leaves; confirm with local extension guidance when possible.\n\n"
        f"[Management]\n"
        f"• Monitoring and traps where applicable.\n"
        f"• Conserve natural enemies.\n"
        f"• Use targeted pesticides at susceptible stages; rotate active ingredients."
    )


def _control_content(item: dict) -> str:
    label = i18n.control_label(item.get("control_type"), "en")
    return (
        f"[Overview]\n"
        f"{label} emphasizes prevention, reduced reliance on broad-spectrum chemicals, and practices compatible with local regulations.\n\n"
        f"[Key practices]\n"
        f"Combine orchard sanitation, monitoring, cultural adjustments, and registered products only when thresholds are reached."
    )


def _general_content(item: dict) -> str:
    title = _general_title(item)
    return (
        f"[Overview]\n"
        f"{title} supports stable yield and fruit quality through timely field operations.\n\n"
        f"[Key points]\n"
        f"Follow crop stage, local climate, and label instructions; adjust practices to orchard or field conditions."
    )


def translate_item(item: dict) -> dict:
    cat = item.get("category_id", "general")
    if cat == "disease":
        title = _disease_title(item)
        summary = f"{title}: symptom recognition, epidemiology, and management essentials."
        content = _disease_content(item)
    elif cat == "pest":
        title = _pest_title(item)
        summary = f"{title}: damage symptoms, identification, and control options."
        content = _pest_content(item)
    elif cat == "control":
        title = _control_title(item)
        summary = f"{title}: practical prevention and treatment guidelines."
        content = _control_content(item)
    else:
        title = _general_title(item)
        summary = f"{title}: core recommendations for crop management."
        content = _general_content(item)

    out = dict(item)
    out["title"] = title
    out["summary"] = summary
    out["content"] = content
    if out.get("fruit_type"):
        out["fruit_types"] = [i18n.fruit_label(out["fruit_type"], "en")]
    return out


def main() -> None:
    payload = json.loads(ZH_PATH.read_text(encoding="utf-8"))
    items = payload.get("items") or []
    en_items = [translate_item(x) for x in items]
    out_payload = {
        "source": "Generated from knowledge_items.json (zh) with i18n labels",
        "locale": "en",
        "count": len(en_items),
        "items": en_items,
    }
    OUT_PATH.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH} ({len(en_items)} entries)")


if __name__ == "__main__":
    main()
