#!/bin/bash
# 启动知识库 API，默认端口 32230，一页 15 条。
# 用法：./run_api.sh  或  PORT=8000 ./run_api.sh
set -e
cd "$(dirname "$0")"
export PORT="${PORT:-32230}"
export HOST="${HOST:-0.0.0.0}"
echo "知识库 API: http://$HOST:$PORT  (每页 15 条)"
python3 app.py
