#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试集群分析功能
"""

print("🧪 测试地址集群分析功能")
print("="*60)

try:
    from okx_crawler import analyze_address_clusters, format_cluster_analysis
    from config import CLUSTER_MIN_COMMON_TOKENS, CLUSTER_MIN_ADDRESSES, CLUSTER_MAX_ADDRESSES
    
    print("✅ 导入成功")
    print(f"配置: 最少共同代币={CLUSTER_MIN_COMMON_TOKENS}, 集群大小={CLUSTER_MIN_ADDRESSES}-{CLUSTER_MAX_ADDRESSES}")
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    exit(1)

print()

# 模拟分析结果数据
mock_analysis_result = {
    'token_address': 'test_token_address',
    'analysis_time': '2025-08-14T12:00:00',
    'total_holders_analyzed': 20,
    'token_statistics': {
        'total_unique_tokens': 15,
        'total_portfolio_value': 5000000,
        'top_tokens_by_value': [
            {
                'symbol': 'TokenA',
                'name': 'Token A',
                'address': 'addr_token_a',
                'total_value': 2000000,
                'holder_count': 8,
                'holders_details': [
                    {'holder_address': 'whale1', 'value_usd': 100000, 'holder_rank': 1},
                    {'holder_address': 'whale2', 'value_usd': 90000, 'holder_rank': 2},
                    {'holder_address': 'whale3', 'value_usd': 80000, 'holder_rank': 3},
                    {'holder_address': 'whale4', 'value_usd': 70000, 'holder_rank': 4},
                    {'holder_address': 'whale5', 'value_usd': 60000, 'holder_rank': 5},
                ]
            },
            {
                'symbol': 'TokenB',
                'name': 'Token B',
                'address': 'addr_token_b',
                'total_value': 1500000,
                'holder_count': 6,
                'holders_details': [
                    {'holder_address': 'whale1', 'value_usd': 150000, 'holder_rank': 1},  # 和TokenA重叠
                    {'holder_address': 'whale2', 'value_usd': 140000, 'holder_rank': 2},  # 和TokenA重叠
                    {'holder_address': 'whale3', 'value_usd': 130000, 'holder_rank': 3},  # 和TokenA重叠
                    {'holder_address': 'whale6', 'value_usd': 120000, 'holder_rank': 6},
                ]
            },
            {
                'symbol': 'TokenC',
                'name': 'Token C',
                'address': 'addr_token_c',
                'total_value': 1000000,
                'holder_count': 5,
                'holders_details': [
                    {'holder_address': 'whale1', 'value_usd': 50000, 'holder_rank': 1},   # 和TokenA, TokenB重叠
                    {'holder_address': 'whale2', 'value_usd': 45000, 'holder_rank': 2},   # 和TokenA, TokenB重叠
                    {'holder_address': 'whale3', 'value_usd': 40000, 'holder_rank': 3},   # 和TokenA, TokenB重叠
                    {'holder_address': 'whale7', 'value_usd': 35000, 'holder_rank': 7},
                ]
            },
            {
                'symbol': 'TokenD',
                'name': 'Token D',
                'address': 'addr_token_d',
                'total_value': 500000,
                'holder_count': 3,
                'holders_details': [
                    {'holder_address': 'whale1', 'value_usd': 25000, 'holder_rank': 1},   # 和前面重叠
                    {'holder_address': 'whale8', 'value_usd': 20000, 'holder_rank': 8},
                    {'holder_address': 'whale9', 'value_usd': 15000, 'holder_rank': 9},
                ]
            }
        ]
    }
}

print("🔍 开始集群分析...")

try:
    # 执行集群分析
    cluster_result = analyze_address_clusters(mock_analysis_result)
    
    print(f"\n📊 集群分析结果:")
    clusters = cluster_result.get('clusters', [])
    summary = cluster_result.get('analysis_summary', {})
    
    print(f"发现集群数量: {summary.get('total_clusters', 0)}")
    print(f"集群中总地址数: {summary.get('total_addresses_in_clusters', 0)}")
    
    print(f"\n🏆 集群详情:")
    for i, cluster in enumerate(clusters[:3], 1):  # 显示前3个集群
        print(f"集群 #{cluster['cluster_id']}: {cluster['address_count']} 个地址")
        print(f"  总价值: ${cluster['total_value']:,.0f}")
        print(f"  共同代币: {cluster['common_tokens_count']} 个")
        print(f"  地址: {cluster['addresses'][:3]}{'...' if len(cluster['addresses']) > 3 else ''}")
        print(f"  代币: {[t['symbol'] for t in cluster['common_tokens'][:3]]}")
        print()
    
    # 测试格式化函数
    print("📝 格式化消息测试:")
    formatted_msg = format_cluster_analysis(cluster_result, max_clusters=2)
    
    # 显示前10行
    lines = formatted_msg.split('\n')
    print("消息前10行:")
    for line in lines[:10]:
        print(f"  {line}")
    print(f"  ... (总共 {len(lines)} 行)")
    
    print(f"\n✅ 集群分析测试完成!")
    
except Exception as e:
    print(f"❌ 集群分析测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n💡 集群分析功能说明:")
print("• 分析大户间的共同投资模式")
print("• 识别可能的机构投资者、项目方团队")
print("• 发现聪明钱集群和跟随者")
print("• 通过 /ca1 命令中的 '🎯 地址集群分析' 按钮使用")
