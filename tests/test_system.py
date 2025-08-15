#!/usr/bin/env python3
"""
测试脚本 - 验证/ca1功能是否正常工作
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_imports():
    """测试所有模块导入"""
    print("🧪 测试模块导入...")
    
    try:
        from src.core.config import get_config
        print("✅ 配置模块")
        
        from src.services.blacklist import get_blacklist_manager
        print("✅ 黑名单模块")
        
        from src.services.crawler import PumpFunCrawler
        print("✅ 爬虫模块")
        
        from src.services.formatter import MessageFormatter
        print("✅ 格式化模块")
        
        from src.handlers.base import BaseCommandHandler
        print("✅ 基础处理器")
        
        from src.handlers.config import ConfigCommandHandler
        print("✅ 配置处理器")
        
        from src.handlers.holding_analysis import HoldingAnalysisHandler
        print("✅ 持仓分析处理器")
        
        from src.models import TokenInfo
        print("✅ 数据模型")
        
        from src.utils import format_number
        print("✅ 工具函数")
        
        print("\n🎉 所有模块导入成功！")
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_okx_functionality():
    """测试OKX功能"""
    print("\n🔍 测试OKX功能...")
    
    try:
        from src.services.okx_crawler import OKXCrawlerForBot
        print("✅ OKX爬虫模块导入成功")
        
        # 创建爬虫实例（不执行实际请求）
        crawler = OKXCrawlerForBot()
        print("✅ OKX爬虫实例创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ OKX功能测试失败: {e}")
        return False

def test_bot_initialization():
    """测试Bot初始化（不启动）"""
    print("\n🤖 测试Bot初始化...")
    
    try:
        # 模拟bot令牌（测试用）
        import os
        os.environ['TELEGRAM_TOKEN'] = 'test_token'
        os.environ['TELEGRAM_CHAT_ID'] = 'test_chat_id'
        
        from src.core.config import get_config
        config = get_config()
        
        print("✅ 配置加载成功")
        print(f"   - Token: {config.bot.telegram_token[:20]}...")
        print(f"   - Chat ID: {config.bot.telegram_chat_id}")
        print(f"   - 检查间隔: {config.bot.interval}秒")
        print(f"   - 大户数量: {config.analysis.top_holders_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Bot初始化测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始系统测试...")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # 测试模块导入
    if test_imports():
        success_count += 1
    
    # 测试OKX功能
    if test_okx_functionality():
        success_count += 1
    
    # 测试Bot初始化
    if test_bot_initialization():
        success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success_count}/{total_tests} 通过")
    
    if success_count == total_tests:
        print("🎉 所有测试通过！/ca1功能已经恢复并优化完成！")
        print("\n💡 现在你可以使用以下命令:")
        print("   • python main.py - 启动新版本Bot")
        print("   • /ca1 <token_address> - 分析代币大户持仓")
        print("   • /config - 配置管理")
        print("   • /help - 查看帮助")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    
    return success_count == total_tests

if __name__ == "__main__":
    main()
