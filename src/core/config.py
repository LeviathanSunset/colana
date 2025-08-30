"""
代币大户分析Bot - 项目配置管理模块
支持 YAML + .env 混合配置方案
- 敏感信息使用 .env 文件
- 业务配置使用 YAML 文件
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv


@dataclass
class BotConfig:
    """机器人基础配置"""
    telegram_token: str
    telegram_chat_id: str
    message_thread_id: Optional[int] = None
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
    max_concurrent_threads: int = 5
    known_pool_addresses: List[str] = field(default_factory=lambda: ["5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"])


@dataclass
class ProxyConfig:
    """代理配置"""
    enabled: bool = False
    http_proxy: str = "http://127.0.0.1:10808"
    https_proxy: str = "http://127.0.0.1:10808"


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


@dataclass
class PermissionsConfig:
    """权限控制配置"""
    ca1_allowed_groups: List[str] = field(default_factory=list)
    allowed_users: List[str] = field(default_factory=list)
    allowed_chats: List[str] = field(default_factory=list)


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5



class ConfigManager:
    """配置管理器 - 支持 YAML + .env 混合配置"""

    def __init__(self, yaml_config_file: str = None, env_file: str = None):
        """
        初始化配置管理器
        
        Args:
            yaml_config_file: YAML配置文件路径，默认为 config/config.yaml
            env_file: .env文件路径，默认为 .env
        """
        # 设置配置文件路径
        self.yaml_config_file = yaml_config_file or "config/config.yaml"
        self.env_file = env_file or ".env"
        
        # 初始化配置对象
        self._bot_config = None
        self._analysis_config = None
        self._proxy_config = None
        self._capump_config = None
        self._jupiter_config = None
        self._permissions_config = None
        self._logging_config = None
        self._logger = None
        
        # 加载配置
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
        """加载配置 - 先加载YAML，再用环境变量覆盖"""
        try:
            # 1. 加载 .env 文件
            self._load_env_file()
            
            # 2. 加载 YAML 配置文件
            self._load_yaml_config()
            
            # 3. 用环境变量覆盖配置
            self._override_with_env()
            
            self.logger.info("✅ 配置加载完成")
            
        except Exception as e:
            self.logger.exception(f"❌ 配置加载失败: {e}")
            self._load_defaults()

    def _load_env_file(self):
        """加载 .env 文件"""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
            self.logger.info(f"✅ 已加载环境变量文件: {self.env_file}")
        else:
            self.logger.warning(f"⚠️ 环境变量文件不存在: {self.env_file}")

    def _load_yaml_config(self):
        """加载 YAML 配置文件"""
        if os.path.exists(self.yaml_config_file):
            try:
                with open(self.yaml_config_file, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f)
                
                # 创建配置对象
                self._create_config_objects(yaml_data)
                self.logger.info(f"✅ 已加载YAML配置文件: {self.yaml_config_file}")
                
            except Exception as e:
                self.logger.exception(f"❌ YAML配置文件加载失败: {e}")
                self._load_defaults()
        else:
            self.logger.warning(f"⚠️ YAML配置文件不存在: {self.yaml_config_file}")
            self._load_defaults()

    def _create_config_objects(self, yaml_data: dict):
        """根据YAML数据创建配置对象"""
        # Bot配置（需要从环境变量获取敏感信息）
        bot_data = yaml_data.get('bot', {})
        self._bot_config = BotConfig(
            telegram_token=os.getenv('TELEGRAM_TOKEN', 'YOUR_BOT_TOKEN_HERE'),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID', 'YOUR_CHAT_ID_HERE'),
            message_thread_id=int(os.getenv('MESSAGE_THREAD_ID')) if os.getenv('MESSAGE_THREAD_ID') else None,
            interval=bot_data.get('interval', 58),
            threshold=bot_data.get('threshold', 0.05),
            min_market_cap=bot_data.get('min_market_cap', 0),
            min_age_days=bot_data.get('min_age_days', 10)
        )
        
        # 分析配置
        analysis_data = yaml_data.get('analysis', {})
        self._analysis_config = AnalysisConfig(
            top_holders_count=analysis_data.get('top_holders_count', 100),
            ranking_size=analysis_data.get('ranking_size', 30),
            detail_buttons_count=analysis_data.get('detail_buttons_count', 30),
            cluster_min_common_tokens=analysis_data.get('cluster_min_common_tokens', 2),
            cluster_min_addresses=analysis_data.get('cluster_min_addresses', 2),
            cluster_max_addresses=analysis_data.get('cluster_max_addresses', 50),
            clusters_per_page=analysis_data.get('clusters_per_page', 3),
            max_concurrent_threads=analysis_data.get('max_concurrent_threads', 5),
            known_pool_addresses=analysis_data.get('known_pool_addresses', ["5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"])
        )
        
        # 代理配置
        proxy_data = yaml_data.get('proxy', {})
        self._proxy_config = ProxyConfig(
            enabled=proxy_data.get('enabled', False),
            http_proxy=proxy_data.get('http_proxy', 'http://127.0.0.1:10808'),
            https_proxy=proxy_data.get('https_proxy', 'http://127.0.0.1:10808')
        )
        
        # Capump配置
        capump_data = yaml_data.get('capump', {})
        self._capump_config = CapumpConfig(
            interval=capump_data.get('interval', 120),
            threshold=capump_data.get('threshold', 0.10),
            min_market_cap=capump_data.get('min_market_cap', 50000),
            min_age_days=capump_data.get('min_age_days', 1),
            auto_analysis_enabled=capump_data.get('auto_analysis_enabled', False),
            max_tokens_per_batch=capump_data.get('max_tokens_per_batch', 10),
            analysis_timeout=capump_data.get('analysis_timeout', 180),
            notification_enabled=capump_data.get('notification_enabled', True)
        )
        
        # Jupiter配置
        jupiter_data = yaml_data.get('jupiter', {})
        self._jupiter_config = JupiterConfig(
            max_mcap=jupiter_data.get('max_mcap', 1000000),
            min_token_age=jupiter_data.get('min_token_age', 3600),
            has_socials=jupiter_data.get('has_socials', True),
            period=jupiter_data.get('period', '24h'),
            max_tokens_per_analysis=jupiter_data.get('max_tokens_per_analysis', 50),
            default_token_count=jupiter_data.get('default_token_count', 10)
        )
        
        # 权限配置
        permissions_data = yaml_data.get('permissions', {})
        self._permissions_config = PermissionsConfig(
            ca1_allowed_groups=permissions_data.get('ca1_allowed_groups', []),
            allowed_users=self._parse_comma_separated(os.getenv('ALLOWED_USERS')) or permissions_data.get('allowed_users', []),
            allowed_chats=self._parse_comma_separated(os.getenv('ALLOWED_CHATS')) or permissions_data.get('allowed_chats', [])
        )
        
        # 日志配置
        logging_data = yaml_data.get('logging', {})
        self._logging_config = LoggingConfig(
            level=os.getenv('LOG_LEVEL') or logging_data.get('level', 'INFO'),
            max_file_size=logging_data.get('max_file_size', 10485760),
            backup_count=logging_data.get('backup_count', 5)
        )

    def _override_with_env(self):
        """用环境变量覆盖配置"""
        # 覆盖代理配置
        if os.getenv('PROXY_ENABLED') is not None:
            self._proxy_config.enabled = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
        if os.getenv('HTTP_PROXY'):
            self._proxy_config.http_proxy = os.getenv('HTTP_PROXY')
        if os.getenv('HTTPS_PROXY'):
            self._proxy_config.https_proxy = os.getenv('HTTPS_PROXY')
        
        # 覆盖分析配置
        if os.getenv('TOP_HOLDERS_COUNT'):
            self._analysis_config.top_holders_count = int(os.getenv('TOP_HOLDERS_COUNT'))
        if os.getenv('RANKING_SIZE'):
            self._analysis_config.ranking_size = int(os.getenv('RANKING_SIZE'))
        if os.getenv('DETAIL_BUTTONS_COUNT'):
            self._analysis_config.detail_buttons_count = int(os.getenv('DETAIL_BUTTONS_COUNT'))
        
        # 覆盖Capump配置
        if os.getenv('CAPUMP_AUTO_ANALYSIS'):
            self._capump_config.auto_analysis_enabled = os.getenv('CAPUMP_AUTO_ANALYSIS', 'false').lower() == 'true'
        if os.getenv('CAPUMP_MIN_MARKET_CAP'):
            self._capump_config.min_market_cap = float(os.getenv('CAPUMP_MIN_MARKET_CAP'))
        
        # 覆盖Jupiter配置
        if os.getenv('JUPITER_MAX_MCAP'):
            self._jupiter_config.max_mcap = int(os.getenv('JUPITER_MAX_MCAP'))
        if os.getenv('JUPITER_DEFAULT_TOKEN_COUNT'):
            self._jupiter_config.default_token_count = int(os.getenv('JUPITER_DEFAULT_TOKEN_COUNT'))

    def _parse_comma_separated(self, value: str) -> List[str]:
        """解析逗号分隔的字符串为列表"""
        if not value:
            return []
        return [item.strip() for item in value.split(',') if item.strip()]

    def _load_defaults(self):
        """加载默认配置"""
        self._bot_config = BotConfig(
            telegram_token=os.getenv('TELEGRAM_TOKEN', 'YOUR_BOT_TOKEN_HERE'),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID', 'YOUR_CHAT_ID_HERE'),
            message_thread_id=int(os.getenv('MESSAGE_THREAD_ID')) if os.getenv('MESSAGE_THREAD_ID') else None
        )
        self._analysis_config = AnalysisConfig()
        self._proxy_config = ProxyConfig()
        self._capump_config = CapumpConfig()
        self._jupiter_config = JupiterConfig()
        self._permissions_config = PermissionsConfig()
        self._logging_config = LoggingConfig()

    def save_yaml_config(self):
        """保存配置到YAML文件（不包含敏感信息）"""
        config_data = {
            'bot': {
                'interval': self._bot_config.interval,
                'threshold': self._bot_config.threshold,
                'min_market_cap': self._bot_config.min_market_cap,
                'min_age_days': self._bot_config.min_age_days
            },
            'analysis': self._analysis_config.__dict__,
            'capump': self._capump_config.__dict__,
            'jupiter': self._jupiter_config.__dict__,
            'proxy': self._proxy_config.__dict__,
            'permissions': {
                'ca1_allowed_groups': self._permissions_config.ca1_allowed_groups,
                'allowed_users': [],  # 不保存用户权限到文件
                'allowed_chats': []   # 不保存聊天权限到文件
            },
            'logging': self._logging_config.__dict__
        }

        try:
            os.makedirs(os.path.dirname(self.yaml_config_file), exist_ok=True)
            with open(self.yaml_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, indent=2)
            self.logger.info(f"💾 YAML配置文件保存成功: {self.yaml_config_file}")
        except Exception as e:
            self.logger.exception(f"❌ YAML配置文件保存失败: {e}")

    # 配置属性访问器
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
    def permissions(self) -> PermissionsConfig:
        return self._permissions_config

    @property
    def logging(self) -> LoggingConfig:
        return self._logging_config

    # 兼容性属性（保持向后兼容）
    @property
    def ca1_allowed_groups(self) -> List[str]:
        """获取允许使用 /ca1 命令的群组列表"""
        return self._permissions_config.ca1_allowed_groups

    def update_config(self, section: str, **kwargs):
        """更新配置"""
        config_map = {
            'bot': self._bot_config,
            'analysis': self._analysis_config,
            'capump': self._capump_config,
            'jupiter': self._jupiter_config,
            'proxy': self._proxy_config,
            'permissions': self._permissions_config,
            'logging': self._logging_config
        }
        
        if section in config_map:
            config_obj = config_map[section]
            for key, value in kwargs.items():
                if hasattr(config_obj, key):
                    setattr(config_obj, key, value)
            self.save_yaml_config()
        else:
            self.logger.warning(f"⚠️ 未知的配置段: {section}")

    def add_known_pool_address(self, address: str):
        """添加已知的池子地址"""
        if address not in self._analysis_config.known_pool_addresses:
            self._analysis_config.known_pool_addresses.append(address)
            self.save_yaml_config()
            self.logger.info(f"✅ 已添加池子地址: {address}")
            return True
        else:
            self.logger.info(f"⚠️ 池子地址已存在: {address}")
            return False
    
    def remove_known_pool_address(self, address: str):
        """移除已知的池子地址"""
        if address in self._analysis_config.known_pool_addresses:
            self._analysis_config.known_pool_addresses.remove(address)
            self.save_yaml_config()
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
