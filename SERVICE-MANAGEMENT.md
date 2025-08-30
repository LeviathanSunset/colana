# Telegram Bot 系统服务管理

## 服务状态

Telegram Bot 已设置为系统服务，会在系统启动时自动运行。

## 快速管理脚本

### 安装系统服务
```bash
./install-service.sh
```

### 检查服务状态
```bash
./check-service.sh
```

### 卸载系统服务
```bash
./uninstall-service.sh
```

## 手动管理命令

### 服务管理
```bash
# 启动服务
systemctl start colana-bot

# 停止服务
systemctl stop colana-bot

# 重启服务
systemctl restart colana-bot

# 查看服务状态
systemctl status colana-bot

# 启用开机自启动
systemctl enable colana-bot

# 禁用开机自启动
systemctl disable colana-bot
```

### 日志查看
```bash
# 查看实时日志
journalctl -u colana-bot -f

# 查看最近50行日志
journalctl -u colana-bot --lines=50

# 查看今天的日志
journalctl -u colana-bot --since today
```

## 服务配置文件

- **服务文件**: `/etc/systemd/system/colana-bot.service`
- **工作目录**: `/home/root/telegram-bot/cocolanababanana`
- **配置文件**: `/home/root/telegram-bot/cocolanababanana/config/.env`
- **日志存储**: `/home/root/telegram-bot/cocolanababanana/storage/logs/`

## 故障排查

### 服务无法启动
1. 检查配置文件是否正确：
   ```bash
   cat /home/root/telegram-bot/cocolanababanana/config/.env
   ```

2. 检查依赖是否安装：
   ```bash
   cd /home/root/telegram-bot/cocolanababanana
   python3 -c "import telebot, requests, yaml, dotenv; print('✅ 依赖检查通过')"
   ```

3. 查看详细错误日志：
   ```bash
   journalctl -u colana-bot --lines=50
   ```

### 手动启动测试
如果服务有问题，可以手动启动进行调试：
```bash
cd /home/root/telegram-bot/cocolanababanana
python3 main.py
```

## 系统要求

- **操作系统**: Linux (测试于 Ubuntu/Debian)
- **Python**: 3.7+
- **权限**: root (用于系统服务管理)
- **网络**: 需要访问 Telegram API 和 OKX API

## 开机自启动确认

系统重启后，服务会自动启动。可以通过以下命令确认：
```bash
systemctl is-enabled colana-bot  # 应该返回 "enabled"
systemctl is-active colana-bot   # 应该返回 "active"
```
