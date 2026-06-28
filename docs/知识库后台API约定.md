# 知识库后台 API 约定

App 知识库优先从后台拉取「知识框架」与列表/详情；后台未实现或请求失败时使用本地内置数据。搜索仅限后台知识库，支持**标签筛选**（水果种类、病害种类、防治方法类别）与关键词。

---

## 1. 筛选选项（可选）

用于搜索页的「水果种类」「病害种类」「防治方法类别」下拉/标签。

- **路径**: `GET /knowledge/filters`
- **响应**: JSON 对象

```json
{
  "fruitTypes": [{"id": "apple", "name": "苹果"}, {"id": "pear", "name": "梨"}],
  "diseaseTypes": [{"id": "anthracnose", "name": "炭疽病"}],
  "controlTypes": [{"id": "agricultural", "name": "农业防治"}]
}
```

- 字段名可用下划线形式：`fruit_types`、`disease_types`、`control_types`
- 若接口返回 404 或未实现，App 使用内置默认选项

---

## 2. 知识列表（带标签与关键词）

仅限后台知识库内的条目，支持按分类与标签筛选、关键词搜索。

- **路径**: `GET /knowledge/items`
- **查询参数**（均可选）:

| 参数 | 说明 |
|------|------|
| category_id | 分类：disease / pest / control / general |
| fruit_type | 水果种类（与 filters 中 fruitTypes 的 id 一致） |
| disease_type | 病害种类（与 filters 中 diseaseTypes 的 id 一致） |
| control_type | 防治方法类别（与 filters 中 controlTypes 的 id 一致） |
| keyword | 关键词，匹配标题、摘要等 |
| page | 页码，从 1 开始 |
| limit | 每页条数 |
| **locale** / **lang** | 语言：`zh`（默认）或 `en`；也可通过 `Accept-Language` 头传递 |
| random | 传 `1` 时，在该分类内随机排序后返回前 limit 条（SQL 使用 ORDER BY RANDOM()）；**不传时**为按 id 稳定排序，用于搜索页分页 |
| exclude_ids | 已下发的 id 列表（逗号分隔），本次结果排除这些 id，可与 random 搭配使用 |

**搜索页约定**（只查后台、searchOnly）：不传 `random`。首次请求 `page=1`、`limit=5`；下拉/加载更多时传 `page=当前页+1`、`limit=5`。后台按 `ORDER BY id` 分页，返回本页 5 条及 `has_more`。App 将新 5 条按 id 去重后追加到列表（5 → 10 → 15 → …）。

- **响应**: JSON 数组，每项为知识条目对象，例如：

```json
[
  {
    "id": "disease_apple_anthracnose",
    "category_id": "disease",
    "title": "苹果炭疽病",
    "summary": "果实与叶片常见病害…",
    "content": "【症状识别】\n…",
    "fruit_types": ["苹果"],
    "disease_type": "anthracnose",
    "control_type": "chemical",
    "image_url": "https://upload.wikimedia.org/..."
  }
]
```

- 字段名可用驼峰：`categoryId`、`fruitType`、`diseaseType`、`controlType`、`fruitTypes`
- **image_url**（可选）：该条对应的症状/虫害/防治示意图，多为 Wikimedia Commons 等公开图；无图时无此字段
- 响应根对象包含 **items**（本条列表）、**has_more**（是否还有下一页）、**locale**（本次使用的语言）。搜索页根据 has_more 决定是否展示「加载更多」；下次请求传 `page=当前页+1`、`limit=5` 及相同筛选参数即可。
- 若请求失败或返回空数组，App 使用本地知识库（按分类 + 关键词过滤）

---

## 3. 知识详情

- **路径**: `GET /knowledge/items/:id`
- **响应**: 单个知识条目 JSON 对象，结构同列表项（需包含 `content`）
- 若 404 或失败，App 使用本地 `KnowledgeRepository.getById(id)` 作为回退

---

## 4. App 端行为小结

| 功能 | 行为 |
|------|------|
| 知识库首页（阅读流） | **首屏** `GET /knowledge/feed?limit=10&user_id=…`；**下拉**再请求 `limit=10&exclude_ids=…`；列表展示后 `POST /knowledge/reads` 上报 impression；进详情上报 read；按响应 `personal_repo_sync` 写入个人仓 jsonl |
| 知识库搜索 | 仍用 `GET /knowledge/items`（**不传** feed），`page`+`limit=10` 稳定分页 |
| 知识详情 | 请求 `GET /knowledge/items/:id`；失败则用本地条目 |
| 筛选选项 | 请求 `GET /knowledge/filters`（带 `locale`）；失败则用 App 内置默认选项 |
| App 语言 | 中文 UI → `locale=zh`；English UI → `locale=en`（见 `docs/App语言与知识库选择.md`） |

**首页请求示例（后台需支持）**  
- 打开：`GET /knowledge/items?category_id=disease&page=1&limit=5&random=1`（以及 pest、control、general 各一次，共 4 次）  
- 刷新：同上，将 `limit=3`，共 4 次请求得到 12 条。  
当 `random=1` 时，后台在该分类内随机排序（如 `ORDER BY RANDOM()`）后返回前 limit 条即可。

实现以上接口后，知识库即可完全由后台驱动，并支持「全部 20 张 / 刷新 12 张、子 Tab 只做分类过滤」的首页逻辑。

---

## 5. 阅读流（加权推荐，符合下拉阅读习惯）

知识库 **首页 / 下拉加载** 请用 **`GET /knowledge/feed`**（不要用纯 `random=1`）。

| 场景 | 请求 |
|------|------|
| 首屏 10 条 | `GET /knowledge/feed?limit=10&user_id={github_login}&locale=zh` |
| 下拉再 10 条 | 同上，并传 `exclude_ids=已展示id逗号分隔`；或依赖服务端 `user_id` 累计的 `seen_counts` |
| 带筛选 | 附加 `category_id` / `fruit_type` / `disease_type` / `control_type` / `keyword` |

**降权公式**（出现越多，再次被抽中概率越低）：

```text
weight = 1 / (1 + 0.55 × impression_count + 1.0 × read_count)
```

- **impression**：列表里展示过一次 +1  
- **read**：用户点进详情 +1（降权更强）

可选参数 **`seen_counts`**（JSON 字符串，App 本地缓存与服务端合并，取较大值）：

```json
{"disease_apple_anthracnose_1": {"impression": 2, "read": 1}}
```

响应含 `seen_counts`（合并后），App 下次请求可原样回传或只传 `user_id` 由服务端记忆。

---

## 6. 阅读记录与个人仓同步

**上报曝光/阅读**：`POST /knowledge/reads`

```json
{
  "user_id": "github_login",
  "events": [
    {"item_id": "disease_apple_anthracnose_1", "event": "impression", "category_id": "disease"},
    {"item_id": "disease_apple_anthracnose_1", "event": "read", "category_id": "disease"}
  ]
}
```

响应 **`personal_repo_sync`**：App 用 OAuth 追加写入用户个人仓：

| 字段 | 说明 |
|------|------|
| `path` | `logs/knowledge_reads/2026-06.jsonl` |
| `append_lines` | 每行一条 JSON（含 `data_tier: log`, `retention_days: 90`） |

换机恢复：`POST /knowledge/reads?import=1` + body `{ "user_id", "seen_counts": {...} }`（从个人仓 jsonl 聚合后上传）。

**查询当前统计**：`GET /knowledge/reads?user_id={github_login}`

---

## 7. 病状/虫害对应图片（可选）

- 列表与详情接口可返回 **image_url**，用于卡片或详情页配图。
- 后台通过 `data/knowledge_image_urls.json` 的 **by_title**（标题 → 图片 URL）为条目挂接图片；可自行补充更多标题与 URL（如 Wikimedia Commons、Bugwood 等开放图）。
- 执行 `python3 scripts/attach_knowledge_images.py` 会根据该表写回 `knowledge_items.json` 并更新 DB；加 `--fetch` 时会对未匹配条目尝试用 Commons API 按关键词搜图（较慢）。
- **本地图加速**：执行 `python3 scripts/download_knowledge_images.py` 会将图片下载到 `data/images/` 并缩图（省空间），API 返回的 `image_url` 变为相对路径如 `/knowledge/images/<id>.jpg`，由同一后端提供 `GET /knowledge/images/<filename>`，访问更快。App 端若收到以 `/` 开头的 `image_url`，用 **baseUrl + image_url** 拼接成完整 URL 即可。
