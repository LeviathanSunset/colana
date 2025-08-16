#!/bin/bash

# 代币大户分析Bot部署脚本
echo "🚀 开始部署代币大户分析Bot..."

# 检查当前目录
if [ ! -f "main.py" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

# 1. 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 2. 激活虚拟环境并安装依赖
echo "📦 安装依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. 检查配置文件
if [ ! -f "config/.env" ]; then
    echo "⚠️  .env文件不存在，从示例文件创建..."
    cp config/.env.example config/.env
    echo "请编辑 config/.env 文件，填入你的Bot Token和Chat ID"
    exit 1
fi

# 4. 测试配置
echo "🔧 测试配置..."
export $(cat config/.env | grep -v '^#' | xargs)
python3 -c "
import sys
sys.path.insert(0, 'src')
from src.core.config import ConfigManager
config = ConfigManager()
if config.bot.telegram_token == 'YOUR_BOT_TOKEN_HERE':
    print('❌ 请在config/.env文件中设置正确的TELEGRAM_TOKEN')
    exit(1)
if config.bot.telegram_chat_id == 'YOUR_CHAT_ID_HERE':
    print('❌ 请在config/.env文件中设置正确的TELEGRAM_CHAT_ID')
    exit(1)
print('✅ 配置检查通过')
"

if [ $? -ne 0 ]; then
    echo "❌ 配置检查失败，请检查config/.env文件"
    exit 1
fi

# 5. 设置systemd服务（可选）
read -p "是否设置为系统服务？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔧 设置systemd服务..."
    sudo cp colana-bot.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable colana-bot
    echo "✅ 服务已设置，使用以下命令管理："
    echo "  启动: sudo systemctl start colana-bot"
    echo "  停止: sudo systemctl stop colana-bot"
    echo "  状态: sudo systemctl status colana-bot"
    echo "  日志: sudo journalctl -u colana-bot -f"
fi

echo "🎉 部署完成！"
echo ""
echo "启动方式："
echo "1. 直接启动: ./start.sh"
echo "2. 后台启动: nohup ./start.sh > bot.log 2>&1 &"
echo "3. 系统服务: sudo systemctl start colana-bot"
