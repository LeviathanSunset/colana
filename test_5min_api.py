#!/usr/bin/env python3
"""
测试Jupiter 5分钟热门代币API
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.jupiter_crawler import JupiterCrawler
from src.core.config import get_config

def test_5min_api():
    """测试5分钟API"""
    try:
        print("🔧 初始化配置和爬虫...")
        config = get_config()
        crawler = JupiterCrawler()
        
        # 测试5分钟API
        print('🔍 测试获取5分钟热门代币...')
        print('📊 API参数:')
        print('   - period: 5min')
        print('   - mintAuthorityDisabled: true')
        print('   - freezeAuthorityDisabled: true')
        print('   - minNetVolume5m: 1000')
        print('   - maxMcap: 30000')
        print('   - hasSocials: true')
        print('   - minTokenAge: 10000')
        print()
        
        tokens = crawler.fetch_top_traded_tokens(
            period='5min',
            max_mcap=30000,
            min_token_age=10000,
            has_socials=True,
            min_net_volume_5m=1000
        )
        
        print(f'✅ 成功获取 {len(tokens)} 个代币')
        
        if tokens:
            print('\n🎯 代币详情:')
            for i, token in enumerate(tokens[:5]):
                base_asset = token.get('baseAsset', {})
                print(f'{i+1}. 代币信息:')
                print(f'   符号: {base_asset.get("symbol", "Unknown")}')
                print(f'   名称: {base_asset.get("name", "Unknown")}')
                print(f'   地址: {base_asset.get("id", "Unknown")}')
                print(f'   市值: ${base_asset.get("mcap", 0):,}')
                print(f'   5min交易量: ${token.get("volume5m", 0):,}')
                print(f'   流动性: ${token.get("liquidity", 0):,}')
                print()
        else:
            print('💡 当前5分钟内可能没有符合条件的代币')
            print('   这是正常的，因为5分钟是一个很短的时间窗口')
            
        # 测试不带交易量限制的5分钟API
        print('\n🔍 测试不带交易量限制的5分钟API...')
        tokens_no_limit = crawler.fetch_top_traded_tokens(
            period='5min',
            max_mcap=100000,  # 提高市值限制
            min_token_age=3600,  # 降低年龄限制
            has_socials=False  # 不要求社交媒体
        )
        
        print(f'✅ 不带交易量限制获取 {len(tokens_no_limit)} 个代币')
        
        return True

    except Exception as e:
        print(f'❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_5min_api()
    if success:
        print("\n🎉 5分钟API测试完成！")
    else:
        print("\n💥 5分钟API测试失败！")
        sys.exit(1)
