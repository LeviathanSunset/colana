"""
代币大户分析Bot - 日志管理模块
统一管理项目的日志输出，支持文件和控制台双输出
"""

import os
import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler


class BotLogger:
    """机器人日志管理器"""
    
    def __init__(self, name: str = "colana_bot", log_dir: str = None):
        """
        初始化日志管理器
        
        Args:
            name: 日志名称
            log_dir: 日志目录，默认为 storage/logs
        """
        self.name = name
        
        # 设置日志目录
        if log_dir is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            self.log_dir = project_root / "storage" / "logs"
        else:
            self.log_dir = Path(log_dir)
        
        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 创建格式器
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 主日志文件处理器（所有级别）
        main_log_file = self.log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log"
        main_handler = RotatingFileHandler(
            filename=str(main_log_file),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(formatter)
        self.logger.addHandler(main_handler)
        
        # 错误日志文件处理器（仅错误和严重错误）
        error_log_file = self.log_dir / f"{self.name}_error_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = RotatingFileHandler(
            filename=str(error_log_file),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """异常日志（包含堆栈信息）"""
        self.logger.exception(message, **kwargs)


class ModuleLogger:
    """模块专用日志管理器"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, module_name: str) -> BotLogger:
        """
        获取模块专用的日志器
        
        Args:
            module_name: 模块名称
            
        Returns:
            BotLogger实例
        """
        if module_name not in cls._loggers:
            cls._loggers[module_name] = BotLogger(name=module_name)
        return cls._loggers[module_name]


# 便捷函数
def get_logger(module_name: str = None) -> BotLogger:
    """
    获取日志器的便捷函数
    
    Args:
        module_name: 模块名称，如果不提供则使用调用者的模块名
    
    Returns:
        BotLogger实例
    """
    if module_name is None:
        # 自动获取调用者的模块名
        import inspect
        frame = inspect.currentframe().f_back
        module_name = frame.f_globals.get('__name__', 'unknown')
        # 简化模块名
        if module_name.startswith('src.'):
            module_name = module_name[4:]  # 去掉 'src.' 前缀
        module_name = module_name.replace('.', '_')
    
    return ModuleLogger.get_logger(module_name)


# 为向后兼容保留的实例
main_logger = get_logger("main")
crawler_logger = get_logger("crawler")
analysis_logger = get_logger("analysis")
telegram_logger = get_logger("telegram")
