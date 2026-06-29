# 知识库后台

按 `docs/` 下说明与接口规范实现的作物知识库 API：筛选选项、列表/搜索（**一页 15 条**）、详情。

## 1. 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/knowledge/feed` | 病虫害阅读流（仅有图，加权推荐） |
| GET | `/knowledge/filters` | 筛选；可加 `domain=disease_pest\|control\|general` |
| GET | `/knowledge/items` | 列表/搜索（防控、基础知识）；分页 |
| GET | `/knowledge/items/:id` | 单条详情，含 content |

- **病虫害**：`GET /knowledge/feed`（下拉刷新）
- **防控 / 基础知识**：`GET /knowledge/items?category_id=control` 或 `general`

## 2. 存储

见 [`data/README.md`](data/README.md)：

| 域 | 路径 | 规则 |
|----|------|------|
| 病虫害 | `data/disease_pest/` | 必须有图；ingest 增量 |
| 农业防控 | `data/control/` | 纯文本 |
| 基础知识 | `data/general/` | 纯文本 |

运行时统一索引：`data/knowledge.db`

## 3. 数据来源与入库

```bash
pip install -r requirements.txt
python3 scripts/sync_knowledge_locales.py
python3 scripts/daily_ingest.py              # 病虫害 bi-daily 增量
```

## 4. 启动 API

```bash
./run_api.sh
# 或指定端口
PORT=8000 ./run_api.sh
```

默认监听 `0.0.0.0:32230`。App 请求 `GET /knowledge/items?…&page=1&limit=15` 即可拿到符合条件的一页 15 条。
