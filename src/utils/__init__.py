"""
通用工具函数模块
"""
import time
import datetime
from typing import Union, Any


def timestamp_to_date(timestamp: Union[int, float, str]) -> str:
    """
    将时间戳转换为日期字符串
    
    Args:
        timestamp: 时间戳（秒或毫秒）
        
    Returns:
        格式化的日期字符串
    """
    try:
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        
        # 如果是毫秒时间戳，转换为秒
        if timestamp > 1e10:
            timestamp = timestamp / 1000
            
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return '未知时间'


def format_number(value: Union[int, float, str]) -> str:
    """
    格式化数字显示
    
    Args:
        value: 要格式化的数值
        
    Returns:
        格式化后的字符串
    """
    try:
        value = float(value)
        if abs(value) >= 1_000_000_000:
            return f"{value/1_000_000_000:.2f}B"
        elif abs(value) >= 1_000_000:
            return f"{value/1_000_000:.2f}M"
        elif abs(value) >= 1_000:
            return f"{value/1_000:.2f}K"
        else:
            return f"{value:,.2f}"
    except Exception:
        return str(value)


def format_percentage(value: Union[int, float]) -> str:
    """
    格式化百分比显示
    
    Args:
        value: 百分比值（小数形式）
        
    Returns:
        格式化后的百分比字符串
    """
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "0.0%"


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    安全转换为浮点数
    
    Args:
        value: 要转换的值
        default: 默认值
        
    Returns:
        转换后的浮点数
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    安全转换为整数
    
    Args:
        value: 要转换的值
        default: 默认值
        
    Returns:
        转换后的整数
    """
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def get_current_timestamp() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)


def calculate_age_days(created_timestamp: Union[int, float, str]) -> float:
    """
    计算代币年龄（天数）
    
    Args:
        created_timestamp: 创建时间戳
        
    Returns:
        年龄天数
    """
    try:
        if isinstance(created_timestamp, str):
            created_timestamp = float(created_timestamp)
            
        if created_timestamp <= 0:
            return 0
            
        # 转换为秒时间戳
        if created_timestamp > 1e10:
            created_timestamp = created_timestamp / 1000
            
        current_time = time.time()
        age_seconds = current_time - created_timestamp
        return age_seconds / (24 * 60 * 60)
    except Exception:
        return 0


def truncate_string(text: str, max_length: int = 100) -> str:
    """
    截断字符串
    
    Args:
        text: 原字符串
        max_length: 最大长度
        
    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def validate_address(address: str) -> bool:
    """
    验证Solana地址格式
    
    Args:
        address: 地址字符串
        
    Returns:
        是否为有效地址
    """
    if not address or not isinstance(address, str):
        return False
    
    # Solana地址通常是44个字符的base58编码
    if len(address) < 32 or len(address) > 50:
        return False
        
    # 简单的字符检查
    allowed_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
    return all(c in allowed_chars for c in address)


def chunk_list(lst: list, chunk_size: int):
    """
    将列表分块
    
    Args:
        lst: 原列表
        chunk_size: 每块大小
        
    Returns:
        分块后的生成器
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]
