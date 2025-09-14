#!/bin/bash

# 代币大户分析Bot启动脚本
echo "🚀 启动代币大户分析Bot..."

# 进入项目目录
cd /root/projects/colana

# 加载环境变量
if [ -f config/.env ]; then
    echo "📝 加载环境变量..."
    export $(cat config/.env | grep -v '^#' | xargs)
else
    echo "❌ 未找到config/.env文件"
    exit 1
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
. venv/bin/activate

# 检查依赖
echo "📦 检查依赖..."
pip list | grep -q "pyTelegramBotAPI" || {
    echo "❌ 依赖未安装，正在安装..."
    pip install -r requirements.txt
}

# 启动Bot
echo "🤖 启动Bot..."
python3 main.py
