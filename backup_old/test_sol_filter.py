#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SOL过滤功能
"""

print("🧪 测试SOL过滤功能")
print("="*50)

try:
    from okx_crawler import OKXCrawlerForBot
    
    # 创建爬虫实例
    crawler = OKXCrawlerForBot()
    
    # 模拟包含SOL的资产数据
    mock_assets_data = {
        'tokens': {
            'tokenlist': [
                {
                    'symbol': 'SOL',
                    'name': 'Solana',
                    'chainName': 'Solana',
                    'coinAmount': '100',
                    'coinUnitPrice': '150',
                    'currencyAmount': '15000',
                    'coinBalanceDetails': [{'address': 'So11111111111111111111111111111111111111112'}]
                },
                {
                    'symbol': 'USDT',
                    'name': 'Tether USD',
                    'chainName': 'Solana',
                    'coinAmount': '1000',
                    'coinUnitPrice': '1',
                    'currencyAmount': '1000',
                    'coinBalanceDetails': [{'address': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}]
                },
                {
                    'symbol': 'BONK',
                    'name': 'Bonk',
                    'chainName': 'Solana',
                    'coinAmount': '1000000',
                    'coinUnitPrice': '0.0001',
                    'currencyAmount': '100',
                    'coinBalanceDetails': [{'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'}]
                }
            ]
        }
    }
    
    print("📊 原始数据:")
    for token in mock_assets_data['tokens']['tokenlist']:
        print(f"  {token['symbol']}: ${token['currencyAmount']}")
    
    print(f"\n🔧 测试 extract_top_tokens 函数:")
    
    # 测试提取代币功能
    extracted_tokens = crawler.extract_top_tokens(mock_assets_data)
    
    print(f"提取结果:")
    for token in extracted_tokens:
        print(f"  {token['symbol']}: ${token['value_usd']:.0f}")
    
    # 检查是否过滤了SOL
    sol_found = any(token['symbol'] == 'SOL' for token in extracted_tokens)
    
    if sol_found:
        print("\n❌ SOL过滤失败 - SOL仍然存在于结果中")
    else:
        print("\n✅ SOL过滤成功 - SOL已被正确过滤")
    
    print(f"\n📝 过滤前: 3个代币 (SOL, USDT, BONK)")
    print(f"过滤后: {len(extracted_tokens)}个代币")
    
    if len(extracted_tokens) == 2:
        symbols = [token['symbol'] for token in extracted_tokens]
        print(f"保留的代币: {', '.join(symbols)}")
        print("✅ 过滤结果正确")
    else:
        print("❌ 过滤结果不正确")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n💡 SOL过滤说明:")
print("• SOL是Solana区块链的原生代币")
print("• 几乎每个钱包都持有SOL (用于支付Gas费)")
print("• 过滤SOL可以专注分析项目代币的投资模式")
print("• 集群分析将更准确地识别共同投资模式")

print("\n📊 百分比含义说明:")
print("• 百分比 = (集群在该代币中的持仓价值 / 所有大户在该代币中的总持仓价值) × 100%")
print("• 例如: 如果所有大户在TokenA中总共持有$1M")
print("• 而某个集群在TokenA中持有$150K")
print("• 则该集群在TokenA中的占比为 15.0%")
print("• 较高的百分比表示该集群在该代币中有显著影响力")
