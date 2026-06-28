# 统一 API 网关（同一端口）

知识库与水果识别模型 API 可在**同一端口**同时提供，一次启动全部可用。

## 启动方式

在 **APP 项目根目录** 执行：

```bash
./run_unified_api.sh
```

或直接：

```bash
python3 run_unified_api.py --port 32222 --weights <path/to/best.pt>
```

- **默认端口**：32222（与 App 直连一致）  
- **默认权重**：`AFSA/task1_fruit_classification/train_detection/runs/mobilenet_v3/weights/best.pt`  
- 可选：`PORT=32222 WEIGHTS=path/to/best.pt ./run_unified_api.sh`

**三模型同时推理（结果对比）**：手机上传一张图后，三个模型都识别，返回是否一致及各自置信度。

```bash
MULTI=1 ./run_unified_api.sh
# 或
python3 run_unified_api.py --multi --port 32222
```

- 会加载 `runs/mobilenet_v3`、`runs/efficientnet_lite0`、`runs/shufflenet_v2` 下的 `weights/best.pt`（与 MobileNet 同目录结构），**仍使用同一端口 32222**。

## 同一端口下的路径

| 路径 | 说明 |
|------|------|
| `GET /knowledge/filters` | 知识库筛选选项 |
| `GET /knowledge/items` | 知识列表（支持 category_id、keyword、page、limit、random 等） |
| `GET /knowledge/items/<id>` | 知识详情 |
| `POST /predict` | 水果识别（上传图片） |
| `GET /health` | 健康检查（识别服务） |
| `POST /annotation/upload` | 标注上传 |
| `GET /upload_log`、`GET /upload_log/export` | 上传记录 |
| `POST /recognition_signal` | 识别信号上报 |

前端/App 只需配置一个 **baseUrl**（如 `http://host:32222`），即可同时访问知识库与识别接口。

## 与单独启动的对比

- **单独启动**：知识库 `konwledgeset/run_api.sh`（32230），识别 `run_api_mobilenet.sh`（32222）等，各占一个端口。  
- **统一网关**：一个进程、一个端口（默认 32222，与 App 直连一致），同时提供上述所有接口。

## 三模型识别时 POST /predict 返回格式

- **一致时**：`consistent: true`，`class` 为统一结果，`confidence` 为三模型平均置信度，`model_results` 为各模型详情（含置信度、top_k）。
- **不一致时**：`consistent: false`，`class` 为多数票结果，`model_results` 中给出每个模型的 `model`、`class`、`confidence`、`top_k`，手机端可展示「模型 A：苹果 0.9；模型 B：苹果 0.85；模型 C：梨 0.6」等。
