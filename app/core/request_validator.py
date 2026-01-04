"""
请求验证中间件

提供请求体大小限制和内容类型验证
"""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.logging import logger
from app.core.config import settings


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
    
    def __init__(self, app, max_size: int = DEFAULT_MAX_SIZE):
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

