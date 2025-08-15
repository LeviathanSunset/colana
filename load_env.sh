#!/bin/bash

# 临时环境变量设置脚本
# 请修改以下值为你的实际配置，然后运行: source load_env.sh

echo "🔧 加载环境变量..."

# 请替换为你的实际配置
export TELEGRAM_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="-1001234567890"
export MESSAGE_THREAD_ID="40517"

# 可选配置
export PROXY_ENABLED="false"
export TOP_HOLDERS_COUNT="100"
export RANKING_SIZE="30"

echo "✅ 环境变量已设置"
echo "📝 当前配置:"
echo "   TELEGRAM_TOKEN: ${TELEGRAM_TOKEN:0:20}..."
echo "   TELEGRAM_CHAT_ID: $TELEGRAM_CHAT_ID"
echo "   MESSAGE_THREAD_ID: $MESSAGE_THREAD_ID"

echo ""
echo "🚀 现在可以启动bot了:"
echo "   python main.py"
