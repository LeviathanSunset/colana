#!/usr/bin/env python3
"""
日志系统测试脚本
用于验证日志功能是否正常工作
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.logger import get_logger

def test_logging():
    """测试日志功能"""
    # 获取不同模块的日志器
    main_logger = get_logger("test_main")
    crawler_logger = get_logger("test_crawler")
    
    # 测试不同级别的日志
    main_logger.info("🚀 开始测试日志系统...")
    
    main_logger.debug("🔍 这是调试信息")
    main_logger.info("ℹ️ 这是一般信息")
    main_logger.warning("⚠️ 这是警告信息")
    main_logger.error("❌ 这是错误信息")
    
    crawler_logger.info("🕷️ 爬虫模块日志测试")
    crawler_logger.debug("📊 爬虫调试信息")
    
    # 测试异常日志
    try:
        raise ValueError("这是一个测试异常")
    except Exception as e:
        main_logger.exception("❗ 捕获到测试异常")
    
    main_logger.info("✅ 日志系统测试完成")
    print("日志测试完成，请检查 storage/logs 目录中的日志文件")

if __name__ == "__main__":
    test_logging()
