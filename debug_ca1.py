#!/usr/bin/env python3
"""
调试 CA1 群组权限问题
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.config import get_config

def debug_ca1_permissions():
    """调试CA1权限配置"""
    print("=== CA1 群组权限调试 ===")
    
    config = get_config()
    
    print(f"配置文件路径: {config.config_file}")
    print(f"允许的群组列表: {config.ca1_allowed_groups}")
    print(f"群组列表类型: {type(config.ca1_allowed_groups)}")
    print(f"群组数量: {len(config.ca1_allowed_groups)}")
    
    # 测试每个群组
    for i, group_id in enumerate(config.ca1_allowed_groups):
        print(f"群组 {i+1}: '{group_id}' (类型: {type(group_id)})")
    
    # 测试权限检查逻辑
    test_chat_ids = [
        "-1002760368002",  # 第一个群组
        "-1002593827726",  # 第二个群组
        "-1001234567890",  # 不存在的群组
    ]
    
    print("\n=== 权限检查测试 ===")
    for chat_id in test_chat_ids:
        allowed_groups = config.ca1_allowed_groups
        has_permission = allowed_groups and chat_id in allowed_groups
        
        print(f"群组 {chat_id}:")
        print(f"  - 有权限列表: {bool(allowed_groups)}")
        print(f"  - 在权限列表中: {chat_id in allowed_groups if allowed_groups else False}")
        print(f"  - 最终权限: {has_permission}")
        print()

if __name__ == "__main__":
    debug_ca1_permissions()
