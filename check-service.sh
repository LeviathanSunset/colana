#!/bin/bash

# Telegram Bot 服务状态检查脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_NAME="colana-bot"

echo -e "${BLUE}🤖 Telegram Bot 服务状态${NC}"
echo "=========================="

# 检查服务状态
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "服务状态: ${GREEN}✅ 运行中${NC}"
else
    echo -e "服务状态: ${RED}❌ 已停止${NC}"
fi

# 检查开机自启动
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "开机自启: ${GREEN}✅ 已启用${NC}"
else
    echo -e "开机自启: ${RED}❌ 未启用${NC}"
fi

# 显示服务详细信息
echo ""
echo -e "${YELLOW}详细状态:${NC}"
systemctl status "$SERVICE_NAME" --no-pager --lines=5

echo ""
echo -e "${YELLOW}最近日志:${NC}"
journalctl -u "$SERVICE_NAME" --lines=5 --no-pager

echo ""
echo -e "${BLUE}管理命令:${NC}"
echo -e "  查看状态: ${YELLOW}systemctl status $SERVICE_NAME${NC}"
echo -e "  查看日志: ${YELLOW}journalctl -u $SERVICE_NAME -f${NC}"
echo -e "  重启服务: ${YELLOW}systemctl restart $SERVICE_NAME${NC}"
echo -e "  停止服务: ${YELLOW}systemctl stop $SERVICE_NAME${NC}"
