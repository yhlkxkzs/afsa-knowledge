# 知识库后台

按 `docs/` 下说明与接口规范实现的作物知识库 API：筛选选项、列表/搜索（**一页 15 条**）、详情。

## 1. 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/knowledge/filters` | 筛选选项（水果种类、病害种类、防治方法类别） |
| GET | `/knowledge/items` | 列表/搜索，分页，默认 **每页 15 条**，不含 content |
| GET | `/knowledge/items/:id` | 单条详情，含 content |

列表支持查询参数：`category_id`、`fruit_type`、`disease_type`、`control_type`、`keyword`、`page`、`limit`（默认 15）。

## 2. 存储

- SQLite：`data/knowledge.db`，单表 `knowledge`（id, category_id, title, summary, content, fruit_type, disease_type, control_type）。
- 检索：LIKE + 条件 + LIMIT/OFFSET，符合文档「最简单存储与检索」约定。

## 3. 数据来源与入库

- 知识内容按 `docs/知识库内容纲要和说明.md` 的病害/虫害/防治/通用条目整理，并结合公开植保与栽培资料写成正文。
- 入库：运行种子脚本，将 17 条作物知识写入数据库（已存在则覆盖）。

```bash
pip install -r requirements.txt
python3 scripts/seed_knowledge.py
```

## 4. 启动 API

```bash
./run_api.sh
# 或指定端口
PORT=8000 ./run_api.sh
```

默认监听 `0.0.0.0:32230`。App 请求 `GET /knowledge/items?…&page=1&limit=15` 即可拿到符合条件的一页 15 条。
