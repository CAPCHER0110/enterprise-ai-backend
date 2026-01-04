"""
日志配置模块

提供结构化日志记录，支持JSON格式（生产环境）和易读格式（开发环境）
"""
import logging
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar

# 请求上下文变量（用于跟踪请求ID等）
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


class ContextFilter(logging.Filter):
    """
    上下文过滤器
    
    自动添加请求ID和会话ID到日志记录
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        record.session_id = session_id_var.get() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON格式的日志格式化器
    
    生产环境使用，便于日志聚合和分析
    """
    
    # 需要排除的标准字段
    RESERVED_ATTRS = frozenset([
        'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
        'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs',
        'message', 'msg', 'name', 'pathname', 'process', 'processName',
        'relativeCreated', 'stack_info', 'thread', 'threadName',
        'request_id', 'session_id'
    ])
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加上下文信息
        if hasattr(record, 'request_id') and record.request_id != "-":
            log_data["request_id"] = record.request_id
        if hasattr(record, 'session_id') and record.session_id != "-":
            log_data["session_id"] = record.session_id
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # 添加extra字段（排除标准字段）
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith('_'):
                try:
                    # 尝试序列化，失败则转为字符串
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """
    带颜色的日志格式化器（开发环境使用）
    """
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def __init__(self, fmt: Optional[str] = None):
        super().__init__(fmt or self._default_format())
    
    def _default_format(self) -> str:
        return (
            "%(asctime)s | %(levelname)-8s | "
            "%(name)s:%(funcName)s:%(lineno)d | "
            "[%(request_id)s] %(message)s"
        )
    
    def format(self, record: logging.LogRecord) -> str:
        # 确保有request_id属性
        if not hasattr(record, 'request_id'):
            record.request_id = '-'
        
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        result = super().format(record)
        
        # 恢复原始levelname
        record.levelname = levelname
        
        return result


def setup_logging() -> logging.Logger:
    """
    配置应用程序日志
    
    - 生产环境（INFO/WARNING/ERROR）使用JSON格式
    - 开发环境（DEBUG）使用带颜色的易读格式
    
    Returns:
        应用日志记录器
    """
    # 延迟导入避免循环依赖
    from app.core.config import settings
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # 根据环境选择日志格式
    use_json = log_level > logging.DEBUG
    
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter()
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ContextFilter())  # 添加上下文过滤器
    root_logger.addHandler(console_handler)
    
    # 设置外部库的日志级别（减少噪音）
    _configure_external_loggers()
    
    # 应用特定的日志记录器
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    
    return app_logger


def _configure_external_loggers() -> None:
    """配置外部库的日志级别"""
    external_loggers = {
        "uvicorn.access": logging.WARNING,
        "uvicorn.error": logging.INFO,
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        "openai": logging.WARNING,
        "anthropic": logging.WARNING,
        "llama_index": logging.INFO,
        "chromadb": logging.WARNING,
        "pinecone": logging.WARNING,
        "qdrant_client": logging.WARNING,
        "pymilvus": logging.WARNING,
        "redis": logging.WARNING,
    }
    
    for logger_name, level in external_loggers.items():
        logging.getLogger(logger_name).setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称（通常是模块名）
        
    Returns:
        配置好的Logger实例
    """
    return logging.getLogger(f"app.{name}")


def set_request_context(request_id: Optional[str] = None, session_id: Optional[str] = None) -> None:
    """
    设置请求上下文
    
    Args:
        request_id: 请求ID
        session_id: 会话ID
    """
    if request_id:
        request_id_var.set(request_id)
    if session_id:
        session_id_var.set(session_id)


def clear_request_context() -> None:
    """清除请求上下文"""
    request_id_var.set(None)
    session_id_var.set(None)


# 初始化全局日志记录器
logger = setup_logging()
