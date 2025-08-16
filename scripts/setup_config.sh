#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 Telegram Bot 配置助手${NC}"
echo "==============================="

# 检查配置文件
CONFIG_FILE="config/config.json"
ENV_FILE="config/.env"

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ 配置文件 $CONFIG_FILE 不存在${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 当前配置状态检查...${NC}"

# 检查必要的配置项
check_config() {
    local file=$1
    local token_pattern=$2
    local chat_pattern=$3
    
    if grep -q "$token_pattern" "$file" && grep -q "$chat_pattern" "$file"; then
        echo -e "${RED}❌ 发现默认配置，需要更新${NC}"
        return 1
    else
        echo -e "${GREEN}✅ 配置已设置${NC}"
        return 0
    fi
}

# 检查config.json
echo -n "检查 config.json: "
if check_config "$CONFIG_FILE" "YOUR_BOT_TOKEN_HERE" "YOUR_CHAT_ID_HERE"; then
    CONFIG_OK=true
else
    CONFIG_OK=false
fi

# 检查.env
echo -n "检查 .env: "
if check_config "$ENV_FILE" "YOUR_BOT_TOKEN_HERE" "YOUR_CHAT_ID_HERE"; then
    ENV_OK=true
else
    ENV_OK=false
fi

echo ""
echo -e "${YELLOW}📝 配置说明:${NC}"
echo "1. 获取 Bot Token: 联系 @BotFather"
echo "2. 获取 Chat ID: 将bot添加到群组后发送消息，查看日志"
echo "3. 获取 Thread ID: 在目标Topic中使用 /topicid 命令"
echo ""

if [ "$CONFIG_OK" = true ] || [ "$ENV_OK" = true ]; then
    echo -e "${GREEN}✅ 配置检查通过，可以启动bot${NC}"
    echo ""
    echo -e "${BLUE}🚀 启动命令:${NC}"
    echo "source venv/bin/activate && python main.py"
else
    echo -e "${RED}❌ 需要配置 Token 和 Chat ID 后才能启动${NC}"
    echo ""
    echo -e "${YELLOW}📁 配置文件位置:${NC}"
    echo "- $CONFIG_FILE (JSON格式)"
    echo "- $ENV_FILE (环境变量格式)"
fi

echo ""
echo -e "${BLUE}💡 快速配置示例:${NC}"
echo 'TELEGRAM_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"'
echo 'TELEGRAM_CHAT_ID="-1001234567890"'
echo 'MESSAGE_THREAD_ID="40517"  # 可选'
