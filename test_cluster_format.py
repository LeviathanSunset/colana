#!/usr/bin/env python3
"""
测试集群格式化函数
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.okx_crawler import format_cluster_analysis

# 创建测试数据
test_cluster_result = {
    'clusters': [
        {
            'cluster_id': 1,
            'addresses': [
                '6imaCAFbJXZYTt5DmnL7uwJL7a5',
                'GY7JKVAdHKQrKnRAQMwEnBZAW',
                'GLuoSKNhBP3Q3N3UJ4VEwUL'
            ],
            'address_count': 3,
            'total_value': 18950,
            'common_tokens': [
                {
                    'symbol': 'assteroid',
                    'name': 'Asteroid Token',
                    'address': 'FLxwDc58Fnb9h1Yq6Vc7YhXjFPwzZadhLPJpUHGMjups',
                    'cluster_value': 8690,
                    'cluster_percentage': 11.9
                },
                {
                    'symbol': 'USDC',
                    'name': 'USD Coin',
                    'address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                    'cluster_value': 10260,
                    'cluster_percentage': 10.8
                }
            ],
            'common_tokens_count': 2,
            'avg_value_per_address': 6316.67
        }
    ],
    'analysis_summary': {
        'total_clusters': 1,
        'total_addresses_in_clusters': 3
    }
}

# 测试函数
print("🧪 测试集群格式化函数...")
result = format_cluster_analysis(test_cluster_result, max_clusters=1)
print("\n结果:")
print(result)
print("\n✅ 测试完成")
