#!/bin/bash

# Telegram Bot 系统服务安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="/home/root/telegram-bot/cocolanababanana"
SERVICE_NAME="colana-ca1-bot"
SERVICE_FILE="$PROJECT_DIR/$SERVICE_NAME.service"

echo -e "${BLUE}🤖 Telegram Bot CA1 简化版系统服务安装程序${NC}"
echo "========================================"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ 请使用root权限运行此脚本${NC}"
    exit 1
fi

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi

# 检查服务文件
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}❌ 服务文件不存在: $SERVICE_FILE${NC}"
    exit 1
fi

# 检查配置文件
echo -e "${YELLOW}📋 检查配置文件...${NC}"
if [ ! -f "$PROJECT_DIR/config/.env" ]; then
    echo -e "${RED}❌ 环境变量文件不存在: $PROJECT_DIR/config/.env${NC}"
    echo "请先复制并配置环境变量文件："
    echo "cp $PROJECT_DIR/config/.env.example $PROJECT_DIR/config/.env"
    exit 1
fi

# 检查配置是否有效
cd "$PROJECT_DIR"
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
" || exit 1

# 安装依赖
echo -e "${YELLOW}📦 检查并安装Python依赖...${NC}"
pip3 install -r "$PROJECT_DIR/requirements.txt" --break-system-packages --quiet || {
    echo -e "${YELLOW}⚠️ 使用系统包管理器安装依赖...${NC}"
    # 如果pip失败，尝试使用apt安装常见包
    apt update -qq
    apt install -y python3-requests python3-yaml python3-dotenv python3-typing-extensions || true
}

# 停止现有服务（如果存在）
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${YELLOW}⏹️ 停止现有服务...${NC}"
    systemctl stop "$SERVICE_NAME"
fi

# 复制服务文件
echo -e "${YELLOW}📝 安装服务文件...${NC}"
cp "$SERVICE_FILE" "/etc/systemd/system/"

# 重新加载systemd
echo -e "${YELLOW}🔄 重新加载systemd配置...${NC}"
systemctl daemon-reload

# 启用服务
echo -e "${YELLOW}✅ 启用开机自启动...${NC}"
systemctl enable "$SERVICE_NAME"

# 启动服务
echo -e "${YELLOW}🚀 启动服务...${NC}"
systemctl start "$SERVICE_NAME"

# 等待几秒钟检查状态
sleep 3

# 检查服务状态
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✅ 服务启动成功！${NC}"
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    echo -e "${YELLOW}查看错误日志:${NC}"
    journalctl -u "$SERVICE_NAME" --lines=10 --no-pager
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 系统服务安装完成！${NC}"
echo ""
echo -e "${BLUE}常用管理命令:${NC}"
echo -e "  启动服务: ${YELLOW}systemctl start $SERVICE_NAME${NC}"
echo -e "  停止服务: ${YELLOW}systemctl stop $SERVICE_NAME${NC}"
echo -e "  重启服务: ${YELLOW}systemctl restart $SERVICE_NAME${NC}"
echo -e "  查看状态: ${YELLOW}systemctl status $SERVICE_NAME${NC}"
echo -e "  查看日志: ${YELLOW}journalctl -u $SERVICE_NAME -f${NC}"
echo -e "  禁用自启: ${YELLOW}systemctl disable $SERVICE_NAME${NC}"
echo ""
echo -e "${GREEN}Bot已设置为开机自启动，将在系统重启后自动运行！${NC}"
