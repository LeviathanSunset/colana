#!/usr/bin/env python3
"""
测试Jupiter爬虫功能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.jupiter_crawler import JupiterCrawler
from src.core.config import get_config

def test_jupiter_crawler():
    """测试Jupiter爬虫"""
    try:
        print("🔧 初始化配置和爬虫...")
        config = get_config()
        crawler = JupiterCrawler()
        
        # 测试获取5分钟热门代币（与您要求的API参数一致）
        print('🔍 测试获取5分钟热门代币...')
        print('📊 API参数:')
        print('   - period: 5min')
        print('   - mintAuthorityDisabled: true')
        print('   - freezeAuthorityDisabled: true')
        print('   - minNetVolume24h: 1000')
        print('   - maxMcap: 30000')
        print('   - hasSocials: true')
        print('   - minTokenAge: 10000')
        print()
        
        tokens = crawler.fetch_top_traded_tokens(
            period='24h',  # 改为24小时
            max_mcap=30000,
            min_token_age=10000,
            has_socials=True,
            min_net_volume_24h=1000
        )
        
        print(f'✅ 成功获取 {len(tokens)} 个代币')
        print()
        
        # 显示前5个代币的详细信息
        for i, token in enumerate(tokens[:5]):
            base_asset = token.get('baseAsset', {})
            print(f'{i+1}. 代币信息:')
            print(f'   符号: {base_asset.get("symbol", "Unknown")}')
            print(f'   名称: {base_asset.get("name", "Unknown")}')
            print(f'   地址: {base_asset.get("id", "Unknown")}')
            print(f'   市值: ${base_asset.get("mcap", 0):,}')
            print(f'   24h交易量: ${token.get("volume24h", 0):,}')
            print(f'   流动性: ${token.get("liquidity", 0):,}')
            print(f'   持有者数: {base_asset.get("holderCount", "Unknown")}')
            
            # 社交媒体信息
            twitter = base_asset.get("twitter", "")
            website = base_asset.get("website", "")
            if twitter or website:
                print(f'   社交媒体: Twitter={bool(twitter)}, Website={bool(website)}')
            
            print()

        # 测试代币地址提取（监控功能需要）
        token_addresses = set()
        for token_data in tokens:
            base_asset = token_data.get('baseAsset', {})
            mint_address = base_asset.get('id', '')
            if mint_address:
                token_addresses.add(mint_address)
        
        print(f'📊 提取到 {len(token_addresses)} 个唯一代币地址')
        print('前5个地址:')
        for i, addr in enumerate(list(token_addresses)[:5]):
            print(f'   {i+1}. {addr}')
        
        return True

    except Exception as e:
        print(f'❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_jupiter_crawler()
    if success:
        print("\n🎉 Jupiter爬虫测试成功！")
    else:
        print("\n💥 Jupiter爬虫测试失败！")
        sys.exit(1)
