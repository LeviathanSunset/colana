#!/usr/bin/env python3
"""
简化版生产环境启动脚本 - 仅启动 /ca1 功能
"""
import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def validate_environment():
    """验证环境变量"""
    required_vars = ['TELEGRAM_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == 'your_bot_token_here':
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"缺少必要的环境变量: {', '.join(missing_vars)}")

def main():
    """主函数"""
    try:
        print("🚀 启动简化版代币分析Bot (生产环境)...")
        
        # 验证环境
        validate_environment()
        print("✅ 环境变量验证通过")
        
        # 导入并启动Bot
        from main import SimpleTokenBot
        
        bot = SimpleTokenBot()
        print("✅ Bot初始化完成")
        
        bot.start()
        
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
    sys.exit(0)

def check_dependencies():

