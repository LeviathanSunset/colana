# 简化版代币分析Bot

这是一个简化版的Telegram机器人，专门用于代币大户持仓分析。采用 **YAML + .env 混合配置方案**，敏感信息和业务配置分离管理。

## 功能

### 🔍 代币大户分析 (`/ca1`)
- 分析指定代币的大户持仓分布
- 支持地址集群分析
- 可按不同维度排序查看
- 提供详细的持仓统计信息
- **🚀 多线程加速**: 并发获取钱包资产，大幅提升分析速度

## 使用方法

### 基本命令

```
/start - 显示欢迎信息
/help - 显示帮助信息
/ca1 <代币地址> - 分析指定代币大户持仓
```

### 大户分析功能

使用 `/ca1` 命令可以：
- 获取代币的TOP持有者列表
- 分析持仓集中度和分布
- 查看大户地址详细信息
- 统计持仓比例和数量

使用示例：
```
/ca1 EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
```

## 功能特点

- **高效分析**: 多线程并发处理，快速获取大户数据
- **精准分析**: 专注于代币大户持仓分析
- **稳定可靠**: 完善的错误处理和重试机制
- **资源优化**: 智能缓存和频率控制
- **配置分离**: 敏感信息与业务配置分离管理

## 安装和运行

### 快速开始

1. **克隆项目**
   ```bash
   git clone <repository_url>
   cd telegram-bot
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   # 复制环境变量模板
   cp config/.env.example .env
   
   # 编辑 .env 文件，填入必要信息
   nano .env
   ```

4. **运行Bot**
   ```bash
   # 使用启动脚本（推荐）
   bash start_simple.sh
   
   # 或直接运行
   python3 main.py
   ```

## 配置系统

### 🔧 混合配置方案

本项目采用 **YAML + .env 混合配置**，实现敏感信息与业务配置的分离：

- **`.env` 文件**: 存储敏感信息（Token、ID等）
- **`config.yaml` 文件**: 存储业务配置（参数、开关等）

### 📝 必需配置 (.env 文件)

复制 `config/.env.example` 到 `.env`，并配置以下必需项：

```bash
# 必需配置
TELEGRAM_TOKEN=你的Bot令牌
TELEGRAM_CHAT_ID=目标群组或频道ID

# 可选配置
MESSAGE_THREAD_ID=指定Topic ID（可选）
```

### ⚙️ 业务配置 (config.yaml 文件)

主要配置项在 `config/config.yaml` 中，包括：

```yaml
# 分析相关配置
analysis:
  top_holders_count: 100         # 获取前N名持有者
  ranking_size: 30               # 排行榜显示数量
  max_concurrent_threads: 5      # 最大并发线程数

# 权限控制
permissions:
  ca1_allowed_groups: []         # 允许使用 /ca1 的群组ID列表

# 代理配置
proxy:
  enabled: false                 # 代理开关
  http_proxy: "http://127.0.0.1:10808"
```

### 🔀 配置优先级

配置加载优先级（从高到低）：
1. **环境变量** - 运行时设置的环境变量
2. **`.env` 文件** - 本地环境变量文件
3. **`config.yaml` 文件** - YAML业务配置
4. **默认值** - 代码中的默认配置

### 📋 配置示例

**环境变量覆盖示例**：
```bash
# 临时覆盖配置运行
TOP_HOLDERS_COUNT=200 PROXY_ENABLED=true python3 main.py
```

**权限控制示例**：
```yaml
# config.yaml
permissions:
  ca1_allowed_groups:
    - "-1001234567890"  # 只允许特定群组使用
    - "-1001234567891"
```

## 故障排除

### 🚨 常见问题和解决方案

**Bot无法启动**
- 检查 `.env` 文件是否存在且配置正确
- 验证 `TELEGRAM_TOKEN` 是否有效
- 确认网络连接正常

**配置加载失败**
- 检查 `config.yaml` 语法是否正确
- 确认 YAML 缩进使用空格而非Tab
- 查看启动日志获取详细错误信息

**分析功能不可用**
- 检查依赖包是否完整安装
- 确认API服务状态
- 验证代币地址格式

**权限问题**
- 检查群组ID是否在 `ca1_allowed_groups` 中
- 确认Bot已被添加到目标群组
- 验证Bot具有发送消息权限

### 📊 调试模式

启用调试模式查看详细日志：
```bash
LOG_LEVEL=DEBUG python3 main.py
```

## 项目结构

```
├── config/
│   ├── .env.example          # 环境变量模板
│   └── config.yaml           # 业务配置文件
├── src/
│   ├── core/
│   │   └── config.py         # 配置管理模块
│   ├── handlers/             # 命令处理器
│   ├── services/             # 业务服务
│   └── utils/                # 工具模块
├── .env                      # 环境变量文件（需创建）
├── main.py                   # 主程序入口
├── requirements.txt          # 依赖清单
└── start_simple.sh          # 启动脚本
```

## 注意事项

- 此版本仅保留 `/ca1` 代币大户分析功能
- 移除了自动价格监控和其他功能
- 专注于提供最核心的代币分析服务
- **重要**: 不要将 `.env` 文件提交到代码库

