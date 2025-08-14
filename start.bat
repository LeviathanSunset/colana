@echo off
title Token Analysis Bot
echo.
echo ========================================
echo   🤖 代币大户分析Bot 启动脚本
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装或未添加到PATH
    echo 请先安装Python 3.7+
    pause
    exit /b 1
)

:: 检查依赖是否安装
echo 📦 检查依赖...
python -c "import telebot, requests" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  依赖未安装，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)

:: 检查配置文件
if not exist "config.json" (
    if exist "config.example.json" (
        echo ⚠️  配置文件不存在，复制示例配置...
        copy config.example.json config.json >nul
        echo ✅ 已创建 config.json，请编辑配置后重新运行
        echo.
        echo 📝 需要配置的项目:
        echo   - telegram_token: 你的Bot Token
        echo   - telegram_chat_id: 目标群组ID
        echo.
        pause
        exit /b 0
    ) else (
        echo ❌ 配置文件不存在
        pause
        exit /b 1
    )
)

:: 启动Bot
echo 🚀 启动机器人...
echo.
python main.py

:: 如果程序异常退出，暂停以便查看错误信息
if errorlevel 1 (
    echo.
    echo ❌ 程序异常退出
    pause
)
