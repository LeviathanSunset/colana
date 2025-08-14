# 🚀 服务器部署指南

## 📋 部署前准备

### 1. 环境变量配置
为了安全起见，敏感信息应该通过环境变量配置：

```bash
# 创建环境变量文件
nano ~/.env

# 添加以下内容：
export TELEGRAM_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
export HTTP_PROXY="http://127.0.0.1:10808"  # 如果需要代理
export HTTPS_PROXY="http://127.0.0.1:10808"
export PROXY_ENABLED="false"  # 服务器可能不需要代理

# 分析参数
export TOP_HOLDERS_COUNT="100"
export RANKING_SIZE="30"
export DETAIL_BUTTONS_COUNT="30"
export CLUSTER_MIN_COMMON_TOKENS="2"
export CLUSTER_MIN_ADDRESSES="2"
export CLUSTER_MAX_ADDRESSES="50"

# 加载环境变量
source ~/.env
```

### 2. 系统依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# CentOS/RHEL
sudo yum install python3 python3-pip git
```

## 🔧 代码改进建议

### 1. 日志系统改进
创建更完善的日志配置：

```python
# src/utils/logger.py
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logger(name, log_file=None, level=logging.INFO):
    """设置日志器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
```

### 2. 异常处理改进
```python
# src/utils/error_handler.py
import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                    if attempt == max_retries - 1:
                        logger.error(f"所有重试都失败: {e}")
                        raise
                    time.sleep(delay * (2 ** attempt))  # 指数退避
            return None
        return wrapper
    return decorator

def safe_execute(func: Callable, default_return=None, log_error=True):
    """安全执行函数，捕获异常"""
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"执行失败: {e}", exc_info=True)
        return default_return
```

### 3. 配置验证
```python
# src/core/config_validator.py
def validate_config(config):
    """验证配置参数"""
    errors = []
    
    # Bot配置验证
    if not config.bot.telegram_token or config.bot.telegram_token == "YOUR_BOT_TOKEN_HERE":
        errors.append("请设置有效的Telegram Bot Token")
    
    if not config.bot.telegram_chat_id or config.bot.telegram_chat_id == "YOUR_CHAT_ID_HERE":
        errors.append("请设置有效的Telegram Chat ID")
    
    # 数值范围验证
    if config.analysis.top_holders_count < 1 or config.analysis.top_holders_count > 500:
        errors.append("TOP_HOLDERS_COUNT 应在 1-500 之间")
    
    if config.analysis.ranking_size < 1 or config.analysis.ranking_size > 100:
        errors.append("RANKING_SIZE 应在 1-100 之间")
    
    if errors:
        raise ValueError("配置验证失败:\n" + "\n".join(errors))
    
    return True
```

### 4. 数据库支持
```python
# src/models/database.py
import sqlite3
import json
from datetime import datetime

class AnalysisDatabase:
    """分析结果数据库"""
    
    def __init__(self, db_path="data/analysis.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT NOT NULL,
            analysis_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result_data TEXT NOT NULL,
            status TEXT DEFAULT 'success'
        )
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_token_address 
        ON analysis_results(token_address)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_analysis(self, token_address, result_data):
        """保存分析结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO analysis_results (token_address, result_data)
        VALUES (?, ?)
        ''', (token_address, json.dumps(result_data, ensure_ascii=False)))
        
        conn.commit()
        conn.close()
```

### 5. 性能监控
```python
# src/utils/performance.py
import time
import psutil
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            result = func(*args, **kwargs)
            status = "SUCCESS"
        except Exception as e:
            result = None
            status = f"ERROR: {e}"
            raise
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            
            logger.info(f"函数 {func.__name__} 执行完成:")
            logger.info(f"  状态: {status}")
            logger.info(f"  耗时: {execution_time:.2f}s")
            logger.info(f"  内存变化: {memory_usage:+.2f}MB")
        
        return result
    return wrapper
```

## 🐳 Docker 部署

### 1. Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要目录
RUN mkdir -p logs data

# 设置权限
RUN chmod +x start.sh

# 暴露端口（如果需要健康检查）
EXPOSE 8080

# 启动命令
CMD ["python", "main.py"]
```

### 2. docker-compose.yml
```yaml
version: '3.8'

services:
  colana-bot:
    build: .
    container_name: colana-bot
    restart: unless-stopped
    environment:
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - PROXY_ENABLED=false
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - colana-network

  # 可选：添加监控
  prometheus:
    image: prom/prometheus
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - colana-network

networks:
  colana-network:
    driver: bridge
```

## 🔒 安全建议

### 1. 敏感信息保护
```python
# 不要在代码中硬编码敏感信息
# ❌ 错误做法
TELEGRAM_TOKEN = "7962867262:AAGg0abpPE3nr4spCrFklnewq5gMFJWNqgY"

# ✅ 正确做法
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("请设置 TELEGRAM_TOKEN 环境变量")
```

### 2. 访问控制
```python
# src/middleware/auth.py
def check_user_permission(user_id, chat_id):
    """检查用户权限"""
    allowed_users = os.getenv('ALLOWED_USERS', '').split(',')
    allowed_chats = os.getenv('ALLOWED_CHATS', '').split(',')
    
    if str(user_id) not in allowed_users and str(chat_id) not in allowed_chats:
        return False
    return True
```

## 🔄 部署流程

### 1. 生产环境部署脚本
```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 开始部署代币分析Bot..."

# 1. 更新代码
git pull origin main

# 2. 检查环境变量
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "❌ 请设置 TELEGRAM_TOKEN 环境变量"
    exit 1
fi

# 3. 安装/更新依赖
pip install -r requirements.txt

# 4. 运行配置验证
python -c "
from src.core.config import get_config
from src.core.config_validator import validate_config
config = get_config()
validate_config(config)
print('✅ 配置验证通过')
"

# 5. 备份旧日志
if [ -d "logs" ]; then
    tar -czf "logs_backup_$(date +%Y%m%d_%H%M%S).tar.gz" logs/
fi

# 6. 创建systemd服务
sudo tee /etc/systemd/system/colana-bot.service > /dev/null <<EOF
[Unit]
Description=Colana Token Analysis Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=/usr/bin:/usr/local/bin
EnvironmentFile=/home/$USER/.env
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 7. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable colana-bot
sudo systemctl start colana-bot

echo "✅ 部署完成!"
echo "📊 查看状态: sudo systemctl status colana-bot"
echo "📝 查看日志: sudo journalctl -u colana-bot -f"
```

### 2. 健康检查
```python
# src/utils/health_check.py
from flask import Flask, jsonify
import threading
import requests

app = Flask(__name__)

@app.route('/health')
def health_check():
    """健康检查接口"""
    try:
        # 检查Bot状态
        bot_status = check_bot_status()
        
        # 检查网络连接
        network_status = check_network()
        
        return jsonify({
            'status': 'healthy',
            'bot_status': bot_status,
            'network_status': network_status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def start_health_server():
    """启动健康检查服务器"""
    app.run(host='0.0.0.0', port=8080, debug=False)

# 在main.py中添加
if __name__ == "__main__":
    # 启动健康检查服务器（后台线程）
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # 启动主程序
    bot = TokenAnalysisBot()
    bot.run()
```

## 📈 监控和维护

### 1. 日志轮转配置
```bash
# /etc/logrotate.d/colana-bot
/home/username/colana2min10/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 username username
    postrotate
        systemctl reload colana-bot
    endscript
}
```

### 2. 监控脚本
```bash
#!/bin/bash
# monitor.sh

# 检查进程状态
if ! pgrep -f "python.*main.py" > /dev/null; then
    echo "❌ Bot进程未运行，正在重启..."
    systemctl restart colana-bot
fi

# 检查内存使用
memory_usage=$(ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem | grep python | head -1 | awk '{print $4}')
if (( $(echo "$memory_usage > 80" | bc -l) )); then
    echo "⚠️  内存使用率过高: $memory_usage%"
    # 可以选择重启或发送告警
fi

# 检查磁盘空间
disk_usage=$(df -h /home | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $disk_usage -gt 90 ]; then
    echo "⚠️  磁盘空间不足: $disk_usage%"
    # 清理旧日志
    find logs/ -name "*.log" -mtime +7 -delete
fi
```

## 🎯 总结

主要改进点：
1. **安全性**: 环境变量配置，访问控制
2. **可靠性**: 重试机制，异常处理，健康检查
3. **可维护性**: 完善日志，监控告警
4. **可扩展性**: 数据库支持，模块化设计
5. **部署自动化**: Docker，systemd服务

这些改进能让你的Bot在生产环境中更加稳定可靠！
