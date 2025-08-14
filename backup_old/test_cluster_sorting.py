#!/usr/bin/env python3
"""
测试集群排序逻辑
"""

def test_cluster_sorting():
    """测试集群按代币数量×地址数量排序"""
    
    # 模拟集群数据
    test_clusters = [
        {
            'cluster_id': 1,
            'address_count': 5,
            'common_tokens_count': 3,
            'total_value': 1000000
        },
        {
            'cluster_id': 2,
            'address_count': 8,
            'common_tokens_count': 2,
            'total_value': 2000000
        },
        {
            'cluster_id': 3,
            'address_count': 3,
            'common_tokens_count': 4,
            'total_value': 500000
        },
        {
            'cluster_id': 4,
            'address_count': 6,
            'common_tokens_count': 3,
            'total_value': 1500000
        }
    ]
    
    print("🔍 测试集群排序逻辑")
    print("排序规则：代币数量 × 地址数量")
    print("\n原始数据：")
    for cluster in test_clusters:
        score = cluster['common_tokens_count'] * cluster['address_count']
        print(f"集群#{cluster['cluster_id']}: {cluster['common_tokens_count']}代币 × {cluster['address_count']}地址 = {score}分 (价值${cluster['total_value']:,})")
    
    # 按新规则排序
    sorted_clusters = sorted(test_clusters, key=lambda x: x['common_tokens_count'] * x['address_count'], reverse=True)
    
    print("\n✅ 按新规则排序后：")
    for i, cluster in enumerate(sorted_clusters, 1):
        score = cluster['common_tokens_count'] * cluster['address_count']
        print(f"第{i}名 - 集群#{cluster['cluster_id']}: {cluster['common_tokens_count']}代币 × {cluster['address_count']}地址 = {score}分")
    
    # 对比旧规则（按价值排序）
    old_sorted = sorted(test_clusters, key=lambda x: x['total_value'], reverse=True)
    print("\n📊 对比旧规则（按价值排序）：")
    for i, cluster in enumerate(old_sorted, 1):
        print(f"第{i}名 - 集群#{cluster['cluster_id']}: 价值${cluster['total_value']:,}")
    
    print("\n🎯 结论：")
    print("• 新规则更注重投资一致性（代币数量）和影响力（地址数量）")
    print("• 不再单纯以资金量为导向，更能识别真正的投资群体")

def test_token_sorting():
    """测试集群内代币按地址数量排序"""
    
    # 模拟代币数据
    test_tokens = [
        {
            'symbol': 'PEPE',
            'cluster_value': 100000,
            'cluster_holders': ['addr1', 'addr2', 'addr3']
        },
        {
            'symbol': 'BONK',
            'cluster_value': 200000,
            'cluster_holders': ['addr1', 'addr2']
        },
        {
            'symbol': 'WIF',
            'cluster_value': 50000,
            'cluster_holders': ['addr1', 'addr2', 'addr3', 'addr4']
        }
    ]
    
    print("\n🪙 测试集群内代币排序")
    print("排序规则：按持有该代币的地址数量")
    print("\n原始数据：")
    for token in test_tokens:
        holder_count = len(token['cluster_holders'])
        print(f"{token['symbol']}: {holder_count}个地址持有，价值${token['cluster_value']:,}")
    
    # 按新规则排序
    sorted_tokens = sorted(test_tokens, key=lambda x: len(x['cluster_holders']), reverse=True)
    
    print("\n✅ 按新规则排序后：")
    for i, token in enumerate(sorted_tokens, 1):
        holder_count = len(token['cluster_holders'])
        print(f"第{i}名 - {token['symbol']}: {holder_count}个地址持有")
    
    print("\n🎯 结论：")
    print("• 优先显示集群内更多地址都持有的代币")
    print("• 体现集群的共同投资偏好，而非单纯的资金集中度")

if __name__ == "__main__":
    test_cluster_sorting()
    test_token_sorting()
