#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置系统的功能
"""

print("🧪 测试配置系统功能")
print("="*50)

# 导入配置
try:
    from config import TOP_HOLDERS_COUNT, RANKING_SIZE, DETAIL_BUTTONS_COUNT
    print("✅ 配置导入成功:")
    print(f"   TOP_HOLDERS_COUNT: {TOP_HOLDERS_COUNT}")
    print(f"   RANKING_SIZE: {RANKING_SIZE}")
    print(f"   DETAIL_BUTTONS_COUNT: {DETAIL_BUTTONS_COUNT}")
except ImportError as e:
    print(f"❌ 配置导入失败: {e}")

print()

# 测试 format_tokens_table 是否使用配置
try:
    from okx_crawler import format_tokens_table
    
    # 模拟代币统计数据
    mock_token_stats = {
        'top_tokens_by_value': [
            {
                'symbol': f'TOKEN{i:02d}',
                'total_value': 1000000 - i * 10000,
                'holder_count': 50 - i,
                'address': f'addr_{i:02d}_mock_address_for_test'
            }
            for i in range(1, 51)  # 生成50个代币
        ]
    }
    
    print("🔧 测试 format_tokens_table 函数:")
    
    # 测试默认参数（应该使用配置文件的值）
    msg, markup = format_tokens_table(mock_token_stats, cache_key="test")
    
    # 计算消息中的代币数量
    lines = msg.split('\n')
    token_lines = [line for line in lines if line.strip() and any(char.isdigit() for char in line.split('.')[0] if '.' in line)]
    actual_tokens_shown = len([line for line in lines if line.strip().startswith('<b>') and '.' in line])
    
    print(f"   配置的排行榜大小: {RANKING_SIZE}")
    print(f"   实际显示的代币数: {actual_tokens_shown}")
    print(f"   配置的按钮数量: {DETAIL_BUTTONS_COUNT}")
    
    # 检查提示文本
    if f"前{DETAIL_BUTTONS_COUNT}个代币" in msg:
        print("   ✅ 按钮提示文本使用了配置值")
    else:
        print("   ❌ 按钮提示文本未使用配置值")
    
    print("\n📊 生成的消息预览 (前10行):")
    preview_lines = msg.split('\n')[:10]
    for line in preview_lines:
        print(f"   {line}")
    
    if len(msg.split('\n')) > 10:
        print("   ...")
        
except Exception as e:
    print(f"❌ 函数测试失败: {e}")

print("\n✅ 配置系统测试完成!")
print("现在用户可以通过 /config 命令调整:")
print("- 大户分析数量 (TOP_HOLDERS_COUNT)")
print("- 排行榜大小 (RANKING_SIZE)")  
print("- 详情按钮数量 (DETAIL_BUTTONS_COUNT)")
