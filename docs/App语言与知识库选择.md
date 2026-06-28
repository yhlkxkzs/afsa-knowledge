# App 语言与知识库选择

App 界面语言（中文 / English）决定请求知识库 API 时使用 **`locale=zh`** 还是 **`locale=en`**。

## 1. 识别结果（水果 / 病害）

推理结果 `predictions.json` 同时包含：

| 字段 | 说明 |
|------|------|
| `predicted_class_zh` | 中文展示名 |
| `predicted_class_en` | 英文展示名 |
| `predicted_class` | 默认中文（兼容旧版） |

App 按当前 UI 语言选择展示字段：

```dart
String displayClass(Map row, Locale locale) {
  return locale.languageCode == 'en'
      ? (row['predicted_class_en'] ?? row['predicted_class'])
      : (row['predicted_class_zh'] ?? row['predicted_class']);
}
```

映射表：

- 水果：`fruit_classification/.github/scripts/species_display_map.json`（275 类，en/zh）
- 病害：`disease_classification/.github/scripts/disease_display_map.json`（212 类，en/zh）

维护：

```bash
# 水果：更新英文译名后重建
python3 tasks/fruit_classification/scripts/generate_species_en_full.py
python3 tasks/fruit_classification/scripts/build_species_display_map.py

# 病害：更新 overrides 后重建
python3 tasks/disease_classification/scripts/build_disease_display_map.py
```

## 2. 知识库 API

所有 `/knowledge/*` 接口支持 **`locale`**（或 `lang` / `language`）查询参数，也支持 **`Accept-Language`** 头。

| App UI | API 参数 | 数据文件 |
|--------|----------|----------|
| 中文 | `locale=zh`（默认） | `data/knowledge_items.json` |
| English | `locale=en` | `data/knowledge_items_en.json` |

示例：

```http
GET /knowledge/items?category_id=disease&limit=5&random=1&locale=en
GET /knowledge/filters?locale=en
GET /knowledge/items/disease_apple_anthracnose_1?locale=en
```

响应中会带 `"locale": "en"`；筛选器 `fruitTypes[].name` 等也会返回对应语言。

## 3. App 端推荐实现

```dart
import 'package:flutter/material.dart';

String knowledgeLocale(BuildContext context) {
  final code = Localizations.localeOf(context).languageCode;
  return code == 'en' ? 'en' : 'zh';
}

Future<Map<String, dynamic>> fetchKnowledgeItems(
  String baseUrl,
  BuildContext context, {
  required String categoryId,
  int limit = 5,
  bool random = true,
}) async {
  final loc = knowledgeLocale(context);
  final uri = Uri.parse('$baseUrl/knowledge/items').replace(queryParameters: {
    'category_id': categoryId,
    'limit': '$limit',
    if (random) 'random': '1',
    'locale': loc,
  });
  // GET uri ...
}
```

**规则**：App 切换系统/应用语言后，知识库列表、详情、筛选下拉均使用同一 `locale`，与识别结果展示字段保持一致。

## 4. 后台维护双语内容

```bash
cd /home/yuhanlin/APP/konwledgeset

# 从中文条目生成英文版 JSON
python3 scripts/build_knowledge_en.py

# 写入 SQLite（zh + en）
python3 scripts/sync_knowledge_locales.py
```

英文条目目前由结构化模板 + `i18n.py` 标签生成；后续可在 `knowledge_items_en.json` 中人工润色，`sync_knowledge_locales.py` 会覆盖写入 DB。
