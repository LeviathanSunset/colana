"""
代币大户分析Bot - 项目配置管理模块
负责环境变量、配置文件的加载和管理
"""

import os
from dataclasses import dataclass
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


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = None):
        self.config_file = config_file or "config/config.json"
        self._bot_config = None
        self._analysis_config = None
        self._proxy_config = None
        self._capump_config = None
        self._ca1_allowed_groups = []
        self.load_config()

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
            
            # 加载ca1允许的群组列表
            if "ca1_allowed_groups" in config_data:
                self._ca1_allowed_groups = config_data["ca1_allowed_groups"]
            else:
                self._ca1_allowed_groups = []

        except Exception as e:
            print(f"配置文件加载失败: {e}")

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

    def save_config(self):
        """保存配置到文件"""
        config_data = {
            "bot": self._bot_config.__dict__,
            "analysis": self._analysis_config.__dict__,
            "capump": self._capump_config.__dict__,
            "ca1_allowed_groups": self._ca1_allowed_groups,
            "proxy": self._proxy_config.__dict__,
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"配置文件保存失败: {e}")

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
        elif section == "proxy":
            for key, value in kwargs.items():
                if hasattr(self._proxy_config, key):
                    setattr(self._proxy_config, key, value)

        self.save_config()


# 全局配置实例
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """获取配置管理器实例"""
    return config_manager


def setup_proxy():
    """设置代理"""
    proxy_config = config_manager.proxy
    if proxy_config.enabled:
        os.environ["HTTP_PROXY"] = proxy_config.http_proxy
        os.environ["HTTPS_PROXY"] = proxy_config.https_proxy
        print(f"✅ 代理已启用: {proxy_config.http_proxy}")
    else:
        # 确保清除代理环境变量
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)
        print("✅ 代理已禁用")
