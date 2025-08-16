#!/bin/bash

# 启动脚本 - 使用虚拟环境
# 自动检查并创建必要的配置

set -e

# 项目根目录
PROJECT_ROOT="/home/root/telegram-bot/colana"

echo "🚀 启动代币分析Bot..."

# 检查虚拟环境
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "📦 创建虚拟环境..."
    cd "$PROJECT_ROOT"
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔗 激活虚拟环境..."
source "$PROJECT_ROOT/venv/bin/activate"

# 安装依赖
echo "📥 安装依赖..."
pip install -r "$PROJECT_ROOT/requirements.txt" --quiet

# 检查配置文件
if [ ! -f "$PROJECT_ROOT/config/.env" ]; then
    echo "⚠️  .env文件不存在，从模板复制..."
    cp "$PROJECT_ROOT/config/.env.example" "$PROJECT_ROOT/config/.env"
    echo "❗ 请编辑 config/.env 文件设置您的Token和Chat ID"
    exit 1
fi

# 检查必要的配置
if grep -q "YOUR_BOT_TOKEN_HERE" "$PROJECT_ROOT/config/.env"; then
    echo "❗ 请在 config/.env 文件中设置正确的 TELEGRAM_TOKEN"
    exit 1
fi

if grep -q "YOUR_CHAT_ID_HERE" "$PROJECT_ROOT/config/.env"; then
    echo "❗ 请在 config/.env 文件中设置正确的 TELEGRAM_CHAT_ID"
    exit 1
fi

# 加载环境变量
export $(cat "$PROJECT_ROOT/config/.env" | grep -v '^#' | xargs)

# 设置Python路径
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 进入项目目录
cd "$PROJECT_ROOT"

# 启动程序
echo "🤖 启动Bot..."
python3 main.py
