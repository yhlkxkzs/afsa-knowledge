# -*- coding: utf-8 -*-
"""
从知识库纲要与公开资料整理作物知识，写入 SQLite。
可多次运行：已存在 id 则跳过（或改为 REPLACE 以覆盖）。
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import db

# 知识条目：id, category_id, title, summary, content, fruit_type, disease_type, control_type
KNOWLEDGE_ENTRIES = [
    # ---------- 病害 ----------
    {
        "id": "disease_apple_anthracnose",
        "category_id": "disease",
        "title": "苹果炭疽病",
        "summary": "果实与叶片病斑，褐色下陷、同心轮纹，绯红色黏液；清园+保护剂预防+治疗剂。",
        "content": """【症状识别】
• 果实：初期针头大淡褐色小斑，扩大后褐色或深褐色，下陷，表面同心轮纹状黑色小点，高湿时溢出绯红色黏液；果肉褐腐有苦味，严重时全果腐烂或成黑色僵果。
• 枝条：衰弱或受伤的 1～2 年生枝上不规则溃疡斑，后期表皮龟裂、木质部外露，枝条干枯。

【发生规律】
病菌以菌丝体在病僵果、枯枝、果台等处越冬；春季产生分生孢子，经雨水、风、昆虫传播。6 月初开始发病，7—8 月盛发；高温高湿加重为害。

【防治要点】
• 清园：冬春彻底清除病枯枝、病果、僵果，集中烧毁。
• 栽培：修剪改善通风，增施有机肥，合理负载；果实套袋。
• 药剂：落花后 10 天起每 10～15 天喷一次至 8 月中下旬。可选 80% 炭疽福美 500～800 倍、75% 百菌清 600 倍、70% 代森锰锌 400～600 倍等；多雨年增加次数。""",
        "fruit_type": "apple",
        "disease_type": "anthracnose",
        "control_type": "chemical",
    },
    {
        "id": "disease_pear_scab",
        "category_id": "disease",
        "title": "梨黑星病",
        "summary": "叶、果黑色霉层，叶早落、果凹陷龟裂；清园+氟硅唑/戊唑醇等。",
        "content": """【症状识别】
叶片、叶柄、果实、新梢均可受害。叶背沿叶脉出现淡黄色病斑，后生黑色霉层，严重时叶早落。果实受害出现淡黄斑，后生黑霉，病部凹陷、龟裂，幼果易畸形。

【发生规律】
病菌在芽鳞、病梢、落叶上越冬；春季借风雨传播。多雨高湿、通风不良果园发病重。

【防治要点】
• 清园：清除落叶、病梢，减少越冬菌源。
• 药剂：萌芽前喷铲除剂；生长期用氟硅唑、戊唑醇、苯醚甲环唑等交替防治，重点保护幼果和嫩叶。""",
        "fruit_type": "pear",
        "disease_type": "scab",
        "control_type": "chemical",
    },
    {
        "id": "disease_peach_brown_rot",
        "category_id": "disease",
        "title": "桃褐腐病",
        "summary": "果实褐腐、灰褐色霉层；清园+苯醚甲环唑/腐霉利+套袋。",
        "content": """【症状识别】
主要为害果实。病斑褐色、扩大后整果褐腐，表面生灰褐色绒状霉层（分生孢子座），病果常脱落或僵挂枝头。花、枝也可受害。

【发生规律】
病菌在僵果、病枝上越冬；花期遇雨易侵染，果实近成熟期多雨高湿发病重。

【防治要点】
• 清园：摘除僵果、病果，剪除病枝。
• 套袋：果实套袋减轻侵染。
• 药剂：花期前后及果实期选用苯醚甲环唑、腐霉利、异菌脲等喷雾防治。""",
        "fruit_type": "peach",
        "disease_type": "brown_rot",
        "control_type": "chemical",
    },
    {
        "id": "disease_grape_downy_mildew",
        "category_id": "disease",
        "title": "葡萄霜霉病",
        "summary": "叶背白色霜状霉、叶面黄褐斑；烯酰吗啉/霜脲·锰锌等。",
        "content": """【症状识别】
主要为害叶片。叶正面出现黄绿色或黄褐色不规则病斑，叶背对应处生白色霜状霉层；严重时叶枯早落。嫩梢、果梗、幼果也可受害。

【发生规律】
病菌在病组织或土壤中越冬；借风雨传播。多雨、露重、通风差时流行。

【防治要点】
• 栽培：改善架面通风，控制氮肥，及时绑蔓。
• 药剂：发病前或发病初期选用烯酰吗啉、霜脲·锰锌、嘧菌酯等喷雾，叶背打匀。""",
        "fruit_type": "grape",
        "disease_type": "downy_mildew",
        "control_type": "chemical",
    },
    {
        "id": "disease_apple_brown_spot",
        "category_id": "disease",
        "title": "苹果褐斑病与叶部病害",
        "summary": "褐斑、枯斑、早期落叶；代森锰锌、多抗霉素等。",
        "content": """【症状识别】
褐斑病在叶上产生同心轮纹型、针芒型或混合型褐斑，后期叶变黄脱落。其他叶部病害可致枯斑、焦边、早期落叶，削弱树势。

【发生规律】
病菌在落叶上越冬；春雨后产生孢子侵染。多雨、树冠郁闭、地势低洼处发病重。

【防治要点】
• 清园：彻底清扫落叶，减少初侵染源。
• 药剂：落花后开始保护，可选用代森锰锌、多抗霉素、戊唑醇等，间隔 10～15 天，多雨年适当加密。""",
        "fruit_type": "apple",
        "disease_type": "brown_spot",
        "control_type": "chemical",
    },
    # ---------- 虫害 ----------
    {
        "id": "pest_aphid",
        "category_id": "pest",
        "title": "蚜虫",
        "summary": "嫩梢叶背刺吸、卷叶煤烟；黄板+吡虫啉/啶虫脒等。",
        "content": """【为害特点】
刺吸式口器，群集嫩梢、叶背、顶芽吸汁，致叶片卷曲、皱缩，分泌蜜露诱发煤烟病，传播病毒病。一年多代，繁殖快。

【识别要点】
体小，绿色、黄绿色或黑色，多无翅或具翅型；嫩梢与叶背常见密集若虫、成蚜。

【防治要点】
• 物理：黄板诱杀有翅蚜。
• 生物：保护瓢虫、草蛉等天敌。
• 化学：嫩梢期选用吡虫啉、啶虫脒、氟啶虫酰胺等，轮换用药，重点喷嫩梢与叶背。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": "chemical",
    },
    {
        "id": "pest_mite",
        "category_id": "pest",
        "title": "红蜘蛛（叶螨）",
        "summary": "叶背吸食、失绿枯焦；捕食螨+阿维菌素/乙唑螨腈/矿物油等轮换。",
        "content": """【为害特点】
体长不足 0.5 mm，在叶背刺吸汁液；受害叶出现灰白小点，逐渐失绿、枯焦、脱落，影响光合与产量。一年十多至二十多代，高温干旱易暴发。

【识别要点】
叶背可见细小活动红点或黄绿色点，放大可见螨体；严重时叶面可见丝网。

【防治要点】
• 生物：释放捕食螨，保护天敌。
• 化学：春梢期、高温前选用阿维菌素、乙唑螨腈、螺螨酯、矿物油等轮换使用，重点喷叶背；避开高温时段。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": "chemical",
    },
    {
        "id": "pest_fruit_borer",
        "category_id": "pest",
        "title": "食心虫",
        "summary": "蛀果“豆沙馅”；糖醋液+套袋+氯虫苯甲酰胺等适期用药。",
        "content": """【为害特点】
幼虫蛀入果实取食，果面有蛀孔、堆有虫粪，果内形成“豆沙馅”状隧道，丧失商品价值。不同果树有桃小、梨小、苹小等种类。

【识别要点】
成虫为小型蛾类；被害果表面有入果孔，孔周有粪屑，切开可见幼虫或褐色隧道。

【防治要点】
• 物理：糖醋液、性诱剂诱杀成虫；果实套袋。
• 化学：在成虫羽化产卵及孵化初期选用氯虫苯甲酰胺、甲维盐等适期用药，覆盖果面。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": "chemical",
    },
    {
        "id": "pest_scale",
        "category_id": "pest",
        "title": "介壳虫",
        "summary": "枝干叶片固着吸食、煤烟病；若虫期噻嗪酮/螺虫乙酯等。",
        "content": """【为害特点】
若虫、成虫固着在枝干、叶片上刺吸，分泌蜜露诱发煤烟病，削弱树势，影响果实品质。种类多，如康氏粉蚧、梨圆蚧等。

【识别要点】
体表常覆蜡质或介壳，紧贴枝、叶；受害处有黏腻蜜露或黑色煤污。

【防治要点】
• 农业：剪除严重被害枝，改善通风。
• 化学：若虫孵化扩散期（介壳未固定前）用药效果好，可选用噻嗪酮、螺虫乙酯、毒死蜱等，喷透枝干与叶背。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": "chemical",
    },
    # ---------- 防治方案 ----------
    {
        "id": "control_agricultural",
        "category_id": "control",
        "title": "农业防治",
        "summary": "清园、修剪、肥水、负载、土壤管理。",
        "content": """【要点】
• 清园：清除枯枝、落叶、落果、杂草，减少病虫越冬基数。
• 修剪：合理整形修剪，改善通风透光，减少病害与部分害虫孳生。
• 肥水：平衡施肥，增施有机肥，合理灌溉，增强树势，提高抗性。
• 负载：合理留果，避免超载导致树势下降。
• 土壤：深翻、覆草、生草等改善土壤结构，有利根系与抗逆。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": "agricultural",
    },
    {
        "id": "control_physical",
        "category_id": "control",
        "title": "物理防治",
        "summary": "套袋、黄板、糖醋液、诱虫带、刮树皮。",
        "content": """【要点】
• 套袋：果实套袋减轻病害与食心虫等为害，改善外观。
• 黄板：悬挂黄色粘虫板诱杀蚜虫、粉虱等趋黄害虫。
• 糖醋液：糖、醋、酒、水配成诱液诱杀蛾类、金龟子等。
• 诱虫带：树干绑诱虫带诱集下树害虫，集中处理。
• 刮树皮：冬季刮除老翘皮，减少越冬害虫与病菌。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": "physical",
    },
    {
        "id": "control_biological",
        "category_id": "control",
        "title": "生物防治",
        "summary": "天敌保护与释放（捕食螨、瓢虫、赤眼蜂等）、生物农药。",
        "content": """【要点】
• 天敌保护：减少广谱农药使用，保留天敌；果园生草、种植蜜源植物有利于天敌栖息。
• 天敌释放：按需释放捕食螨防治叶螨，瓢虫、草蛉控蚜，赤眼蜂防治鳞翅目等。
• 生物农药：使用苏云金杆菌、白僵菌、多角体病毒等生物制剂，以及植物源、矿物源药剂，降低抗性与残留。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": "biological",
    },
    {
        "id": "control_chemical",
        "category_id": "control",
        "title": "化学防治要点",
        "summary": "对症选药、适期、轮换、安全间隔；常见药剂举例。",
        "content": """【要点】
• 对症选药：根据病虫种类选用登记药剂，看清防治对象与用量。
• 适期用药：在病虫发生关键期（如卵孵盛期、发病初期）用药，提高防效。
• 轮换用药：不同作用机制药剂轮换，延缓抗药性。
• 安全间隔：采收前严格按标签安全间隔期停用，保证残留达标。
• 常见药剂举例：杀菌如代森锰锌、戊唑醇、烯酰吗啉；杀虫如吡虫啉、阿维菌素、氯虫苯甲酰胺等；按说明使用。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": "chemical",
    },
    # ---------- 通用 ----------
    {
        "id": "general_fertilizer",
        "category_id": "general",
        "title": "施肥管理",
        "summary": "秋施基肥（9—10 月）、追肥与叶面肥、水肥结合。",
        "content": """【要点】
• 秋施基肥：以有机肥为主，9—10 月施用，有利于根系吸收与树体贮藏养分，为翌年萌芽、开花、坐果打基础。
• 追肥：根据物候与树势，在萌芽前后、花后、果实膨大期等关键期适量追施氮、磷、钾及中微量元素。
• 叶面肥：在需肥关键期或根系吸收受限时，可配合叶面喷施尿素、磷酸二氢钾、钙肥等。
• 水肥结合：施肥后适当灌水，提高利用率；避免肥害。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": None,
    },
    {
        "id": "general_pruning",
        "category_id": "general",
        "title": "修剪管理",
        "summary": "冬剪与夏剪、拉枝开角、两调一控。",
        "content": """【要点】
• 冬剪：落叶后至萌芽前进行，疏除病虫枝、过密枝，短截、回缩调节枝量与结果部位，培养树形。
• 夏剪：生长期通过抹芽、摘心、疏梢、拉枝等控制旺长，改善光照，促进成花与果实品质。
• 拉枝开角：对直立枝拉枝开张角度，缓和长势，促进成花。
• 两调一控：调枝量、调结构，控制树冠大小与通风透光，维持稳定产量与树势。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": None,
    },
    {
        "id": "general_irrigation",
        "category_id": "general",
        "title": "灌溉管理",
        "summary": "该浇则浇、该控则控，膨大期细水勤灌、封冻水。",
        "content": """【要点】
• 该浇则浇：萌芽前后、果实膨大期、采后等关键需水期及时补水，避免干旱落果或影响品质。
• 该控则控：花芽分化期适当控水有利于成花；成熟前适度控水有利于着色与糖度。
• 膨大期：果实膨大期可细水勤灌，保持土壤适度湿润，减少裂果与日灼。
• 封冻水：入冬前灌一次透水，有利于树体抗寒与翌春萌芽。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": None,
    },
    {
        "id": "general_orchard_core",
        "category_id": "general",
        "title": "果园管理核心要点",
        "summary": "「当年叶片下年肥」「无光不结果」「叶靠根长、根靠叶养」；保护叶片、合理负载。",
        "content": """【要点】
• “当年叶片下年肥”：当年叶片制造养分供当年果实与翌年萌芽、开花，故保护叶片、延长功能期是连年丰产的基础。
• “无光不结果”：充足光照是花芽分化与果实着色的前提，通过修剪、密度控制保证树冠透光。
• “叶靠根长、根靠叶养”：根系吸收水分养分供叶片生长，叶片光合产物供根系生长，二者协调才能树势稳健。
• 保护叶片：防治早期落叶病与害虫，避免过早落叶。
• 合理负载：根据树势与品种适量留果，避免大小年与树势早衰。""",
        "fruit_type": None,
        "disease_type": None,
        "control_type": None,
    },
]


def seed():
    db.init_db()
    n = db.upsert_items(KNOWLEDGE_ENTRIES, locale="zh")
    print(f"已写入 {n} 条知识条目 (locale=zh)。")


if __name__ == "__main__":
    seed()
