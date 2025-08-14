#!/usr/bin/env python3
"""
深度调试集群分析逻辑问题
"""

def debug_current_logic():
    """调试当前逻辑的问题"""
    
    print("🔍 深度调试当前集群分析逻辑")
    
    # 模拟一个会暴露问题的场景
    address_tokens = {
        'addr1': {'token_A', 'token_B'},          # 与addr2有AB共同
        'addr2': {'token_A', 'token_B', 'token_C'}, # 与addr1有AB，与addr3有BC  
        'addr3': {'token_B', 'token_C'},          # 与addr2有BC
        'addr4': {'token_X', 'token_Y'},          # 独立
    }
    
    CLUSTER_MIN_COMMON_TOKENS = 2
    CLUSTER_MIN_ADDRESSES = 3
    
    print("\n📊 测试数据：")
    for addr, tokens in address_tokens.items():
        print(f"{addr}: {tokens}")
    
    print(f"\n问题场景：")
    print(f"• addr1 & addr2 共同持有: {address_tokens['addr1'] & address_tokens['addr2']} (2个)")
    print(f"• addr2 & addr3 共同持有: {address_tokens['addr2'] & address_tokens['addr3']} (2个)")  
    print(f"• addr1 & addr3 共同持有: {address_tokens['addr1'] & address_tokens['addr3']} (1个) ❌")
    print(f"• 三者共同持有: {address_tokens['addr1'] & address_tokens['addr2'] & address_tokens['addr3']} (1个) ❌")
    
    print(f"\n配置: 最少{CLUSTER_MIN_COMMON_TOKENS}个共同代币, 最少{CLUSTER_MIN_ADDRESSES}个地址")
    
    # 模拟当前逻辑
    sorted_addresses = sorted(address_tokens.items(), key=lambda x: len(x[1]), reverse=True)
    processed_addresses = set()
    
    print(f"\n🔍 当前逻辑执行：")
    
    for addr, tokens in sorted_addresses:
        if addr in processed_addresses:
            continue
            
        if len(tokens) < CLUSTER_MIN_COMMON_TOKENS:
            continue
            
        print(f"\n处理地址 {addr}, 持有代币: {tokens}")
        
        cluster_addresses = {addr}
        
        # 寻找有共同代币的地址
        for other_addr, other_tokens in sorted_addresses:
            if other_addr == addr or other_addr in processed_addresses:
                continue
                
            shared_tokens = tokens & other_tokens
            print(f"  检查 {other_addr} (持有{other_tokens}), 共同代币: {shared_tokens}")
            
            if len(shared_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                cluster_addresses.add(other_addr)
                print(f"    ✅ 加入集群! (共同代币{len(shared_tokens)}个)")
            else:
                print(f"    ❌ 共同代币不足 ({len(shared_tokens)} < {CLUSTER_MIN_COMMON_TOKENS})")
        
        print(f"集群候选: {cluster_addresses}")
        
        # 计算真实共同代币
        if len(cluster_addresses) >= CLUSTER_MIN_ADDRESSES:
            common_tokens = None
            for cluster_addr in cluster_addresses:
                if common_tokens is None:
                    common_tokens = address_tokens[cluster_addr].copy()
                else:
                    common_tokens &= address_tokens[cluster_addr]
            
            print(f"真实共同代币: {common_tokens} ({len(common_tokens)}个)")
            
            if len(common_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                print(f"    ✅ 符合条件的集群!")
                processed_addresses.update(cluster_addresses)
            else:
                print(f"    ❌ 真实共同代币不足: {len(common_tokens)} < {CLUSTER_MIN_COMMON_TOKENS}")
        else:
            print(f"    ❌ 地址数量不足: {len(cluster_addresses)} < {CLUSTER_MIN_ADDRESSES}")

def suggest_better_logic():
    """建议更好的逻辑"""
    
    print(f"\n\n💡 问题分析和建议：")
    
    print(f"\n🐛 当前逻辑的问题：")
    print(f"1. 传递性错误：A-B有共同代币，B-C有共同代币，不代表A-B-C都有共同代币")
    print(f"2. 配置过严：要求3个地址都持有2个相同代币，条件太苛刻")
    print(f"3. 缺乏渐进逻辑：没有从小集群扩展到大集群的机制")
    
    print(f"\n✅ 改进建议：")
    print(f"1. 降低门槛：CLUSTER_MIN_ADDRESSES = 2（先找2个地址的集群）")
    print(f"2. 添加调试日志：打印每一步的计算过程")
    print(f"3. 分层发现：先找强关联（多个共同代币），再找弱关联")
    print(f"4. 渐进扩展：从核心2-3个地址开始，逐步扩展集群")

def test_with_relaxed_config():
    """用放宽的配置测试"""
    
    print(f"\n🧪 用放宽配置测试：")
    
    address_tokens = {
        'addr1': {'token_A', 'token_B'},
        'addr2': {'token_A', 'token_B', 'token_C'},
        'addr3': {'token_B', 'token_C'},
        'addr4': {'token_X', 'token_Y'},
        'addr5': {'token_X', 'token_Y', 'token_Z'},
    }
    
    CLUSTER_MIN_COMMON_TOKENS = 2
    CLUSTER_MIN_ADDRESSES = 2  # 放宽到2个地址
    
    print(f"\n放宽配置: 最少{CLUSTER_MIN_COMMON_TOKENS}个共同代币, 最少{CLUSTER_MIN_ADDRESSES}个地址")
    
    sorted_addresses = sorted(address_tokens.items(), key=lambda x: len(x[1]), reverse=True)
    processed_addresses = set()
    clusters = []
    
    for addr, tokens in sorted_addresses:
        if addr in processed_addresses:
            continue
            
        if len(tokens) < CLUSTER_MIN_COMMON_TOKENS:
            continue
            
        cluster_addresses = {addr}
        
        for other_addr, other_tokens in sorted_addresses:
            if other_addr == addr or other_addr in processed_addresses:
                continue
                
            shared_tokens = tokens & other_tokens
            
            if len(shared_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                cluster_addresses.add(other_addr)
        
        if len(cluster_addresses) >= CLUSTER_MIN_ADDRESSES:
            # 计算真实共同代币
            common_tokens = None
            for cluster_addr in cluster_addresses:
                if common_tokens is None:
                    common_tokens = address_tokens[cluster_addr].copy()
                else:
                    common_tokens &= address_tokens[cluster_addr]
            
            if len(common_tokens) >= CLUSTER_MIN_COMMON_TOKENS:
                clusters.append({
                    'addresses': cluster_addresses,
                    'common_tokens': common_tokens
                })
                processed_addresses.update(cluster_addresses)
                print(f"✅ 发现集群: {cluster_addresses} -> {common_tokens}")
            else:
                print(f"❌ 集群 {cluster_addresses} 真实共同代币不足: {common_tokens}")
    
    print(f"\n放宽配置结果: 发现 {len(clusters)} 个集群")

if __name__ == "__main__":
    debug_current_logic()
    suggest_better_logic()
    test_with_relaxed_config()
