#!/bin/bash

# Telegram Bot 系统服务卸载脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_NAME="colana-bot"

echo -e "${BLUE}🗑️ Telegram Bot 系统服务卸载程序${NC}"
echo "========================================"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ 请使用root权限运行此脚本${NC}"
    exit 1
fi

# 停止服务
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${YELLOW}⏹️ 停止服务...${NC}"
    systemctl stop "$SERVICE_NAME"
fi

# 禁用服务
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${YELLOW}🚫 禁用开机自启动...${NC}"
    systemctl disable "$SERVICE_NAME"
fi

# 删除服务文件
if [ -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
    echo -e "${YELLOW}🗑️ 删除服务文件...${NC}"
    rm "/etc/systemd/system/$SERVICE_NAME.service"
fi

# 重新加载systemd
echo -e "${YELLOW}🔄 重新加载systemd配置...${NC}"
systemctl daemon-reload

echo ""
echo -e "${GREEN}✅ 系统服务卸载完成！${NC}"
echo -e "${BLUE}Bot服务已从系统中移除，不会再开机自启动。${NC}"
