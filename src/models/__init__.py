"""
数据模型模块
定义项目中使用的数据结构
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class TokenInfo:
    """代币信息"""

    mint: str
    name: str
    symbol: str
    usd_market_cap: float
    created_timestamp: int
    age_days: float
    change: Optional[float] = None

    @property
    def created_date(self) -> str:
        """获取创建日期字符串"""
        try:
            timestamp = self.created_timestamp / 1000
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        except Exception:
            return "未知"

    @property
    def gmgn_link(self) -> str:
        """获取GMGN链接"""
        return f"https://gmgn.ai/sol/token/{self.mint}"


@dataclass
class HolderInfo:
    """持有者信息"""

    address: str
    balance: float
    percentage: float
    usd_value: float


@dataclass
class ClusterInfo:
    """集群信息"""

    addresses: List[str]
    common_tokens: List[str]
    total_addresses: int
    common_token_count: int


@dataclass
class AnalysisResult:
    """分析结果"""

    token: TokenInfo
    holders: List[HolderInfo]
    clusters: List[ClusterInfo]
    analysis_time: datetime
    cache_key: str


@dataclass
class PriceChangeResult:
    """价格变化结果"""

    token: TokenInfo
    old_price: float
    new_price: float
    change_percent: float
    time_span_minutes: int
