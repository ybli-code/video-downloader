#!/bin/bash
# ──────────────────────────────────────────────
# 视频下载技能 - 一键启动脚本
# ──────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "  视频下载技能 - 启动中..."
echo "=================================================="

# 1. 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 python3，请先安装 Python >= 3.9"
    exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[1/4] Python $PY_VERSION"

# 2. 检查并安装依赖
echo "[2/4] 检查 Python 依赖..."
pip3 install -q -r requirements.txt --break-system-packages 2>/dev/null || \
pip3 install -q -r requirements.txt 2>/dev/null || true

# 3. 检查 ffmpeg
echo "[3/4] 检查 ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "  [警告] 未找到 ffmpeg，正在安装..."
    apt-get update -qq && apt-get install -y -qq ffmpeg 2>/dev/null || \
    echo "  [警告] ffmpeg 安装失败，去水印功能将不可用"
fi
if command -v ffmpeg &> /dev/null; then
    echo "  ffmpeg: $(ffmpeg -version | head -1)"
else
    echo "  [警告] ffmpeg 不可用，去水印功能将不可用"
fi

# 4. 启动服务
echo "[4/4] 启动 Web 服务..."
echo ""
echo "=================================================="
echo "  访问地址: http://localhost:5000"
echo "  命令行:   python cli.py <视频链接>"
echo "=================================================="
echo ""

python3 app.py
