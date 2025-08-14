"""
基础测试文件
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from src.core.config import ConfigManager
from src.services.blacklist import BlacklistManager
from src.utils import format_number, format_percentage, validate_address


def test_config_manager():
    """测试配置管理器"""
    config = ConfigManager()
    assert config.bot is not None
    assert config.analysis is not None
    assert config.proxy is not None


def test_blacklist_manager():
    """测试黑名单管理器"""
    blacklist = BlacklistManager("test_blacklist.json")
    
    # 清空测试
    blacklist.clear_blacklist()
    assert blacklist.get_blacklist_count() == 0
    
    # 添加测试
    test_address = "TestAddress123"
    assert blacklist.add_to_blacklist(test_address) == True
    assert blacklist.is_blacklisted(test_address) == True
    assert blacklist.get_blacklist_count() == 1
    
    # 重复添加测试
    assert blacklist.add_to_blacklist(test_address) == False
    
    # 删除测试
    assert blacklist.remove_from_blacklist(test_address) == True
    assert blacklist.is_blacklisted(test_address) == False
    assert blacklist.get_blacklist_count() == 0
    
    # 清理测试文件
    if os.path.exists("test_blacklist.json"):
        os.remove("test_blacklist.json")


def test_format_number():
    """测试数字格式化"""
    assert format_number(1000) == "1.00K"
    assert format_number(1000000) == "1.00M"
    assert format_number(1000000000) == "1.00B"
    assert format_number(123.45) == "123.45"


def test_format_percentage():
    """测试百分比格式化"""
    assert format_percentage(0.05) == "5.0%"
    assert format_percentage(1.0) == "100.0%"
    assert format_percentage(0.123) == "12.3%"


def test_validate_address():
    """测试地址验证"""
    # 有效地址示例
    valid_address = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"
    assert validate_address(valid_address) == True
    
    # 无效地址示例
    assert validate_address("") == False
    assert validate_address("short") == False
    assert validate_address("0" * 100) == False
    assert validate_address(None) == False


if __name__ == "__main__":
    pytest.main([__file__])
