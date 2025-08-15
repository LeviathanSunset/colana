#!/usr/bin/env python3
"""
测试 CA1 权限功能
只测试配置加载和权限逻辑
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.config import get_config

def test_ca1_permission_logic():
    """测试CA1权限逻辑"""
    print("=== CA1 权限逻辑测试 ===")
    
    config = get_config()
    
    # 测试用例
    test_cases = [
        ("-1002760368002", "第一个允许的群组"),
        ("-1002593827726", "第二个允许的群组"),
        ("-1001111111111", "不允许的群组"),
        ("123456789", "普通群组"),
    ]
    
    print(f"当前允许的群组: {config.ca1_allowed_groups}")
    print()
    
    for chat_id, description in test_cases:
        print(f"测试 {description} ({chat_id}):")
        
        # 模拟权限检查逻辑 (与实际代码相同)
        allowed_groups = config.ca1_allowed_groups
        has_permission = allowed_groups and str(chat_id) in allowed_groups
        
        print(f"  - 允许的群组列表: {allowed_groups}")
        print(f"  - 当前群组ID (字符串): '{str(chat_id)}'")
        print(f"  - 在允许列表中: {str(chat_id) in allowed_groups if allowed_groups else False}")
        print(f"  - 最终权限: {has_permission}")
        
        if has_permission:
            print(f"  - 结果: ✅ 允许使用 /ca1")
        else:
            print(f"  - 结果: ❌ 拒绝使用 /ca1")
        
        print()

if __name__ == "__main__":
    test_ca1_permission_logic()
