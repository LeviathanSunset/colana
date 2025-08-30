# 简化版代币分析Bot

这是一个简化版的Telegram机器人，专门用于代币大户持仓分析。

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

## 安装和运行

1. 克隆项目
2. 安装依赖：`pip install -r requirements.txt`
3. 配置环境变量或 `config/config.json`（参考 `config/config.example.json`）
4. 运行：`python main.py` 或 `python production_start.py`

## 配置

### 环境变量
- `TELEGRAM_TOKEN`: Telegram Bot Token
- `TELEGRAM_CHAT_ID`: 允许使用的群组ID（可选）

### 配置文件示例
```json
{
  "bot": {
    "telegram_token": "your_bot_token_here"
  },
  "analysis": {
    "max_concurrent_threads": 5,
    "top_holders_count": 100
  },
  "ca1_allowed_groups": [
    "-1001234567890"
  ]
}
```

## 注意事项

- 此版本仅保留 `/ca1` 代币大户分析功能
- 移除了自动价格监控和其他功能
- 专注于提供最核心的代币分析服务

## 故障排除

### 常见问题和解决方案

**Bot无法启动**
- 检查Telegram Token是否正确
- 确认网络连接正常
- 查看错误日志获取详细信息

**分析功能不可用**
- 检查API服务状态
- 确认代理设置正确
- 验证代币地址格式

**性能问题**
- 调整并发数量
- 检查网络延迟
- 监控系统资源使用

## 注意事项

