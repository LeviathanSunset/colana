#!/usr/bin/env python3
"""
调试集群分析问题
"""

def debug_cluster_logic():
    """调试集群发现逻辑"""
    
    print("🔍 调试集群分析逻辑")
    
    # 模拟地址-代币映射
    address_tokens = {
        'addr1': {'token_A', 'token_B', 'token_C'},
        'addr2': {'token_A', 'token_B', 'token_D'},  
        'addr3': {'token_A', 'token_C', 'token_E'},
        'addr4': {'token_B', 'token_C', 'token_F'},
        'addr5': {'token_A', 'token_B', 'token_C', 'token_G'}
    }
    
    CLUSTER_MIN_COMMON_TOKENS = 3
    CLUSTER_MIN_ADDRESSES = 2
    
    print("\n📊 测试数据：")
    for addr, tokens in address_tokens.items():
        print(f"{addr}: {tokens}")
    
    print(f"\n配置: 最少{CLUSTER_MIN_COMMON_TOKENS}个共同代币, 最少{CLUSTER_MIN_ADDRESSES}个地址")
    
    # 模拟当前的错误逻辑
    print("\n❌ 当前错误逻辑测试：")
    sorted_addresses = sorted(address_tokens.items(), key=lambda x: len(x[1]), reverse=True)
    
    processed_addresses = set()
    clusters_old = []
    
    for addr, tokens in sorted_addresses:
        if addr in processed_addresses:
            continue
            
        if len(tokens) < CLUSTER_MIN_COMMON_TOKENS:
            continue
            
        print(f"\n处理地址 {addr}, 持有代币: {tokens}")
        
        cluster_addresses = {addr}
        common_tokens = tokens.copy()
        print(f"初始共同代币: {common_tokens}")
        
        for other_addr, other_tokens in sorted_addresses:
            if other_addr == addr or other_addr in processed_addresses:
                continue
                
            shared_tokens = tokens & other_tokens
            print(f"  检查 {other_addr} (持有{other_tokens}), 与{addr}共同代币: {shared_tokens}")
            
            if len(shared_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                cluster_addresses.add(other_addr)
                old_common = common_tokens.copy()
                common_tokens &= other_tokens  # 这里是问题所在！
                print(f"    ✅ 加入集群! 共同代币更新: {old_common} & {other_tokens} = {common_tokens}")
        
        print(f"最终集群: 地址{len(cluster_addresses)}个, 共同代币{len(common_tokens)}个")
        
        if len(cluster_addresses) >= CLUSTER_MIN_ADDRESSES and len(common_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
            clusters_old.append({
                'addresses': cluster_addresses,
                'common_tokens': common_tokens
            })
            processed_addresses.update(cluster_addresses)
            print(f"    ✅ 发现集群: {cluster_addresses}, 共同代币: {common_tokens}")
        else:
            print(f"    ❌ 不符合条件")
    
    print(f"\n旧逻辑结果: 发现 {len(clusters_old)} 个集群")
    
    # 修正的逻辑
    print("\n\n✅ 修正后的逻辑测试：")
    processed_addresses = set()
    clusters_new = []
    
    for addr, tokens in sorted_addresses:
        if addr in processed_addresses:
            continue
            
        if len(tokens) < CLUSTER_MIN_COMMON_TOKENS:
            continue
            
        print(f"\n处理地址 {addr}, 持有代币: {tokens}")
        
        cluster_addresses = {addr}
        
        # 寻找有足够共同代币的地址
        for other_addr, other_tokens in sorted_addresses:
            if other_addr == addr or other_addr in processed_addresses:
                continue
                
            shared_tokens = tokens & other_tokens
            print(f"  检查 {other_addr} (持有{other_tokens}), 与{addr}共同代币: {shared_tokens}")
            
            if len(shared_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                cluster_addresses.add(other_addr)
                print(f"    ✅ 加入集群!")
        
        # 计算所有集群地址的实际共同代币
        if len(cluster_addresses) >= CLUSTER_MIN_ADDRESSES:
            # 找出所有地址都持有的代币
            common_tokens = None
            for cluster_addr in cluster_addresses:
                if common_tokens is None:
                    common_tokens = address_tokens[cluster_addr].copy()
                else:
                    common_tokens &= address_tokens[cluster_addr]
            
            print(f"集群 {cluster_addresses} 的真实共同代币: {common_tokens}")
            
            if len(common_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                clusters_new.append({
                    'addresses': cluster_addresses,
                    'common_tokens': common_tokens
                })
                processed_addresses.update(cluster_addresses)
                print(f"    ✅ 发现集群: {cluster_addresses}, 共同代币: {common_tokens}")
            else:
                print(f"    ❌ 共同代币不足: {len(common_tokens)} < {CLUSTER_MIN_COMMON_TOKENS}")
        else:
            print(f"    ❌ 地址数量不足: {len(cluster_addresses)} < {CLUSTER_MIN_ADDRESSES}")
    
    print(f"\n新逻辑结果: 发现 {len(clusters_new)} 个集群")
    
    for i, cluster in enumerate(clusters_new, 1):
        print(f"集群{i}: {cluster['addresses']} -> {cluster['common_tokens']}")

if __name__ == "__main__":
    debug_cluster_logic()
