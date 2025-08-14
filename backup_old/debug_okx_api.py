#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试OKX API数据结构
"""

import json
from okx_crawler import OKXCrawlerForBot

def test_okx_api_structure():
    """测试OKX API返回的真实数据结构"""
    crawler = OKXCrawlerForBot()
    
    # 使用一个已知的钱包地址进行测试
    # 这是一个示例地址，你可以替换为实际的大户地址
    test_wallet = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    
    print(f"正在测试钱包地址: {test_wallet}")
    print("=" * 60)
    
    # 获取钱包资产
    wallet_assets = crawler.get_wallet_assets(test_wallet)
    
    if wallet_assets:
        print("✅ 成功获取钱包资产数据")
        print("原始数据结构:")
        print(json.dumps(wallet_assets, indent=2, ensure_ascii=False))
    else:
        print("❌ 获取钱包资产失败")

if __name__ == "__main__":
    test_okx_api_structure()
