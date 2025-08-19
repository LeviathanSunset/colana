#!/usr/bin/env python3
"""
验证多线程功能是否正常集成到Bot中
"""

import sys
import os
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, '/home/root/telegram-bot/colana')

def test_integration():
    """测试多线程功能集成"""
    
    print("🔍 验证多线程功能集成...")
    
    try:
        # 1. 测试导入
        from src.services.okx_crawler import OKXCrawlerForBot
        print("✅ 成功导入 OKXCrawlerForBot")
        
        # 2. 测试配置加载
        try:
            from src.core.config import get_config
            config = get_config()
            thread_count = getattr(config.analysis, 'max_concurrent_threads', 5)
            print(f"✅ 配置加载成功，线程数: {thread_count}")
        except Exception as e:
            print(f"⚠️ 配置加载警告: {e}")
            thread_count = 5
        
        # 3. 测试爬虫实例创建
        crawler = OKXCrawlerForBot()
        print("✅ 爬虫实例创建成功")
        
        # 4. 测试多线程方法存在
        if hasattr(crawler, 'get_wallet_assets_threaded'):
            print("✅ 多线程方法已添加")
        else:
            print("❌ 多线程方法未找到")
            return False
        
        # 5. 测试分析方法签名
        import inspect
        sig = inspect.signature(crawler.analyze_token_holders)
        params = list(sig.parameters.keys())
        
        if 'use_threading' in params:
            print("✅ 分析方法支持多线程参数")
        else:
            print("❌ 分析方法缺少多线程参数")
            return False
        
        # 6. 简单功能测试（不进行实际分析）
        test_addresses = [
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "So11111111111111111111111111111111111111111"
        ]
        
        print("🔄 测试多线程方法调用...")
        start_time = time.time()
        
        # 调用多线程方法（测试小数据集）
        result = crawler.get_wallet_assets_threaded(test_addresses[:1], max_workers=2)
        
        elapsed = time.time() - start_time
        print(f"✅ 多线程方法调用成功，耗时: {elapsed:.1f}s")
        print(f"   返回结果类型: {type(result)}")
        print(f"   结果数量: {len(result)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_bot_status():
    """检查Bot服务状态"""
    print("\n🤖 检查Bot服务状态...")
    
    try:
        import subprocess
        result = subprocess.run(['systemctl', 'is-active', 'colana-bot'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip() == 'active':
            print("✅ Bot服务正在运行")
            return True
        else:
            print(f"⚠️ Bot服务状态: {result.stdout.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ 检查服务状态失败: {e}")
        return False

def main():
    """主函数"""
    print("="*50)
    print("🚀 多线程功能验证测试")
    print("="*50)
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 运行集成测试
    integration_success = test_integration()
    
    # 检查Bot状态
    bot_success = check_bot_status()
    
    print("\n" + "="*50)
    print("📊 测试总结")
    print("="*50)
    
    if integration_success and bot_success:
        print("🎉 所有测试通过！多线程功能已成功集成")
        print("✅ 现在可以享受加速的代币分析体验")
        print("\n💡 使用建议:")
        print("   - 通过 /ca1 命令体验多线程分析")
        print("   - 观察日志中的性能提升信息")
        print("   - 根据需要调整配置中的线程数")
    else:
        print("⚠️ 部分测试失败，请检查:")
        if not integration_success:
            print("   - 多线程功能集成")
        if not bot_success:
            print("   - Bot服务状态")
    
    print("\n📚 相关文档:")
    print("   - docs/MULTITHREADING_GUIDE.md")
    print("   - docs/QUICK_GUIDE.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出现未预期错误: {e}")
        import traceback
        traceback.print_exc()
