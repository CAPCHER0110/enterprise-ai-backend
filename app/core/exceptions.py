"""
自定义异常和异常处理器

提供统一的异常处理机制和自定义异常类型
"""
from typing import Any, Optional, Dict
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.logging import logger
from app.core.config import settings


class AppException(Exception):
    """
    应用自定义异常基类
    
    所有自定义异常都应继承此类
    """
    def __init__(
        self, 
        message: str, 
        code: str = "app_error", 
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "error": self.message,
            "code": self.code
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationException(AppException):
    """验证异常 - 用于请求参数验证失败"""
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, code="validation_error", status_code=400, details=details)


class ConnectionException(AppException):
    """连接异常 - 用于外部服务连接失败"""
    def __init__(self, message: str, service: str = "unknown"):
        super().__init__(
            f"Connection to {service} failed: {message}",
            code="connection_error",
            status_code=503,
            details={"service": service}
        )
        self.service = service


class AuthenticationException(AppException):
    """认证异常 - 用于身份验证失败"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, code="authentication_error", status_code=401)


class AuthorizationException(AppException):
    """授权异常 - 用于权限不足"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, code="authorization_error", status_code=403)


class RateLimitException(AppException):
    """速率限制异常 - 用于请求过于频繁"""
    def __init__(self, message: str = "Too many requests", retry_after: int = 60):
        super().__init__(
            message, 
            code="rate_limit_exceeded", 
            status_code=429,
            details={"retry_after": retry_after}
        )
        self.retry_after = retry_after


class ResourceNotFoundException(AppException):
    """资源未找到异常"""
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(
            message, 
            code="not_found", 
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class ServiceUnavailableException(AppException):
    """服务不可用异常"""
    def __init__(self, service: str, message: Optional[str] = None):
        msg = f"Service '{service}' is temporarily unavailable"
        if message:
            msg = f"{msg}: {message}"
        super().__init__(
            msg, 
            code="service_unavailable", 
            status_code=503,
            details={"service": service}
        )


def add_exception_handlers(app: FastAPI) -> None:
    """注册异常处理器"""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理HTTP异常"""
        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={"path": request.url.path, "status_code": exc.status_code}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "code": "http_error",
                "path": str(request.url.path)
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证错误"""
        errors = exc.errors()
        # 简化错误信息用于日志
        error_summary = [f"{e.get('loc', ['unknown'])[-1]}: {e.get('msg', 'invalid')}" for e in errors[:3]]
        logger.warning(
            f"Validation error: {', '.join(error_summary)}",
            extra={"path": request.url.path, "errors_count": len(errors)}
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation failed",
                "code": "validation_error",
                "details": errors,
                "path": str(request.url.path)
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """处理值错误"""
        logger.warning(
            f"Value error: {str(exc)}",
            extra={"path": request.url.path}
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": str(exc),
                "code": "validation_error",
                "path": str(request.url.path)
            },
        )
    
    @app.exception_handler(RateLimitException)
    async def rate_limit_exception_handler(request: Request, exc: RateLimitException):
        """处理速率限制异常"""
        logger.warning(
            f"Rate limit exceeded",
            extra={"path": request.url.path, "retry_after": exc.retry_after}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict() | {"path": str(request.url.path)},
            headers={"Retry-After": str(exc.retry_after)}
        )
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """处理应用自定义异常"""
        log_level = logger.error if exc.status_code >= 500 else logger.warning
        log_level(
            f"App exception [{exc.code}]: {exc.message}",
            extra={"path": request.url.path, "status_code": exc.status_code}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict() | {"path": str(request.url.path)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理所有未捕获的异常"""
        # 获取请求ID用于关联
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            exc_info=True,
            extra={
                "path": request.url.path,
                "request_id": request_id,
                "exception_type": type(exc).__name__
            }
        )
        
        # 生产环境不暴露详细错误信息
        error_message = "Internal Server Error"
        if settings.LOG_LEVEL.upper() == "DEBUG":
            error_message = f"{type(exc).__name__}: {str(exc)}"
        
        return JSONResponse(
            status_code=500,
            content={
                "error": error_message,
                "code": "server_error",
                "path": str(request.url.path),
                "request_id": request_id
            },
        )