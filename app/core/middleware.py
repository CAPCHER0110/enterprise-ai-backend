"""
中间件模块 - 请求追踪、日志、性能监控、速率限制、请求验证

统一的中间件模块，包含所有 HTTP 中间件实现
"""
import time
import uuid
import threading
from typing import Callable, Optional, Dict, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import JSONResponse
from app.core.logging import logger
from app.core.config import settings


# =============================================================================
# 请求追踪中间件
# =============================================================================

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


# =============================================================================
# 请求验证中间件
# =============================================================================

class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    请求体大小限制中间件
    
    限制请求体大小，防止大文件攻击
    """
    
    # 默认最大请求体大小：10MB
    DEFAULT_MAX_SIZE = 10 * 1024 * 1024
    
    # 文件上传路径的最大大小：100MB
    UPLOAD_MAX_SIZE = 100 * 1024 * 1024
    
    # 文件上传路径模式
    UPLOAD_PATHS = ["/api/v1/ingest/upload"]
    
    def __init__(self, app: ASGIApp, max_size: int = DEFAULT_MAX_SIZE):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 确定此请求的最大大小
        path = request.url.path
        max_size = self.max_size
        
        # 文件上传路径使用更大的限制
        for upload_path in self.UPLOAD_PATHS:
            if path.startswith(upload_path):
                max_size = self.UPLOAD_MAX_SIZE
                break
        
        # 检查Content-Length头
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > max_size:
                    logger.warning(
                        f"Request body too large: {length} bytes (max: {max_size})",
                        extra={"path": path, "content_length": length}
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request body too large",
                            "code": "payload_too_large",
                            "max_size": max_size,
                            "received_size": length
                        }
                    )
            except ValueError:
                pass
        
        return await call_next(request)


class ContentTypeMiddleware(BaseHTTPMiddleware):
    """
    内容类型验证中间件
    
    验证POST/PUT请求的Content-Type
    """
    
    # 需要验证Content-Type的方法
    METHODS_REQUIRING_CONTENT_TYPE = {"POST", "PUT", "PATCH"}
    
    # 排除的路径（如文件上传）
    EXCLUDED_PATHS = ["/api/v1/ingest/upload"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 只检查需要body的请求
        if request.method not in self.METHODS_REQUIRING_CONTENT_TYPE:
            return await call_next(request)
        
        # 排除特定路径
        path = request.url.path
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return await call_next(request)
        
        # 检查Content-Type
        content_type = request.headers.get("content-type", "")
        
        # 对于JSON API，要求application/json
        if not content_type.startswith("application/json"):
            # 如果有body但没有正确的content-type
            content_length = request.headers.get("content-length", "0")
            if content_length != "0":
                logger.debug(
                    f"Non-JSON content type for {path}: {content_type}"
                )
        
        return await call_next(request)


# =============================================================================
# 速率限制中间件
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app: ASGIApp, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        
        # 配置默认规则
        if self.enabled:
            from app.core.rate_limiter import rate_limiter
            rate_limiter.set_default_rule(
                requests=getattr(settings, 'RATE_LIMIT_REQUESTS', 100),
                window=getattr(settings, 'RATE_LIMIT_WINDOW', 60)
            )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        from app.core.rate_limiter import rate_limiter
        
        # 如果未启用或是健康检查端点，跳过限流
        if not self.enabled or request.url.path in ["/health", "/metrics", "/live", "/ready"]:
            return await call_next(request)
        
        # 获取客户端标识（优先级：API Key > IP地址）
        client_id = self._get_client_id(request)
        
        # 检查速率限制
        is_allowed, retry_after = rate_limiter.is_allowed(client_id)
        
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {client_id} on {request.url.path}",
                extra={
                    "client_id": client_id,
                    "path": request.url.path,
                    "retry_after": retry_after
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "code": "rate_limit_exceeded",
                    "retry_after": retry_after,
                    "message": f"Rate limit exceeded. Please retry after {retry_after} seconds."
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(getattr(settings, 'RATE_LIMIT_REQUESTS', 100)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after)
                }
            )
        
        # 添加速率限制头
        response = await call_next(request)
        
        # 获取剩余请求数
        remaining = rate_limiter.get_remaining(client_id)
        
        response.headers["X-RateLimit-Limit"] = str(getattr(settings, 'RATE_LIMIT_REQUESTS', 100))
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(getattr(settings, 'RATE_LIMIT_WINDOW', 60))
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用API Key
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        if api_key:
            return f"key:{api_key[:8]}"  # 只使用前8个字符
        
        # 使用IP地址
        client_ip = request.client.host if request.client else "unknown"
        
        # 检查X-Forwarded-For头（如果在代理后面）
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"


# =============================================================================
# 日志中间件
# =============================================================================

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


# =============================================================================
# 指标收集中间件
# =============================================================================

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


# =============================================================================
# 导出所有中间件
# =============================================================================

__all__ = [
    "RequestIDMiddleware",
    "RequestSizeMiddleware",
    "ContentTypeMiddleware",
    "RateLimitMiddleware",
    "LoggingMiddleware",
    "MetricsMiddleware",
]
