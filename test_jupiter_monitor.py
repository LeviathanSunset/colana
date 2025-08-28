#!/usr/bin/env python3
"""
测试Jupiter监控功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.jupiter_crawler import JupiterCrawler
from src.handlers.jupiter_monitor import JupiterMonitorHandler
from src.core.config import get_config

def test_jupiter_api():
    """测试Jupiter API"""
    print("🧪 测试Jupiter API...")
    
    crawler = JupiterCrawler()
    
    # 测试严格参数
    print("\n📊 使用严格参数测试:")
    tokens = crawler.fetch_top_traded_tokens(
        period="5m",
        min_net_volume_5m=1000,
        max_mcap=30000,
        has_socials=True,
        min_token_age=10000
    )
    
    print(f"✅ 获取到 {len(tokens)} 个符合严格条件的代币")
    
    if tokens:
        print("\n📋 前3个代币信息:")
        for i, token in enumerate(tokens[:3]):
            base_asset = token.get('baseAsset', {})
            stats5m = base_asset.get('stats5m', {})
            
            print(f"{i+1}. {base_asset.get('name', 'Unknown')} ({base_asset.get('symbol', 'N/A')})")
            print(f"   地址: {base_asset.get('id', 'N/A')}")
            print(f"   市值: ${base_asset.get('mcap', 0):,.2f}")
            print(f"   5min交易量: ${stats5m.get('buyVolume', 0) + stats5m.get('sellVolume', 0):,.2f}")
            print(f"   价格变化(5min): {stats5m.get('priceChange', 0):+.2f}%")
            print()
    else:
        print("⚠️  没有找到符合条件的代币，尝试放松参数...")
        
        # 测试放松的参数
        tokens_relaxed = crawler.fetch_top_traded_tokens(
            period="5m",
            min_net_volume_5m=100,
            max_mcap=100000,
            has_socials=False,
            min_token_age=1000
        )
        
        print(f"✅ 放松参数后获取到 {len(tokens_relaxed)} 个代币")
        
        if tokens_relaxed:
            print("\n📋 前3个代币信息:")
            for i, token in enumerate(tokens_relaxed[:3]):
                base_asset = token.get('baseAsset', {})
                stats5m = base_asset.get('stats5m', {})
                
                print(f"{i+1}. {base_asset.get('name', 'Unknown')} ({base_asset.get('symbol', 'N/A')})")
                print(f"   地址: {base_asset.get('id', 'N/A')}")
                print(f"   市值: ${base_asset.get('mcap', 0):,.2f}")
                print(f"   5min交易量: ${stats5m.get('buyVolume', 0) + stats5m.get('sellVolume', 0):,.2f}")
                print(f"   价格变化(5min): {stats5m.get('priceChange', 0):+.2f}%")
                print()

def test_monitor_logic():
    """测试监控逻辑"""
    print("\n🧪 测试监控逻辑...")
    
    # 创建一个模拟的监控处理器（但不启动实际的bot）
    try:
        from unittest.mock import Mock
        
        # 模拟bot对象
        mock_bot = Mock()
        monitor = JupiterMonitorHandler(mock_bot)
        
        print("✅ JupiterMonitorHandler 初始化成功")
        print(f"📊 监控参数: {monitor.monitor_params}")
        
        # 测试获取当前代币
        tokens = monitor._fetch_current_tokens()
        if tokens:
            print(f"✅ 获取到 {len(tokens)} 个符合条件的代币地址")
            print(f"📋 前5个代币地址: {list(tokens)[:5]}")
        else:
            print("⚠️  没有获取到符合条件的代币")
            
    except Exception as e:
        print(f"❌ 监控逻辑测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始Jupiter监控功能测试...\n")
    
    try:
        test_jupiter_api()
        test_monitor_logic()
        
        print("\n✅ 所有测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
