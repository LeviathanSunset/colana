#!/bin/bash

# 简化版代币分析Bot启动脚本

echo "🚀 启动简化版代币分析Bot..."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查配置文件
if [ ! -f "config/config.json" ]; then
    echo "⚠️ 未找到配置文件 config/config.json"
    echo "📝 请复制 config/config.example.json 到 config/config.json 并配置"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
python3 -c "import telebot, requests" 2>/dev/null || {
    echo "⚠️ 缺少依赖包，正在安装..."
    pip3 install -r requirements.txt
}

# 启动Bot
echo "✅ 启动Bot..."
python3 main.py
