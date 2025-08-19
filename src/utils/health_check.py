"""
健康检查模块
提供HTTP健康检查端点，用于监控Bot运行状态
"""

import time
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from ..utils.logger import get_logger


class HealthStatus:
    """健康状态管理类"""
    
    def __init__(self):
        self.logger = get_logger("health")
        self.start_time = time.time()
        self.last_heartbeat = time.time()
        self.stats = {
            "requests_total": 0,
            "errors_total": 0,
            "api_calls_total": 0,
            "analysis_count": 0,
            "last_analysis_time": None,
            "active_threads": 0,
        }
        self.services_status = {
            "telegram_bot": {"status": "unknown", "last_check": None, "error": None},
            "okx_api": {"status": "unknown", "last_check": None, "error": None},
            "jupiter_api": {"status": "unknown", "last_check": None, "error": None},
            "crawler": {"status": "unknown", "last_check": None, "error": None},
        }
        
    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_heartbeat = time.time()
        
    def increment_stat(self, stat_name: str, value: int = 1):
        """增加统计计数"""
        if stat_name in self.stats:
            self.stats[stat_name] += value
            
    def update_service_status(self, service: str, status: str, error: str = None):
        """更新服务状态"""
        if service in self.services_status:
            self.services_status[service] = {
                "status": status,
                "last_check": datetime.now().isoformat(),
                "error": error
            }
            
    def get_health_data(self):
        """获取健康状态数据"""
        uptime = time.time() - self.start_time
        time_since_heartbeat = time.time() - self.last_heartbeat
        
        # 判断整体健康状态
        overall_status = "healthy"
        if time_since_heartbeat > 300:  # 5分钟没有心跳
            overall_status = "unhealthy"
        elif any(service["status"] == "error" for service in self.services_status.values()):
            overall_status = "degraded"
            
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(uptime),
            "uptime_human": self._format_uptime(uptime),
            "last_heartbeat": datetime.fromtimestamp(self.last_heartbeat).isoformat(),
            "time_since_heartbeat": int(time_since_heartbeat),
            "stats": self.stats.copy(),
            "services": self.services_status.copy(),
            "system_info": {
                "active_threads": threading.active_count(),
                "python_version": self._get_python_version(),
            }
        }
        
    def _format_uptime(self, uptime_seconds):
        """格式化运行时间"""
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
            
    def _get_python_version(self):
        """获取Python版本"""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


class HealthCheckHandler(BaseHTTPRequestHandler):
    """健康检查HTTP处理器"""
    
    def __init__(self, *args, health_status=None, **kwargs):
        self.health_status = health_status
        super().__init__(*args, **kwargs)
        
    def do_GET(self):
        """处理GET请求"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            if path == "/health":
                self._handle_health_check()
            elif path == "/metrics":
                self._handle_metrics()
            elif path == "/status":
                self._handle_detailed_status()
            elif path == "/":
                self._handle_root()
            else:
                self._send_error(404, "Not Found")
                
        except Exception as e:
            self.health_status.logger.exception(f"健康检查请求处理失败: {e}")
            self._send_error(500, f"Internal Server Error: {str(e)}")
            
    def _handle_health_check(self):
        """处理基础健康检查"""
        health_data = self.health_status.get_health_data()
        status_code = 200 if health_data["status"] == "healthy" else 503
        
        response = {
            "status": health_data["status"],
            "timestamp": health_data["timestamp"],
            "uptime": health_data["uptime_human"]
        }
        
        self._send_json_response(response, status_code)
        
    def _handle_metrics(self):
        """处理指标查询"""
        health_data = self.health_status.get_health_data()
        
        # Prometheus风格的指标
        metrics = []
        for key, value in health_data["stats"].items():
            if isinstance(value, (int, float)):
                metrics.append(f"colana_bot_{key} {value}")
                
        metrics.append(f"colana_bot_uptime_seconds {health_data['uptime_seconds']}")
        metrics.append(f"colana_bot_active_threads {health_data['system_info']['active_threads']}")
        
        response = "\n".join(metrics) + "\n"
        self._send_response(response, "text/plain")
        
    def _handle_detailed_status(self):
        """处理详细状态查询"""
        health_data = self.health_status.get_health_data()
        self._send_json_response(health_data)
        
    def _handle_root(self):
        """处理根路径"""
        html = """
        <html>
        <head><title>Colana Bot Health Check</title></head>
        <body>
            <h1>Colana Bot Health Check</h1>
            <ul>
                <li><a href="/health">Basic Health Check</a></li>
                <li><a href="/status">Detailed Status</a></li>
                <li><a href="/metrics">Metrics</a></li>
            </ul>
        </body>
        </html>
        """
        self._send_response(html, "text/html")
        
    def _send_json_response(self, data, status_code=200):
        """发送JSON响应"""
        response = json.dumps(data, indent=2, ensure_ascii=False)
        self._send_response(response, "application/json", status_code)
        
    def _send_response(self, content, content_type="text/plain", status_code=200):
        """发送响应"""
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Content-length', str(len(content.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
        
    def _send_error(self, status_code, message):
        """发送错误响应"""
        error_response = {"error": message, "status_code": status_code}
        self._send_json_response(error_response, status_code)
        
    def log_message(self, format, *args):
        """重写日志方法，使用我们的logger"""
        if hasattr(self, 'health_status') and self.health_status:
            self.health_status.logger.debug(f"HTTP {format % args}")


# 全局健康状态实例
_health_status = HealthStatus()


def get_health_status() -> HealthStatus:
    """获取健康状态实例"""
    return _health_status


def start_health_server(port: int = 8080, host: str = "0.0.0.0"):
    """启动健康检查服务器"""
    logger = get_logger("health")
    
    try:
        # 创建自定义处理器
        def handler(*args, **kwargs):
            return HealthCheckHandler(*args, health_status=_health_status, **kwargs)
            
        server = HTTPServer((host, port), handler)
        logger.info(f"🏥 健康检查服务器启动在 http://{host}:{port}")
        logger.info(f"   - 健康检查: http://{host}:{port}/health")
        logger.info(f"   - 详细状态: http://{host}:{port}/status")
        logger.info(f"   - 指标: http://{host}:{port}/metrics")
        
        # 启动心跳
        def heartbeat_worker():
            while True:
                try:
                    _health_status.update_heartbeat()
                    time.sleep(30)  # 每30秒更新一次心跳
                except Exception as e:
                    logger.exception(f"心跳更新失败: {e}")
                    
        heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
        heartbeat_thread.start()
        
        # 运行服务器
        server.serve_forever()
        
    except Exception as e:
        logger.exception(f"❌ 健康检查服务器启动失败: {e}")
        raise


def update_service_status(service: str, status: str, error: str = None):
    """更新服务状态的便捷函数"""
    _health_status.update_service_status(service, status, error)


def increment_stat(stat_name: str, value: int = 1):
    """增加统计的便捷函数"""
    _health_status.increment_stat(stat_name, value)


# 装饰器：自动统计API调用
def track_api_call(service_name: str):
    """装饰器：跟踪API调用"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                increment_stat("api_calls_total")
                result = func(*args, **kwargs)
                update_service_status(service_name, "healthy")
                return result
            except Exception as e:
                increment_stat("errors_total")
                update_service_status(service_name, "error", str(e))
                raise
        return wrapper
    return decorator


# 装饰器：自动统计分析任务
def track_analysis(func):
    """装饰器：跟踪分析任务"""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            increment_stat("analysis_count")
            _health_status.stats["last_analysis_time"] = datetime.now().isoformat()
            return result
        except Exception as e:
            increment_stat("errors_total")
            raise
    return wrapper
