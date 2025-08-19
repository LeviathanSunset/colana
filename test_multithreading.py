#!/usr/bin/env python3
"""
测试多线程OKX爬虫功能
"""

import sys
import time
from src.services.okx_crawler import OKXCrawlerForBot

def test_multithreading():
    """测试多线程功能"""
    
    # 创建爬虫实例
    crawler = OKXCrawlerForBot()
    
    # 测试代币地址（使用最近分析过的代币）
    test_token = "LiGHtkg3uTa9836RaNkKLLriqTNRcMdRAhqjGWNv777"
    
    print("🔄 开始测试单线程模式...")
    start_time = time.time()
    
    # 测试单线程模式
    result_single = crawler.analyze_token_holders(
        token_address=test_token,
        top_holders_count=20,  # 只分析前20名减少测试时间
        use_threading=False
    )
    
    single_time = time.time() - start_time
    print(f"✅ 单线程模式完成，耗时: {single_time:.1f}s")
    
    print("\n🔄 开始测试多线程模式...")
    start_time = time.time()
    
    # 测试多线程模式
    result_multi = crawler.analyze_token_holders(
        token_address=test_token,
        top_holders_count=20,  # 只分析前20名减少测试时间
        use_threading=True
    )
    
    multi_time = time.time() - start_time
    print(f"✅ 多线程模式完成，耗时: {multi_time:.1f}s")
    
    # 计算性能提升
    if single_time > 0:
        improvement = (single_time - multi_time) / single_time * 100
        speedup = single_time / multi_time if multi_time > 0 else 0
        
        print(f"\n📊 性能对比:")
        print(f"   单线程耗时: {single_time:.1f}s")
        print(f"   多线程耗时: {multi_time:.1f}s")
        print(f"   性能提升: {improvement:.1f}%")
        print(f"   加速倍数: {speedup:.1f}x")
    
    # 验证结果完整性
    single_holders = result_single.get("total_holders_analyzed", 0)
    multi_holders = result_multi.get("total_holders_analyzed", 0)
    
    print(f"\n📋 结果验证:")
    print(f"   单线程分析钱包数: {single_holders}")
    print(f"   多线程分析钱包数: {multi_holders}")
    
    if single_holders == multi_holders:
        print("✅ 结果一致性验证通过")
    else:
        print("⚠️ 结果数量不一致，可能存在问题")

if __name__ == "__main__":
    try:
        test_multithreading()
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
