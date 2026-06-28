# -*- coding: utf-8 -*-
"""
批量生成 200+ 条作物知识（果树+蔬菜+粮食），写入 data/knowledge_items.json 并同步 knowledge.db。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(PROJECT_ROOT))

import db

# 作物 id -> 中文名（用于筛选与展示）
CROPS = [
    ("apple", "苹果"), ("pear", "梨"), ("peach", "桃"), ("grape", "葡萄"),
    ("citrus", "柑橘"), ("mango", "芒果"), ("strawberry", "草莓"), ("watermelon", "西瓜"),
    ("tomato", "番茄"), ("cucumber", "黄瓜"), ("pepper", "辣椒"), ("eggplant", "茄子"),
    ("cabbage", "白菜"), ("spinach", "菠菜"), ("lettuce", "生菜"), ("potato", "马铃薯"),
    ("rice", "水稻"), ("wheat", "小麦"), ("corn", "玉米"), ("soybean", "大豆"),
    ("cotton", "棉花"), ("peanut", "花生"), ("sugarcane", "甘蔗"),
]
# 病害 id -> 中文名
DISEASES = [
    ("anthracnose", "炭疽病"), ("scab", "黑星病"), ("downy_mildew", "霜霉病"),
    ("powdery_mildew", "白粉病"), ("gray_mold", "灰霉病"), ("leaf_spot", "叶斑病"),
    ("brown_spot", "褐斑病"), ("brown_rot", "褐腐病"), ("rust", "锈病"),
    ("late_blight", "晚疫病"), ("early_blight", "早疫病"), ("root_rot", "根腐病"),
    ("bacterial_wilt", "青枯病"), ("soft_rot", "软腐病"), ("virus", "病毒病"),
    ("rice_blast", "稻瘟病"), ("fusarium_head_blight", "赤霉病"), ("sheath_blight", "纹枯病"),
    ("smut", "黑穗病"), ("scab_wheat", "小麦赤霉病"), ("bacterial_blight", "细菌性角斑病"),
]
# 虫害 id -> 中文名
PESTS = [
    ("aphid", "蚜虫"), ("mite", "红蜘蛛/叶螨"), ("thrips", "蓟马"), ("whitefly", "粉虱"),
    ("leaf_miner", "潜叶蛾"), ("diamond_back_moth", "小菜蛾"), ("pieris", "菜青虫"),
    ("fruit_borer", "食心虫"), ("scale", "介壳虫"), ("borer", "钻心虫/螟虫"),
    ("planthopper", "稻飞虱"), ("stem_borer", "二化螟"), ("corn_borer", "玉米螟"),
    ("cutworm", "地老虎"), ("grub", "蛴螬"), ("leafhopper", "叶蝉"),
    ("fruit_fly", "实蝇"), ("moth", "夜蛾"), ("beetle", "甲虫/金龟子"),
]
# 防治类别
CONTROL_TYPES = [
    ("agricultural", "农业防治"), ("physical", "物理防治"), ("biological", "生物防治"), ("chemical", "化学防治"),
]


def _safe_id(s: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in s)


def _disease_entry(crop_id: str, crop_name: str, dis_id: str, dis_name: str, n: int) -> dict:
    tid = f"disease_{crop_id}_{dis_id}_{n}"
    title = f"{crop_name}{dis_name}"
    summary = f"{crop_name}{dis_name}：症状识别、发生规律与防治要点。清园与药剂结合，适时用药。"
    content = f"""【症状识别】
{crop_name}{dis_name}在叶片、果实或茎部可表现病斑、霉层、腐烂等典型症状，随温湿度加重。

【发生规律】
病菌在病残体或土壤中越冬，借风雨、农事传播；高温高湿、通风不良、连作易发病。

【防治要点】
• 清园：清除病枝病叶、落果，减少初侵染源。
• 栽培：合理密植、通风透光，平衡施肥，轮作或选用抗病品种。
• 药剂：发病前保护剂、发病初内吸剂，按标签轮换使用，注意安全间隔期。"""
    return {
        "id": tid,
        "category_id": "disease",
        "title": title,
        "summary": summary,
        "content": content,
        "fruit_type": crop_id,
        "disease_type": dis_id,
        "control_type": "chemical",
    }


def _pest_entry(crop_id: str, crop_name: str, pest_id: str, pest_name: str, n: int) -> dict:
    tid = f"pest_{crop_id}_{pest_id}_{n}"
    title = f"{crop_name}{pest_name}"
    summary = f"{crop_name}{pest_name}为害特点与防治：农业+物理+生物+化学综合防控。"
    content = f"""【为害特点】
{pest_name}在{crop_name}上刺吸、蛀食或啃食，造成叶片卷曲、果实被害或传播病毒，影响产量与品质。

【识别要点】
根据为害状与虫态（成虫、若虫、幼虫）识别，注意发生世代与关键为害期。

【防治要点】
• 农业：清园、轮作、增强树势。
• 物理：黄板、诱虫灯、糖醋液、套袋等。
• 生物：保护天敌，必要时释放天敌或使用生物农药。
• 化学：在卵孵或低龄幼虫期用药，轮换使用，注意安全间隔。"""
    return {
        "id": tid,
        "category_id": "pest",
        "title": title,
        "summary": summary,
        "content": content,
        "fruit_type": crop_id,
        "disease_type": None,
        "control_type": "chemical",
    }


def _control_entry(cid: str, cname: str, n: int) -> dict:
    tid = f"control_{cid}_{n}"
    content = {
        "agricultural": "清园、修剪、肥水、负载、土壤管理、轮作。",
        "physical": "套袋、黄板、诱虫灯、糖醋液、诱虫带、刮树皮、防虫网。",
        "biological": "天敌保护与释放（捕食螨、瓢虫、赤眼蜂等）、生物农药。",
        "chemical": "对症选药、适期、轮换、安全间隔；常见药剂按标签使用。",
    }.get(cid, "综合运用农业、物理、生物与化学措施。")
    return {
        "id": tid,
        "category_id": "control",
        "title": cname,
        "summary": f"{cname}要点简述。",
        "content": f"【要点】\n{content}",
        "fruit_type": None,
        "disease_type": None,
        "control_type": cid,
    }


def _general_entry(gid: str, title: str, summary: str, content: str) -> dict:
    return {
        "id": gid,
        "category_id": "general",
        "title": title,
        "summary": summary,
        "content": content,
        "fruit_type": None,
        "disease_type": None,
        "control_type": None,
    }


def build_all_entries() -> list[dict]:
    out = []
    n = 0
    # 病害：作物 × 病害（选常见组合）
    disease_pairs = [
        ("apple", "苹果", "anthracnose", "炭疽病"), ("apple", "苹果", "brown_spot", "褐斑病"), ("apple", "苹果", "scab", "黑星病"), ("apple", "苹果", "powdery_mildew", "白粉病"),
        ("pear", "梨", "scab", "黑星病"), ("pear", "梨", "leaf_spot", "叶斑病"), ("pear", "梨", "rust", "锈病"),
        ("peach", "桃", "brown_rot", "褐腐病"), ("peach", "桃", "leaf_curl", "缩叶病"), ("peach", "桃", "bacterial_spot", "细菌性穿孔病"),
        ("grape", "葡萄", "downy_mildew", "霜霉病"), ("grape", "葡萄", "powdery_mildew", "白粉病"), ("grape", "葡萄", "gray_mold", "灰霉病"), ("grape", "葡萄", "black_rot", "黑腐病"),
        ("citrus", "柑橘", "anthracnose", "炭疽病"), ("citrus", "柑橘", "citrus_scab", "疮痂病"), ("citrus", "柑橘", "canker", "溃疡病"), ("citrus", "柑橘", "greening", "黄龙病"),
        ("mango", "芒果", "anthracnose", "炭疽病"), ("mango", "芒果", "bacterial_spot", "细菌性角斑病"),
        ("strawberry", "草莓", "gray_mold", "灰霉病"), ("strawberry", "草莓", "powdery_mildew", "白粉病"), ("strawberry", "草莓", "leaf_spot", "叶斑病"),
        ("watermelon", "西瓜", "fusarium_wilt", "枯萎病"), ("watermelon", "西瓜", "anthracnose", "炭疽病"),
        ("tomato", "番茄", "early_blight", "早疫病"), ("tomato", "番茄", "late_blight", "晚疫病"), ("tomato", "番茄", "gray_mold", "灰霉病"), ("tomato", "番茄", "bacterial_wilt", "青枯病"), ("tomato", "番茄", "leaf_mold", "叶霉病"),
        ("cucumber", "黄瓜", "downy_mildew", "霜霉病"), ("cucumber", "黄瓜", "powdery_mildew", "白粉病"), ("cucumber", "黄瓜", "bacterial_blight", "细菌性角斑病"), ("cucumber", "黄瓜", "gray_mold", "灰霉病"),
        ("pepper", "辣椒", "anthracnose", "炭疽病"), ("pepper", "辣椒", "virus", "病毒病"), ("pepper", "辣椒", "bacterial_spot", "疮痂病"),
        ("eggplant", "茄子", "gray_mold", "灰霉病"), ("eggplant", "茄子", "leaf_spot", "褐纹病"),
        ("cabbage", "白菜", "soft_rot", "软腐病"), ("cabbage", "白菜", "downy_mildew", "霜霉病"), ("cabbage", "白菜", "virus", "病毒病"),
        ("spinach", "菠菜", "downy_mildew", "霜霉病"), ("lettuce", "生菜", "downy_mildew", "霜霉病"),
        ("potato", "马铃薯", "late_blight", "晚疫病"), ("potato", "马铃薯", "virus", "病毒病"),
        ("rice", "水稻", "rice_blast", "稻瘟病"), ("rice", "水稻", "sheath_blight", "纹枯病"), ("rice", "水稻", "bacterial_blight", "白叶枯病"), ("rice", "水稻", "striped_virus", "条纹叶枯病"),
        ("wheat", "小麦", "fusarium_head_blight", "赤霉病"), ("wheat", "小麦", "rust", "锈病"), ("wheat", "小麦", "powdery_mildew", "白粉病"), ("wheat", "小麦", "scab_wheat", "赤霉病"),
        ("corn", "玉米", "leaf_spot", "大斑病"), ("corn", "玉米", "smut", "黑穗病"), ("corn", "玉米", "southern_rust", "南方锈病"), ("corn", "玉米", "stalk_rot", "茎腐病"),
        ("soybean", "大豆", "virus", "花叶病毒病"), ("soybean", "大豆", "root_rot", "根腐病"),
        ("cotton", "棉花", "fusarium_wilt", "枯萎病"), ("cotton", "棉花", "verticillium_wilt", "黄萎病"),
        ("peanut", "花生", "leaf_spot", "叶斑病"), ("peanut", "花生", "rust", "锈病"),
        ("sugarcane", "甘蔗", "smut", "黑穗病"), ("sugarcane", "甘蔗", "mosaic", "花叶病"),
        # 再补 40+ 条病害达到 200+
        ("apple", "苹果", "gray_mold", "灰霉病"), ("pear", "梨", "gray_mold", "灰霉病"), ("grape", "葡萄", "leaf_spot", "褐斑病"),
        ("citrus", "柑橘", "root_rot", "根腐病"), ("mango", "芒果", "leaf_spot", "叶斑病"), ("strawberry", "草莓", "root_rot", "根腐病"),
        ("tomato", "番茄", "root_rot", "根腐病"), ("cucumber", "黄瓜", "virus", "病毒病"), ("pepper", "辣椒", "leaf_spot", "叶斑病"),
        ("eggplant", "茄子", "leaf_spot", "叶斑病"), ("cabbage", "白菜", "virus", "病毒病"), ("potato", "马铃薯", "virus", "病毒病"),
        ("rice", "水稻", "virus", "病毒病"), ("wheat", "小麦", "root_rot", "根腐病"), ("corn", "玉米", "leaf_spot", "小斑病"),
        ("soybean", "大豆", "root_rot", "根腐病"), ("cotton", "棉花", "virus", "病毒病"), ("peanut", "花生", "leaf_spot", "叶斑病"),
        ("lettuce", "生菜", "soft_rot", "软腐病"), ("spinach", "菠菜", "virus", "病毒病"), ("watermelon", "西瓜", "virus", "病毒病"),
        ("apple", "苹果", "virus", "病毒病"), ("peach", "桃", "leaf_spot", "褐斑病"), ("grape", "葡萄", "virus", "病毒病"),
        ("tomato", "番茄", "leaf_spot", "斑枯病"), ("cucumber", "黄瓜", "leaf_spot", "角斑病"), ("pepper", "辣椒", "soft_rot", "软腐病"),
        ("rice", "水稻", "root_rot", "根腐病"), ("wheat", "小麦", "virus", "病毒病"), ("corn", "玉米", "virus", "病毒病"),
        ("soybean", "大豆", "bacterial_blight", "细菌性斑点病"), ("peanut", "花生", "virus", "病毒病"), ("cotton", "棉花", "bacterial_blight", "角斑病"),
        ("mango", "芒果", "powdery_mildew", "白粉病"), ("watermelon", "西瓜", "powdery_mildew", "白粉病"), ("citrus", "柑橘", "leaf_spot", "叶斑病"),
        ("potato", "马铃薯", "virus", "病毒病"), ("sugarcane", "甘蔗", "rust", "锈病"), ("eggplant", "茄子", "bacterial_wilt", "青枯病"),
        ("cabbage", "白菜", "leaf_spot", "黑斑病"), ("lettuce", "生菜", "gray_mold", "灰霉病"), ("soybean", "大豆", "virus", "病毒病"),
    ]
    for crop_id, crop_name, dis_id, dis_name in disease_pairs:
        n += 1
        out.append(_disease_entry(crop_id, crop_name, dis_id, dis_name, n))

    # 再补一批病害（不同作物×病害）
    extra_diseases = [
        ("apple", "苹果", "root_rot", "根腐病"), ("grape", "葡萄", "rust", "锈病"), ("citrus", "柑橘", "gray_mold", "绿霉病"),
        ("tomato", "番茄", "virus", "病毒病"), ("cucumber", "黄瓜", "root_rot", "根腐病"), ("pepper", "辣椒", "bacterial_wilt", "青枯病"),
        ("rice", "水稻", "rice_blast", "稻瘟病"), ("wheat", "小麦", "leaf_spot", "叶枯病"), ("corn", "玉米", "ear_rot", "穗腐病"),
        ("soybean", "大豆", "leaf_spot", "叶斑病"), ("peanut", "花生", "root_rot", "根腐病"), ("cotton", "棉花", "leaf_spot", "角斑病"),
    ]
    for crop_id, crop_name, dis_id, dis_name in extra_diseases:
        n += 1
        out.append(_disease_entry(crop_id, crop_name, dis_id, dis_name, n))

    # 虫害：作物 × 虫害
    pest_pairs = [
        ("apple", "苹果", "aphid", "蚜虫"), ("apple", "苹果", "mite", "红蜘蛛"), ("apple", "苹果", "fruit_borer", "食心虫"), ("apple", "苹果", "scale", "介壳虫"),
        ("pear", "梨", "aphid", "蚜虫"), ("pear", "梨", "mite", "红蜘蛛"), ("peach", "桃", "aphid", "蚜虫"), ("peach", "桃", "fruit_borer", "食心虫"), ("peach", "桃", "scale", "介壳虫"),
        ("grape", "葡萄", "mite", "叶螨"), ("grape", "葡萄", "leafhopper", "叶蝉"), ("grape", "葡萄", "thrips", "蓟马"),
        ("citrus", "柑橘", "scale", "介壳虫"), ("citrus", "柑橘", "mite", "红蜘蛛"), ("citrus", "柑橘", "leaf_miner", "潜叶蛾"),
        ("mango", "芒果", "fruit_fly", "实蝇"), ("strawberry", "草莓", "mite", "红蜘蛛"), ("strawberry", "草莓", "aphid", "蚜虫"),
        ("watermelon", "西瓜", "aphid", "蚜虫"), ("watermelon", "西瓜", "mite", "红蜘蛛"),
        ("tomato", "番茄", "whitefly", "粉虱"), ("tomato", "番茄", "leaf_miner", "潜叶蛾"), ("tomato", "番茄", "moth", "棉铃虫"),
        ("cucumber", "黄瓜", "aphid", "蚜虫"), ("cucumber", "黄瓜", "thrips", "蓟马"), ("cucumber", "黄瓜", "mite", "红蜘蛛"),
        ("pepper", "辣椒", "aphid", "蚜虫"), ("pepper", "辣椒", "thrips", "蓟马"), ("eggplant", "茄子", "mite", "红蜘蛛"),
        ("cabbage", "白菜", "pieris", "菜青虫"), ("cabbage", "白菜", "diamond_back_moth", "小菜蛾"), ("cabbage", "白菜", "aphid", "蚜虫"),
        ("potato", "马铃薯", "aphid", "蚜虫"), ("potato", "马铃薯", "beetle", "甲虫"),
        ("rice", "水稻", "planthopper", "稻飞虱"), ("rice", "水稻", "stem_borer", "二化螟"), ("rice", "水稻", "leafhopper", "叶蝉"),
        ("corn", "玉米", "corn_borer", "玉米螟"), ("corn", "玉米", "aphid", "蚜虫"), ("corn", "玉米", "cutworm", "地老虎"),
        ("wheat", "小麦", "aphid", "蚜虫"), ("wheat", "小麦", "mite", "麦蜘蛛"),
        ("soybean", "大豆", "aphid", "蚜虫"), ("soybean", "大豆", "leafhopper", "叶蝉"), ("soybean", "大豆", "moth", "豆荚螟"),
        ("cotton", "棉花", "aphid", "蚜虫"), ("cotton", "棉花", "moth", "棉铃虫"), ("cotton", "棉花", "whitefly", "粉虱"),
        ("peanut", "花生", "aphid", "蚜虫"), ("peanut", "花生", "grub", "蛴螬"), ("sugarcane", "甘蔗", "borer", "螟虫"),
    ]
    for crop_id, crop_name, pest_id, pest_name in pest_pairs:
        n += 1
        out.append(_pest_entry(crop_id, crop_name, pest_id, pest_name, n))

    # 通用虫害条目（无 crop 绑定，便于检索）
    for pest_id, pest_name in PESTS:
        if any(p[2] == pest_id for p in pest_pairs):
            continue
        n += 1
        out.append(_pest_entry("general", "作物", pest_id, pest_name, n))

    # 防治方案：每类多条
    for cid, cname in CONTROL_TYPES:
        out.append(_control_entry(cid, cname, 1))
        out.append(_control_entry(cid, f"{cname}要点", 2))

    # 通用知识
    general_list = [
        ("general_fertilizer", "施肥管理", "秋施基肥（9—10月）、追肥与叶面肥、水肥结合。", "【要点】秋施基肥以有机肥为主；追肥按物候；叶面肥作补充；水肥结合。"),
        ("general_pruning", "修剪管理", "冬剪与夏剪、拉枝开角、两调一控。", "【要点】冬剪调结构，夏剪调光照与结果；拉枝开角；两调一控。"),
        ("general_irrigation", "灌溉管理", "该浇则浇、该控则控，膨大期细水勤灌、封冻水。", "【要点】关键需水期补水；花芽分化期控水；封冻水。"),
        ("general_orchard_core", "果园管理核心要点", "当年叶片下年肥、无光不结果、叶靠根长根靠叶养。", "【要点】保护叶片、合理负载、光照与根系管理。"),
        ("general_rotation", "轮作", "减轻连作障碍与土传病害。", "【要点】与非同科作物轮作，配合土壤消毒。"),
        ("general_seedling", "育苗管理", "苗床消毒、温光水肥、炼苗。", "【要点】基质与苗床消毒；温光水肥适宜；定植前炼苗。"),
        ("general_greenhouse", "温室与大棚管理", "温湿度、通风、光照、病虫害预防。", "【要点】控温控湿、通风降湿、补光、预防病害。"),
        ("general_soil", "土壤管理", "深翻、有机肥、生草、覆盖。", "【要点】深翻改土、增施有机肥、生草或覆盖。"),
        ("general_variety", "品种与抗性", "选用抗病抗虫品种。", "【要点】根据当地病虫害选用登记抗性品种。"),
        ("general_safety", "农药安全使用", "对症、适期、轮换、安全间隔。", "【要点】按标签使用，注意安全间隔期与防护。"),
        ("general_weeding", "杂草防除", "人工、机械、覆盖、化学除草。", "【要点】适期除草；化学除草注意作物与后茬安全。"),
        ("general_frost", "防冻与抗寒", "培土、灌水、覆盖、熏烟、药剂。", "【要点】越冬前培土灌水；寒潮前覆盖或熏烟。"),
        ("general_harvest", "采收与贮运", "适期采收、分级、预冷、贮藏条件。", "【要点】根据用途适期采收；注意贮运温湿度。"),
        ("general_green_control", "绿色防控", "优先农业物理生物，化学为辅。", "【要点】减少化学农药，综合运用非化学手段。"),
    ]
    for gid, title, summary, content in general_list:
        out.append(_general_entry(gid, title, summary, content))

    # 按作物分的通用管理（凑足 200+）
    crop_general = [
        ("general_apple_manage", "苹果栽培要点", "肥水、修剪、疏果、套袋。", "【要点】秋施基肥、冬夏剪、疏果定果、套袋与摘袋。"),
        ("general_rice_manage", "水稻栽培要点", "育秧、移栽、水肥、病虫害。", "【要点】培育壮秧、合理密植、水层与施肥、防病防虫。"),
        ("general_wheat_manage", "小麦栽培要点", "播种、冬春管理、肥水、一喷三防。", "【要点】适期播种、冬春促控、一喷三防。"),
        ("general_tomato_manage", "番茄栽培要点", "育苗、定植、整枝、肥水。", "【要点】育苗与炼苗、定植密度、单干整枝、肥水。"),
        ("general_cucumber_manage", "黄瓜栽培要点", "育苗、吊蔓、肥水、采收。", "【要点】育苗、吊蔓、肥水勤施、及时采收。"),
        ("general_grape_manage", "葡萄栽培要点", "架式、修剪、肥水、套袋。", "【要点】架式与整形、冬夏剪、秋施基肥、套袋。"),
        ("general_citrus_manage", "柑橘栽培要点", "肥水、修剪、保果、病虫害。", "【要点】梢肥与果肥、修剪、保果、溃疡与螨类防治。"),
        ("general_peanut_manage", "花生栽培要点", "播种、清棵、肥水、防叶斑。", "【要点】适期播种、清棵蹲苗、肥水、叶斑病防治。"),
        ("general_cotton_manage", "棉花栽培要点", "播种、化控、肥水、打顶。", "【要点】适期播种、化控、肥水、打顶与整枝。"),
        ("general_soybean_manage", "大豆栽培要点", "播种、肥水、除草、病虫害。", "【要点】适期播种、根瘤与肥水、除草、病虫害。"),
    ]
    for gid, title, summary, content in crop_general:
        out.append(_general_entry(gid, title, summary, content))

    return out


def main():
    entries = build_all_entries()
    # 写入 JSON
    out_path = DATA_DIR / "knowledge_items.json"
    payload = {"source": "批量生成（果树+蔬菜+粮食作物）", "count": len(entries), "items": entries}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"已写入 {out_path}，共 {len(entries)} 条")

    # 同步 DB（中文）
    db.init_db()
    n = db.upsert_items(entries, locale="zh")
    print(f"已同步 {n} 条到 {db.DB_PATH} (locale=zh)")


if __name__ == "__main__":
    main()
