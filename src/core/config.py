"""
代币大户分析Bot - 项目配置管理模块
负责环境变量、配置文件的加载和管理
"""

import os
from dataclasses import dataclass
from typing import List
import json


@dataclass
class BotConfig:
    """机器人基础配置"""

    telegram_token: str
    telegram_chat_id: str
    message_thread_id: int = None
    interval: int = 58
    threshold: float = 0.05
    min_market_cap: float = 0
    min_age_days: int = 10


@dataclass
class AnalysisConfig:
    """分析相关配置"""

    top_holders_count: int = 100
    ranking_size: int = 30
    detail_buttons_count: int = 30
    cluster_min_common_tokens: int = 2
    cluster_min_addresses: int = 2
    cluster_max_addresses: int = 50
    clusters_per_page: int = 3
    # 已知的池子地址列表（即使OKX检测不到也要识别）
    known_pool_addresses: List[str] = None
    
    def __post_init__(self):
        if self.known_pool_addresses is None:
            self.known_pool_addresses = [
                "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"  # 已知池子地址
            ]


@dataclass
class ProxyConfig:
    """代理配置"""

    http_proxy: str = "http://127.0.0.1:10808"
    https_proxy: str = "http://127.0.0.1:10808"
    enabled: bool = True


@dataclass
class CapumpConfig:
    """Capump分析配置"""
    
    interval: int = 120
    threshold: float = 0.10
    min_market_cap: float = 50000
    min_age_days: int = 1
    auto_analysis_enabled: bool = False
    max_tokens_per_batch: int = 10
    analysis_timeout: int = 180
    notification_enabled: bool = True


@dataclass  
class JupiterConfig:
    """Jupiter分析配置"""
    
    max_mcap: int = 1000000
    min_token_age: int = 3600
    has_socials: bool = True
    period: str = "24h"
    max_tokens_per_analysis: int = 50
    default_token_count: int = 10


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = None):
        self.config_file = config_file or "config/config.json"
        self._bot_config = None
        self._analysis_config = None
        self._proxy_config = None
        self._capump_config = None
        self._jupiter_config = None
        self._ca1_allowed_groups = []
        self._logger = None
        self.load_config()
    
    @property
    def logger(self):
        """延迟加载logger以避免循环导入"""
        if self._logger is None:
            try:
                from ..utils.logger import get_logger
                self._logger = get_logger("config")
            except ImportError:
                # 如果logger模块不可用，使用print作为后备
                class SimpleLogger:
                    def info(self, msg): print(f"INFO: {msg}")
                    def error(self, msg): print(f"ERROR: {msg}")
                    def exception(self, msg): print(f"EXCEPTION: {msg}")
                    def debug(self, msg): print(f"DEBUG: {msg}")
                    def warning(self, msg): print(f"WARNING: {msg}")
                self._logger = SimpleLogger()
        return self._logger

    def load_config(self):
        """加载配置"""
        # 优先从环境变量加载
        self._load_from_env()

        # 从文件加载配置
        if os.path.exists(self.config_file):
            self._load_from_file()
        else:
            # 使用默认配置
            self._load_defaults()

    def _load_from_env(self):
        """从环境变量加载配置"""
        self._bot_config = BotConfig(
            telegram_token=os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE"),
            message_thread_id=int(os.getenv("MESSAGE_THREAD_ID")) if os.getenv("MESSAGE_THREAD_ID") else None,
            interval=int(os.getenv("INTERVAL", 58)),
            threshold=float(os.getenv("THRESHOLD", 0.05)),
            min_market_cap=float(os.getenv("MIN_MARKET_CAP", 0)),
            min_age_days=int(os.getenv("MIN_AGE_DAYS", 10)),
        )

        self._analysis_config = AnalysisConfig(
            top_holders_count=int(os.getenv("TOP_HOLDERS_COUNT", 100)),
            ranking_size=int(os.getenv("RANKING_SIZE", 30)),
            detail_buttons_count=int(os.getenv("DETAIL_BUTTONS_COUNT", 30)),
            cluster_min_common_tokens=int(os.getenv("CLUSTER_MIN_COMMON_TOKENS", 2)),
            cluster_min_addresses=int(os.getenv("CLUSTER_MIN_ADDRESSES", 2)),
            cluster_max_addresses=int(os.getenv("CLUSTER_MAX_ADDRESSES", 50)),
            clusters_per_page=int(os.getenv("CLUSTERS_PER_PAGE", 3)),
            known_pool_addresses=["5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"],  # 默认已知池子地址
        )

        self._proxy_config = ProxyConfig(
            http_proxy=os.getenv("HTTP_PROXY", "http://127.0.0.1:10808"),
            https_proxy=os.getenv("HTTPS_PROXY", "http://127.0.0.1:10808"),
            enabled=os.getenv("PROXY_ENABLED", "true").lower() == "true",
        )

        self._capump_config = CapumpConfig(
            interval=int(os.getenv("CAPUMP_INTERVAL", 120)),
            threshold=float(os.getenv("CAPUMP_THRESHOLD", 0.10)),
            min_market_cap=float(os.getenv("CAPUMP_MIN_MARKET_CAP", 50000)),
            min_age_days=int(os.getenv("CAPUMP_MIN_AGE_DAYS", 1)),
            auto_analysis_enabled=os.getenv("CAPUMP_AUTO_ANALYSIS", "false").lower() == "true",
            max_tokens_per_batch=int(os.getenv("CAPUMP_MAX_TOKENS_PER_BATCH", 10)),
            analysis_timeout=int(os.getenv("CAPUMP_ANALYSIS_TIMEOUT", 180)),
            notification_enabled=os.getenv("CAPUMP_NOTIFICATION", "true").lower() == "true",
        )

        self._jupiter_config = JupiterConfig(
            max_mcap=int(os.getenv("JUPITER_MAX_MCAP", 1000000)),
            min_token_age=int(os.getenv("JUPITER_MIN_TOKEN_AGE", 3600)),
            has_socials=os.getenv("JUPITER_HAS_SOCIALS", "true").lower() == "true",
            period=os.getenv("JUPITER_PERIOD", "24h"),
            max_tokens_per_analysis=int(os.getenv("JUPITER_MAX_TOKENS_PER_ANALYSIS", 50)),
            default_token_count=int(os.getenv("JUPITER_DEFAULT_TOKEN_COUNT", 10)),
        )

    def _load_from_file(self):
        """从文件加载配置"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # 更新bot配置
            if "bot" in config_data:
                bot_data = config_data["bot"]
                if hasattr(self._bot_config, "__dict__"):
                    for key, value in bot_data.items():
                        if hasattr(self._bot_config, key):
                            setattr(self._bot_config, key, value)
            
            # 更新analysis配置
            if "analysis" in config_data:
                analysis_data = config_data["analysis"]
                if hasattr(self._analysis_config, "__dict__"):
                    for key, value in analysis_data.items():
                        if hasattr(self._analysis_config, key):
                            setattr(self._analysis_config, key, value)
            
            # 更新capump配置
            if "capump" in config_data:
                capump_data = config_data["capump"]
                if hasattr(self._capump_config, "__dict__"):
                    for key, value in capump_data.items():
                        if hasattr(self._capump_config, key):
                            setattr(self._capump_config, key, value)
            
            # 更新jupiter配置
            if "jupiter" in config_data:
                jupiter_data = config_data["jupiter"]
                if hasattr(self._jupiter_config, "__dict__"):
                    for key, value in jupiter_data.items():
                        if hasattr(self._jupiter_config, key):
                            setattr(self._jupiter_config, key, value)
            
            # 更新proxy配置
            if "proxy" in config_data:
                proxy_data = config_data["proxy"]
                if hasattr(self._proxy_config, "__dict__"):
                    for key, value in proxy_data.items():
                        if hasattr(self._proxy_config, key):
                            setattr(self._proxy_config, key, value)
            
            # 加载ca1允许的群组列表
            if "ca1_allowed_groups" in config_data:
                self._ca1_allowed_groups = config_data["ca1_allowed_groups"]
            else:
                self._ca1_allowed_groups = []

        except Exception as e:
            self.logger.exception(f"❌ 配置文件加载失败: {e}")
            self._load_defaults()

    def _load_defaults(self):
        """加载默认配置"""
        if not self._bot_config:
            self._bot_config = BotConfig(
                telegram_token="YOUR_BOT_TOKEN_HERE", 
                telegram_chat_id="YOUR_CHAT_ID_HERE",
                message_thread_id=None
            )

        if not self._analysis_config:
            self._analysis_config = AnalysisConfig()

        if not self._proxy_config:
            self._proxy_config = ProxyConfig()

        if not self._capump_config:
            self._capump_config = CapumpConfig()

        if not self._jupiter_config:
            self._jupiter_config = JupiterConfig()

    def save_config(self):
        """保存配置到文件"""
        config_data = {
            "bot": self._bot_config.__dict__,
            "analysis": self._analysis_config.__dict__,
            "capump": self._capump_config.__dict__,
            "jupiter": self._jupiter_config.__dict__,
            "ca1_allowed_groups": self._ca1_allowed_groups,
            "proxy": self._proxy_config.__dict__,
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"💾 配置文件保存成功: {self.config_file}")
        except Exception as e:
            self.logger.exception(f"❌ 配置文件保存失败: {e}")

    @property
    def bot(self) -> BotConfig:
        return self._bot_config

    @property
    def analysis(self) -> AnalysisConfig:
        return self._analysis_config

    @property
    def proxy(self) -> ProxyConfig:
        return self._proxy_config

    @property
    def capump(self) -> CapumpConfig:
        return self._capump_config

    @property
    def jupiter(self) -> JupiterConfig:
        return self._jupiter_config

    @property
    def ca1_allowed_groups(self) -> list:
        """获取允许使用 /ca1 命令的群组列表"""
        return self._ca1_allowed_groups

    def update_config(self, section: str, **kwargs):
        """更新配置"""
        if section == "bot":
            for key, value in kwargs.items():
                if hasattr(self._bot_config, key):
                    setattr(self._bot_config, key, value)
        elif section == "analysis":
            for key, value in kwargs.items():
                if hasattr(self._analysis_config, key):
                    setattr(self._analysis_config, key, value)
        elif section == "capump":
            for key, value in kwargs.items():
                if hasattr(self._capump_config, key):
                    setattr(self._capump_config, key, value)
        elif section == "jupiter":
            for key, value in kwargs.items():
                if hasattr(self._jupiter_config, key):
                    setattr(self._jupiter_config, key, value)
        elif section == "proxy":
            for key, value in kwargs.items():
                if hasattr(self._proxy_config, key):
                    setattr(self._proxy_config, key, value)

        self.save_config()

    def add_known_pool_address(self, address: str):
        """添加已知的池子地址"""
        if address not in self._analysis_config.known_pool_addresses:
            self._analysis_config.known_pool_addresses.append(address)
            self.save_config()
            self.logger.info(f"✅ 已添加池子地址: {address}")
            return True
        else:
            self.logger.info(f"⚠️ 池子地址已存在: {address}")
            return False
    
    def remove_known_pool_address(self, address: str):
        """移除已知的池子地址"""
        if address in self._analysis_config.known_pool_addresses:
            self._analysis_config.known_pool_addresses.remove(address)
            self.save_config()
            self.logger.info(f"✅ 已移除池子地址: {address}")
            return True
        else:
            self.logger.info(f"⚠️ 池子地址不存在: {address}")
            return False


# 全局配置实例
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """获取配置管理器实例"""
    return config_manager


def setup_proxy():
    """设置代理"""
    try:
        from ..utils.logger import get_logger
        logger = get_logger("proxy")
    except ImportError:
        # 如果logger模块不可用，使用print作为后备
        class SimpleLogger:
            def info(self, msg): print(msg)
        logger = SimpleLogger()
    
    proxy_config = config_manager.proxy
    if proxy_config.enabled:
        os.environ["HTTP_PROXY"] = proxy_config.http_proxy
        os.environ["HTTPS_PROXY"] = proxy_config.https_proxy
        logger.info(f"✅ 代理已启用: {proxy_config.http_proxy}")
    else:
        # 确保清除代理环境变量
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)
        logger.info("✅ 代理已禁用")
