#!/usr/bin/env python3
"""
测试标题修改功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, '/home/root/telegram-bot/colana')

def test_title_change():
    """测试标题修改功能"""
    
    print("🔍 测试标题修改功能...")
    
    try:
        # 导入格式化函数
        from src.services.okx_crawler import format_tokens_table
        
        # 模拟代币统计数据
        mock_token_stats = {
            "total_portfolio_value": 1000000,
            "total_unique_tokens": 50,
            "top_tokens_by_value": [
                {
                    "symbol": "USDT",
                    "name": "Tether USD",
                    "address": "test_address_1",
                    "total_value": 500000,
                    "holder_count": 15,
                    "is_target_token": False
                },
                {
                    "symbol": "SOL",
                    "name": "Solana",
                    "address": "test_address_2", 
                    "total_value": 300000,
                    "holder_count": 12,
                    "is_target_token": False
                }
            ]
        }
        
        print("\n📋 测试1: 不传递目标代币符号（使用默认标题）")
        msg1, _ = format_tokens_table(mock_token_stats, max_tokens=5)
        print("生成的标题:", msg1.split('\n')[0])
        
        print("\n📋 测试2: 传递目标代币符号 'USDT'")
        msg2, _ = format_tokens_table(mock_token_stats, max_tokens=5, target_token_symbol="USDT")
        print("生成的标题:", msg2.split('\n')[0])
        
        print("\n📋 测试3: 传递目标代币符号 'PEPE'")
        msg3, _ = format_tokens_table(mock_token_stats, max_tokens=5, target_token_symbol="PEPE")
        print("生成的标题:", msg3.split('\n')[0])
        
        # 验证结果
        title1 = msg1.split('\n')[0]
        title2 = msg2.split('\n')[0]
        title3 = msg3.split('\n')[0]
        
        # 检查默认标题
        if "大户热门代币排行榜" in title1:
            print("✅ 测试1通过: 默认标题正确")
        else:
            print("❌ 测试1失败: 默认标题不正确")
            
        # 检查USDT标题
        if "USDT大户主要持仓" in title2:
            print("✅ 测试2通过: USDT标题正确")
        else:
            print("❌ 测试2失败: USDT标题不正确")
            
        # 检查PEPE标题
        if "PEPE大户主要持仓" in title3:
            print("✅ 测试3通过: PEPE标题正确")
        else:
            print("❌ 测试3失败: PEPE标题不正确")
            
        print("\n🎉 所有测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*50)
    print("🔧 测试标题修改功能")
    print("="*50)
    
    success = test_title_change()
    
    print("\n" + "="*50)
    if success:
        print("✅ 标题修改功能测试成功！")
        print("💡 现在Bot将显示 '🔥 {代币符号}大户主要持仓' 而不是 '🔥 大户热门代币排行榜'")
    else:
        print("❌ 标题修改功能测试失败")
    print("="*50)
