# 知识库数据目录

三类内容分域存储，检索逻辑不同：

```text
data/
  disease_pest/          # 病虫害：必须有图；ingest 流水线；/knowledge/feed 加权阅读流
    zh/items.json
    en/items.json
    images/
    ingest_config.json
    ingest_history.json
  control/               # 农业防控：纯文本；/knowledge/items?category_id=control
    zh/items.json
    en/items.json
  general/               # 基础知识：纯文本；/knowledge/items?category_id=general
    zh/items.json
    en/items.json
  catalog/               # 数据集登记（ingest 用）
    dataset_catalog.json
    local_image_index.json
  knowledge.db           # API 运行时统一索引（由 sync_knowledge_locales 重建）
```

## API

| 场景 | 接口 |
|------|------|
| 病虫害阅读流 | `GET /knowledge/feed`（仅有图条目） |
| 防控 / 基础知识列表 | `GET /knowledge/items?category_id=control\|general` |
| 筛选 | `GET /knowledge/filters?domain=disease_pest\|control\|general` |
| 图片 | `GET /knowledge/images/{filename}` → `disease_pest/images/` |

## 维护

```bash
python3 scripts/migrate_data_layout.py      # 从旧版单文件迁移（已执行可跳过）
python3 scripts/sync_knowledge_locales.py   # 重建 knowledge.db
python3 scripts/daily_ingest.py --bootstrap # 病虫害增量（仅写 disease_pest/）
```
