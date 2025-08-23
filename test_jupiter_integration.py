#!/usr/bin/env python3
"""
测试Jupiter配置修改和使用功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.config import get_config

def test_jupiter_config_integration():
    """测试Jupiter配置与爬虫的集成"""
    print("🧪 测试Jupiter配置与爬虫集成功能...")
    
    config = get_config()
    
    print("\n📊 当前Jupiter配置:")
    print(f"  max_mcap: {config.jupiter.max_mcap:,}")
    print(f"  min_token_age: {config.jupiter.min_token_age}")
    print(f"  default_token_count: {config.jupiter.default_token_count}")
    print(f"  max_tokens_per_analysis: {config.jupiter.max_tokens_per_analysis}")
    print(f"  has_socials: {config.jupiter.has_socials}")
    print(f"  period: {config.jupiter.period}")
    
    # 备份原始配置
    original_config = {
        'max_mcap': config.jupiter.max_mcap,
        'min_token_age': config.jupiter.min_token_age,
        'default_token_count': config.jupiter.default_token_count,
        'max_tokens_per_analysis': config.jupiter.max_tokens_per_analysis,
        'has_socials': config.jupiter.has_socials,
        'period': config.jupiter.period
    }
    
    try:
        print("\n🔧 测试配置修改...")
        
        # 修改配置
        test_config = {
            'max_mcap': 5000000,
            'min_token_age': 7200,
            'default_token_count': 5,
            'max_tokens_per_analysis': 25,
            'has_socials': False,
            'period': '7d'
        }
        
        config.update_config('jupiter', **test_config)
        print("✅ 配置修改完成")
        
        # 验证配置生效
        print("\n🔍 验证配置生效...")
        for key, expected_value in test_config.items():
            actual_value = getattr(config.jupiter, key)
            if actual_value == expected_value:
                print(f"  ✅ {key}: {actual_value}")
            else:
                print(f"  ❌ {key}: 期望 {expected_value}, 实际 {actual_value}")
        
        # 测试爬虫是否使用新配置
        print("\n🕷️ 测试爬虫配置使用...")
        try:
            from src.services.jupiter_crawler import JupiterCrawler, JupiterAnalyzer
            
            crawler = JupiterCrawler()
            print(f"  🔧 爬虫默认参数:")
            print(f"    maxMcap: {crawler.default_params['maxMcap']}")
            print(f"    minTokenAge: {crawler.default_params['minTokenAge']}")
            print(f"    hasSocials: {crawler.default_params['hasSocials']}")
            
            # 验证默认参数是否使用了新配置
            if crawler.default_params['maxMcap'] == str(test_config['max_mcap']):
                print("  ✅ 爬虫正确使用了配置的最大市值")
            else:
                print(f"  ❌ 爬虫未使用配置的最大市值")
            
            if crawler.default_params['minTokenAge'] == str(test_config['min_token_age']):
                print("  ✅ 爬虫正确使用了配置的最小代币年龄")
            else:
                print(f"  ❌ 爬虫未使用配置的最小代币年龄")
            
            if crawler.default_params['hasSocials'] == str(test_config['has_socials']).lower():
                print("  ✅ 爬虫正确使用了配置的社交信息要求")
            else:
                print(f"  ❌ 爬虫未使用配置的社交信息要求")
            
            # 测试分析器
            analyzer = JupiterAnalyzer()
            print(f"  📊 分析器配置: default_token_count={analyzer.config.jupiter.default_token_count}")
            
        except Exception as e:
            print(f"  ❌ 测试爬虫时出错: {e}")
        
        print("\n🎉 Jupiter配置集成测试完成！")
        
    finally:
        # 恢复原始配置
        print("\n🔙 恢复原始配置...")
        config.update_config('jupiter', **original_config)
        print("✅ 配置已恢复")

if __name__ == "__main__":
    try:
        test_jupiter_config_integration()
    except Exception as e:
        print(f"\n💥 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
