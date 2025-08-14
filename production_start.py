#!/usr/bin/env python3
"""
生产环境启动脚本
增强的错误处理和监控
"""
import os
import sys
import time
import logging
import signal
import threading
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def setup_logging():
    """设置生产环境日志"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # 创建logs目录
    os.makedirs('logs', exist_ok=True)
    
    # 配置日志格式
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def validate_environment():
    """验证环境变量"""
    required_vars = ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == 'your_bot_token_here':
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"缺少必要的环境变量: {', '.join(missing_vars)}")

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"收到信号 {signum}，正在优雅关闭...")
    sys.exit(0)

def check_dependencies():
    """检查依赖包"""
    try:
        import telebot
        import requests
        logger.info("✅ 依赖检查通过")
    except ImportError as e:
        logger.error(f"❌ 缺少依赖: {e}")
        logger.info("请运行: pip install -r requirements.txt")
        sys.exit(1)

def main():
    """主函数"""
    global logger
    logger = setup_logging()
    
    logger.info("🚀 启动代币分析Bot (生产环境)")
    
    try:
        # 环境检查
        validate_environment()
        check_dependencies()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动主程序
        from main import TokenAnalysisBot
        
        bot = TokenAnalysisBot()
        logger.info("✅ Bot初始化完成")
        
        # 启动健康检查服务器（可选）
        if os.getenv('ENABLE_HEALTH_CHECK', 'false').lower() == 'true':
            from src.utils.health_check import start_health_server
            health_thread = threading.Thread(target=start_health_server, daemon=True)
            health_thread.start()
            logger.info("✅ 健康检查服务器已启动")
        
        # 运行Bot
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("👋 用户中断，正在退出...")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("🔚 程序已退出")

if __name__ == "__main__":
    main()
