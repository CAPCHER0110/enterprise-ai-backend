"""
速率限制中间件
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.rate_limiter import rate_limiter
from app.core.config import settings
from app.core.logging import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        
        # 配置默认规则
        if self.enabled:
            rate_limiter.set_default_rule(
                requests=getattr(settings, 'RATE_LIMIT_REQUESTS', 100),
                window=getattr(settings, 'RATE_LIMIT_WINDOW', 60)
            )
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 如果未启用或是健康检查端点，跳过限流
        if not self.enabled or request.url.path in ["/health", "/metrics"]:
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

