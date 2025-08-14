#!/usr/bin/env python3
"""
测试修复后的集群分析逻辑
"""

def test_fixed_cluster_logic():
    """测试修复后的集群发现逻辑"""
    
    print("🔍 测试修复后的集群分析逻辑")
    
    # 更复杂的测试数据，应该能找到多个集群
    address_tokens = {
        'addr1': {'token_A', 'token_B', 'token_C'},          # 集群1: ABC
        'addr2': {'token_A', 'token_B', 'token_C', 'token_D'}, # 集群1: ABC
        'addr3': {'token_A', 'token_B', 'token_E'},          # 集群1: AB (不够3个)
        'addr4': {'token_X', 'token_Y', 'token_Z'},          # 集群2: XYZ
        'addr5': {'token_X', 'token_Y', 'token_Z', 'token_W'}, # 集群2: XYZ
        'addr6': {'token_X', 'token_Y', 'token_M'},          # 集群2: XY (不够3个)
        'addr7': {'token_P', 'token_Q', 'token_R'},          # 独立地址
        'addr8': {'token_A', 'token_B', 'token_C', 'token_F'}, # 集群1: ABC
    }
    
    CLUSTER_MIN_COMMON_TOKENS = 3
    CLUSTER_MIN_ADDRESSES = 2
    CLUSTER_MAX_ADDRESSES = 50
    
    print("\n📊 测试数据：")
    for addr, tokens in address_tokens.items():
        print(f"{addr}: {tokens}")
    
    print(f"\n配置: 最少{CLUSTER_MIN_COMMON_TOKENS}个共同代币, 集群大小{CLUSTER_MIN_ADDRESSES}-{CLUSTER_MAX_ADDRESSES}")
    
    # 模拟修复后的逻辑
    sorted_addresses = sorted(address_tokens.items(), key=lambda x: len(x[1]), reverse=True)
    
    processed_addresses = set()
    clusters = []
    
    for addr, tokens in sorted_addresses:
        if addr in processed_addresses:
            continue
            
        if len(tokens) < CLUSTER_MIN_COMMON_TOKENS:
            continue
            
        print(f"\n🔍 处理地址 {addr}, 持有代币: {tokens}")
        
        # 寻找与当前地址有共同代币的其他地址
        cluster_addresses = {addr}
        
        # 遍历其他地址，找到有共同代币的
        for other_addr, other_tokens in sorted_addresses:
            if other_addr == addr or other_addr in processed_addresses:
                continue
                
            # 计算共同代币
            shared_tokens = tokens & other_tokens
            print(f"  检查 {other_addr} (持有{other_tokens}), 共同代币: {shared_tokens}")
            
            if len(shared_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                cluster_addresses.add(other_addr)
                print(f"    ✅ 加入集群! (共同代币{len(shared_tokens)}个)")
                
                # 限制集群大小
                if len(cluster_addresses) >= CLUSTER_MAX_ADDRESSES:
                    break
            else:
                print(f"    ❌ 共同代币不足 ({len(shared_tokens)} < {CLUSTER_MIN_COMMON_TOKENS})")
        
        # 计算集群中所有地址真正的共同代币
        if len(cluster_addresses) >= CLUSTER_MIN_ADDRESSES:
            # 找出所有集群地址都持有的代币
            common_tokens = None
            for cluster_addr in cluster_addresses:
                if common_tokens is None:
                    common_tokens = address_tokens[cluster_addr].copy()
                else:
                    common_tokens &= address_tokens[cluster_addr]
                    
            print(f"📊 集群候选: {cluster_addresses}")
            print(f"🎯 真实共同代币: {common_tokens} ({len(common_tokens)}个)")
            
            # 如果找到了足够的地址形成集群且有足够的共同代币
            if len(common_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                cluster_info = {
                    'cluster_id': len(clusters) + 1,
                    'addresses': list(cluster_addresses),
                    'address_count': len(cluster_addresses),
                    'common_tokens': list(common_tokens),
                    'common_tokens_count': len(common_tokens),
                }
                
                clusters.append(cluster_info)
                processed_addresses.update(cluster_addresses)
                
                print(f"    ✅ 发现集群#{len(clusters)}: {len(cluster_addresses)}个地址, {len(common_tokens)}个共同代币")
                print(f"       地址: {cluster_addresses}")
                print(f"       代币: {common_tokens}")
            else:
                print(f"    ❌ 真实共同代币不足: {len(common_tokens)} < {CLUSTER_MIN_COMMON_TOKENS}")
        else:
            print(f"    ❌ 集群地址不足: {len(cluster_addresses)} < {CLUSTER_MIN_ADDRESSES}")
    
    print(f"\n🎉 修复后逻辑结果: 发现 {len(clusters)} 个集群")
    
    for cluster in clusters:
        print(f"\n集群#{cluster['cluster_id']}:")
        print(f"  地址({cluster['address_count']}个): {cluster['addresses']}")
        print(f"  共同代币({cluster['common_tokens_count']}个): {cluster['common_tokens']}")
        
    # 按代币数量×地址数量排序
    clusters.sort(key=lambda x: x['common_tokens_count'] * x['address_count'], reverse=True)
    
    print(f"\n🏆 按评分排序后:")
    for i, cluster in enumerate(clusters, 1):
        score = cluster['common_tokens_count'] * cluster['address_count']
        print(f"第{i}名 - 集群#{cluster['cluster_id']}: {cluster['common_tokens_count']}代币 × {cluster['address_count']}地址 = {score}分")

if __name__ == "__main__":
    test_fixed_cluster_logic()
