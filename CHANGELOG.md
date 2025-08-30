# 简化版Bot - 变更说明

## 已移除的功能

### 自动监控系统
- ❌ 删除了 PumpFun 价格监控
- ❌ 删除了自动爬虫循环
- ❌ 删除了价格变化预警推送
- ❌ 删除了黑名单过滤系统

### 多余的命令
- ❌ `/config` - 配置管理命令
- ❌ `/cajup`, `/jupca` - Jupiter 分析命令  
- ❌ `/jupiter_monitor`, `/jmonitor` - Jupiter 监控命令
- ❌ `/capump` - 自动pump分析命令
- ❌ `/testtopic` - 测试topic命令

### 系统启动功能
- ❌ systemd 服务文件 (colana-bot.service)
- ❌ 部署脚本 (scripts/ 目录)
- ❌ 健康检查服务器
- ❌ 自动重启机制

### 移除的文件
```
scripts/                    - 部署脚本目录
deployment/                 - 系统服务配置
src/handlers/config.py      - 配置管理处理器
src/handlers/jupiter_*.py   - Jupiter相关处理器
src/handlers/auto_pump_*.py - 自动pump分析处理器
src/services/blacklist.py  - 黑名单服务
src/services/crawler.py    - PumpFun爬虫
src/services/jupiter_*.py  - Jupiter服务
src/utils/health_check.py  - 健康检查服务
```

## 保留的功能

### 核心功能
- ✅ `/ca1 <代币地址>` - 代币大户持仓分析
- ✅ `/start` - 欢迎信息
- ✅ `/help` - 帮助信息

### 分析功能
- ✅ 多线程大户数据获取
- ✅ 持仓分布分析
- ✅ 地址集群分析  
- ✅ 代币排名分析
- ✅ 交互式按钮界面

### 保留的文件
```
main.py                     - 简化版主程序
production_start.py         - 简化版生产启动脚本
src/handlers/holding_analysis.py - CA1功能处理器
src/handlers/base.py        - 基础处理器
src/services/okx_crawler.py - OKX数据爬虫
src/services/formatter.py  - 消息格式化
src/core/config.py         - 配置管理
src/utils/logger.py        - 日志系统
src/utils/data_manager.py  - 数据管理
src/models/               - 数据模型
```

## 启动方式

### 方式1：直接启动
```bash
python3 main.py
```

### 方式2：生产环境启动
```bash
python3 production_start.py
```

### 方式3：使用启动脚本
```bash
./start_simple.sh
```

## 配置文件

简化版配置示例 (`config/simple_config.example.json`):
```json
{
  "bot": {
    "telegram_token": "YOUR_BOT_TOKEN_HERE"
  },
  "analysis": {
    "top_holders_count": 100,
    "max_concurrent_threads": 5
  },
  "ca1_allowed_groups": []
}
```

## 环境变量支持

也可以通过环境变量配置：
- `TELEGRAM_TOKEN` - Bot Token
- `TELEGRAM_CHAT_ID` - 群组ID（可选）

这样就实现了一个精简版的Bot，专注于 `/ca1` 代币大户分析功能，移除了所有自动监控和系统启动相关的功能。
