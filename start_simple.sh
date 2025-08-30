#!/bin/bash

# 简化版代币分析Bot启动脚本

echo "🚀 启动简化版代币分析Bot..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查配置文件
if [ ! -f ".env" ]; then
    echo "⚠️ 未找到环境变量文件 .env"
    echo "📝 请复制 config/.env.example 到 .env 并配置必要的环境变量"
    echo ""
    echo "必需配置项："
    echo "  - TELEGRAM_TOKEN: Bot令牌"
    echo "  - TELEGRAM_CHAT_ID: 目标群组/频道ID"
    echo ""
    echo "可选配置项请参考 config/.env.example 文件"
    exit 1
fi

if [ ! -f "config/config.yaml" ]; then
    echo "⚠️ 未找到YAML配置文件 config/config.yaml"
    echo "📝 请确保配置文件存在，或程序将使用默认配置"
fi

# 检查依赖
echo "📦 检查依赖..."
python3 -c "import telebot, requests, yaml, dotenv" 2>/dev/null || {
    echo "⚠️ 缺少依赖包，正在安装..."
    pip3 install --break-system-packages -r requirements.txt
}

# 启动Bot
echo "✅ 启动Bot..."
python3 main.py
