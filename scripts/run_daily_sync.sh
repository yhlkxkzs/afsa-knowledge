#!/usr/bin/env bash
# 每日定时执行：更新知识库 data/（knowledge_items.json + knowledge.db）
# 由 cron 在每天早上 7 点调用，例如：0 7 * * * /path/to/konwledgeset/scripts/run_daily_sync.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/data"
LOG_FILE="$DATA_DIR/sync.log"

cd "$PROJECT_ROOT"
mkdir -p "$DATA_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始更新知识库 data/（200+ 条作物知识）..." >> "$LOG_FILE"
if python3 "$PROJECT_ROOT/scripts/expand_knowledge_200.py" >> "$LOG_FILE" 2>&1; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 更新完成" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 更新失败，退出码 $?" >> "$LOG_FILE"
  exit 1
fi
