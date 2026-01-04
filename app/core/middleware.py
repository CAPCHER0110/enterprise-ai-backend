"""
中间件 - 请求追踪、日志、性能监控
"""
import time
import uuid
import threading
from typing import Callable, Optional, Dict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.logging import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """添加请求ID到每个请求"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        from app.core.logging import set_request_context, clear_request_context
        
        # 生成或获取请求ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 设置日志上下文
        set_request_context(request_id=request_id)
        
        try:
            # 将请求ID添加到响应头
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # 清除日志上下文
            clear_request_context()


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")
        
        # 记录请求信息
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown"
            }
        )
        
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time
                }
            )
            
            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "error": str(e)
                },
                exc_info=True
            )
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    线程安全的指标收集中间件
    
    使用锁保护计数器操作，支持高并发场景
    """
    
    _instance: Optional['MetricsMiddleware'] = None
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._lock = threading.Lock()
        self._request_count = 0
        self._error_count = 0
        self._total_time = 0.0
        self._path_metrics: Dict[str, Dict[str, float]] = {}
        # 保存实例以便外部访问
        MetricsMiddleware._instance = self
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        path = request.url.path
        
        with self._lock:
            self._request_count += 1
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            with self._lock:
                self._total_time += process_time
                if response.status_code >= 400:
                    self._error_count += 1
                
                # 按路径统计
                if path not in self._path_metrics:
                    self._path_metrics[path] = {"count": 0, "errors": 0, "total_time": 0.0}
                self._path_metrics[path]["count"] += 1
                self._path_metrics[path]["total_time"] += process_time
                if response.status_code >= 400:
                    self._path_metrics[path]["errors"] += 1
            
            return response
        except Exception:
            process_time = time.time() - start_time
            with self._lock:
                self._error_count += 1
                self._total_time += process_time
            raise
    
    def get_metrics(self) -> dict:
        """获取指标（线程安全）"""
        with self._lock:
            avg_time = self._total_time / self._request_count if self._request_count > 0 else 0
            error_rate = self._error_count / self._request_count if self._request_count > 0 else 0
            
            return {
                "total_requests": self._request_count,
                "total_errors": self._error_count,
                "error_rate": round(error_rate, 4),
                "avg_process_time": round(avg_time, 4),
                "paths": {
                    path: {
                        "count": m["count"],
                        "errors": m["errors"],
                        "avg_time": round(m["total_time"] / m["count"], 4) if m["count"] > 0 else 0
                    }
                    for path, m in self._path_metrics.items()
                }
            }
    
    def reset_metrics(self) -> None:
        """重置指标（用于测试）"""
        with self._lock:
            self._request_count = 0
            self._error_count = 0
            self._total_time = 0.0
            self._path_metrics.clear()

