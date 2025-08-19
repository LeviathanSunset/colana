"""
代币大户分析Bot - 增强日志管理模块
统一管理项目的日志输出，支持文件和控制台双输出
包含详细的错误分类和解决方案提示
"""

import os
import logging
import sys
import traceback
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler


class ErrorClassifier:
    """错误分类器 - 提供详细的错误分析和解决方案"""
    
    ERROR_SOLUTIONS = {
        # 网络相关错误
        "ConnectionError": {
            "category": "网络连接",
            "description": "网络连接失败",
            "solutions": [
                "检查网络连接是否正常",
                "检查代理设置是否正确",
                "确认防火墙未阻止连接",
                "稍后重试或联系网络管理员"
            ],
            "prevention": "建议配置稳定的网络环境和备用代理"
        },
        "TimeoutError": {
            "category": "超时错误",
            "description": "请求超时",
            "solutions": [
                "增加超时时间设置",
                "检查网络速度",
                "减少并发请求数量",
                "稍后重试"
            ],
            "prevention": "合理设置超时参数，避免过高的并发请求"
        },
        "HTTPError": {
            "category": "HTTP请求",
            "description": "HTTP请求失败",
            "solutions": [
                "检查API密钥是否有效",
                "确认请求参数格式正确",
                "检查API接口是否正常",
                "查看HTTP状态码确定具体问题"
            ],
            "prevention": "定期检查API状态，实现请求重试机制"
        },
        
        # API相关错误
        "APIError": {
            "category": "API调用",
            "description": "API调用失败",
            "solutions": [
                "检查API密钥配置",
                "确认API调用频率限制",
                "检查请求参数是否正确",
                "查看API文档确认接口变更"
            ],
            "prevention": "实现API调用限流和错误重试机制"
        },
        "RateLimitError": {
            "category": "频率限制",
            "description": "API调用频率超限",
            "solutions": [
                "降低请求频率",
                "实现请求队列机制",
                "使用多个API密钥轮换",
                "等待限制重置后重试"
            ],
            "prevention": "合理控制API调用频率，实现智能限流"
        },
        
        # 数据相关错误
        "DataNotFoundError": {
            "category": "数据获取",
            "description": "未找到数据",
            "solutions": [
                "检查代币地址是否正确",
                "确认代币是否存在",
                "检查数据源是否正常",
                "尝试其他数据源"
            ],
            "prevention": "实现数据验证和多数据源备份"
        },
        "ParseError": {
            "category": "数据解析",
            "description": "数据解析失败",
            "solutions": [
                "检查数据格式是否正确",
                "确认API响应结构未变更",
                "增加数据验证逻辑",
                "联系数据提供方确认"
            ],
            "prevention": "实现健壮的数据解析和验证机制"
        },
        
        # 配置相关错误
        "ConfigError": {
            "category": "配置错误",
            "description": "配置文件错误",
            "solutions": [
                "检查配置文件格式",
                "确认必需配置项是否填写",
                "参考config.example.json示例",
                "重新生成配置文件"
            ],
            "prevention": "使用配置验证和默认值机制"
        },
        "AuthenticationError": {
            "category": "身份验证",
            "description": "身份验证失败",
            "solutions": [
                "检查Telegram Bot Token",
                "确认Token格式正确",
                "验证Bot是否已激活",
                "重新创建Bot并更新Token"
            ],
            "prevention": "定期检查Token有效性"
        },
        
        # 系统相关错误
        "FileNotFoundError": {
            "category": "文件系统",
            "description": "文件未找到",
            "solutions": [
                "检查文件路径是否正确",
                "确认文件是否存在",
                "检查文件权限",
                "重新创建缺失文件"
            ],
            "prevention": "实现文件存在性检查和自动创建机制"
        },
        "PermissionError": {
            "category": "权限错误",
            "description": "文件权限不足",
            "solutions": [
                "检查文件和目录权限",
                "使用sudo运行（如适用）",
                "修改文件所有者",
                "检查磁盘空间"
            ],
            "prevention": "正确设置文件和目录权限"
        },
        "MemoryError": {
            "category": "内存错误",
            "description": "内存不足",
            "solutions": [
                "减少并发处理数量",
                "优化数据处理逻辑",
                "增加系统内存",
                "实现数据分批处理"
            ],
            "prevention": "优化内存使用，实现资源监控"
        }
    }
    
    @classmethod
    def classify_error(cls, error: Exception) -> Dict[str, Any]:
        """
        分类错误并提供解决方案
        
        Args:
            error: 异常对象
            
        Returns:
            包含错误信息和解决方案的字典
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # 特殊错误类型处理
        if "timeout" in error_message.lower():
            error_type = "TimeoutError"
        elif "connection" in error_message.lower():
            error_type = "ConnectionError"
        elif "rate limit" in error_message.lower():
            error_type = "RateLimitError"
        elif "not found" in error_message.lower():
            error_type = "DataNotFoundError"
        elif "parse" in error_message.lower() or "json" in error_message.lower():
            error_type = "ParseError"
        elif "config" in error_message.lower():
            error_type = "ConfigError"
        elif "auth" in error_message.lower() or "token" in error_message.lower():
            error_type = "AuthenticationError"
        
        solution_info = cls.ERROR_SOLUTIONS.get(error_type, {
            "category": "未知错误",
            "description": "未分类的错误",
            "solutions": [
                "检查错误日志获取详细信息",
                "查看系统资源使用情况",
                "尝试重启服务",
                "联系技术支持"
            ],
            "prevention": "实现更详细的错误处理和监控"
        })
        
        return {
            "error_type": error_type,
            "error_message": error_message,
            "category": solution_info["category"],
            "description": solution_info["description"],
            "solutions": solution_info["solutions"],
            "prevention": solution_info["prevention"],
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc()
        }


class BotLogger:
    """增强的机器人日志管理器"""
    
    def __init__(self, name: str = "colana_bot", log_dir: str = None):
        """
        初始化日志管理器
        
        Args:
            name: 日志名称
            log_dir: 日志目录，默认为 storage/logs
        """
        self.name = name
        self.error_classifier = ErrorClassifier()
        
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
        
        # 解决方案日志处理器（用于记录错误解决方案）
        solution_log_file = self.log_dir / f"{self.name}_solutions_{datetime.now().strftime('%Y%m%d')}.log"
        solution_handler = RotatingFileHandler(
            filename=str(solution_log_file),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        solution_handler.setLevel(logging.WARNING)
        
        # 解决方案专用格式器
        solution_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - SOLUTION - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        solution_handler.setFormatter(solution_formatter)
        solution_handler.addFilter(lambda record: hasattr(record, 'is_solution'))
        self.logger.addHandler(solution_handler)
    
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
    
    def error_with_solution(self, error: Exception, context: str = "", **kwargs):
        """
        记录错误并提供解决方案
        
        Args:
            error: 异常对象
            context: 错误上下文信息
        """
        # 分类错误并获取解决方案
        error_info = self.error_classifier.classify_error(error)
        
        # 记录基础错误信息
        error_msg = f"❌ {context}: {error_info['error_message']}"
        self.logger.error(error_msg, **kwargs)
        
        # 记录详细解决方案
        solution_msg = self._format_solution_message(error_info, context)
        
        # 创建解决方案记录
        solution_record = logging.LogRecord(
            name=self.logger.name,
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg=solution_msg,
            args=(),
            exc_info=None
        )
        solution_record.is_solution = True
        
        self.logger.handle(solution_record)
        
        # 同时在控制台显示简化的解决方案
        print(f"\n🔧 错误解决建议:")
        print(f"   类别: {error_info['category']}")
        print(f"   描述: {error_info['description']}")
        print(f"   解决方案:")
        for i, solution in enumerate(error_info['solutions'][:3], 1):
            print(f"   {i}. {solution}")
        if len(error_info['solutions']) > 3:
            print(f"   ... 更多解决方案请查看日志文件")
        print(f"   预防措施: {error_info['prevention']}\n")
        
        return error_info
    
    def _format_solution_message(self, error_info: Dict[str, Any], context: str) -> str:
        """格式化解决方案消息"""
        solution_data = {
            "context": context,
            "error_classification": {
                "type": error_info["error_type"],
                "category": error_info["category"],
                "description": error_info["description"],
                "message": error_info["error_message"]
            },
            "solutions": error_info["solutions"],
            "prevention": error_info["prevention"],
            "timestamp": error_info["timestamp"],
            "traceback": error_info["traceback"]
        }
        
        return json.dumps(solution_data, ensure_ascii=False, indent=2)
    
    def log_performance(self, operation: str, duration: float, details: Dict[str, Any] = None):
        """
        记录性能信息
        
        Args:
            operation: 操作名称
            duration: 耗时（秒）
            details: 详细信息
        """
        performance_info = {
            "operation": operation,
            "duration_seconds": round(duration, 3),
            "timestamp": datetime.now().isoformat()
        }
        
        if details:
            performance_info["details"] = details
        
        if duration > 10:  # 超过10秒的操作记录为警告
            self.warning(f"⚠️ 性能警告: {operation} 耗时 {duration:.2f}s - {json.dumps(performance_info, ensure_ascii=False)}")
        elif duration > 60:  # 超过1分钟的操作记录为错误
            self.error(f"🐌 性能问题: {operation} 耗时 {duration:.2f}s - {json.dumps(performance_info, ensure_ascii=False)}")
        else:
            self.info(f"⏱️ 性能: {operation} 耗时 {duration:.2f}s")
    
    def log_api_call(self, api_name: str, success: bool, response_time: float = None, error: Exception = None):
        """
        记录API调用信息
        
        Args:
            api_name: API名称
            success: 是否成功
            response_time: 响应时间
            error: 错误信息（如果失败）
        """
        api_info = {
            "api": api_name,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        if response_time is not None:
            api_info["response_time"] = round(response_time, 3)
        
        if success:
            self.info(f"✅ API调用成功: {api_name} ({response_time:.3f}s)" if response_time else f"✅ API调用成功: {api_name}")
        else:
            self.error(f"❌ API调用失败: {api_name}")
            if error:
                self.error_with_solution(error, f"API调用失败 - {api_name}")


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
