"""
Enterprise AI Backend - 主入口

生产级RAG后端服务，支持多种LLM、向量数据库和记忆方案
"""
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Union

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import add_exception_handlers
from app.core.middleware import (
    RequestIDMiddleware, 
    LoggingMiddleware, 
    MetricsMiddleware,
    RateLimitMiddleware,
    RequestSizeMiddleware
)
from app.core.connections import RedisConnectionPool
from app.core.config_validator import ConfigValidator
from app.core.shutdown import shutdown_manager, register_cleanup
from app.utils.llm_factory import init_settings, get_index
from app.api.v1 import chat, ingest, admin, llm, vector_store, memory


# ==================== 注册清理任务 ====================
@register_cleanup
async def cleanup_redis() -> None:
    """清理Redis连接"""
    await RedisConnectionPool.close()
    logger.info("✓ Redis connections closed")


@register_cleanup
async def cleanup_cache() -> None:
    """清理缓存"""
    from app.core.cache import cache
    cache.clear()
    logger.info("✓ Cache cleared")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    Startup:
        1. 验证配置
        2. 初始化LlamaIndex设置（LLM + Embedding）
        3. 初始化向量数据库连接
        4. 初始化Redis连接池
    
    Shutdown:
        1. 执行所有注册的清理任务
    """
    # ==================== Startup ====================
    logger.info("=" * 60)
    logger.info("Starting up Enterprise AI Brain...")
    logger.info(f"Version: 1.1.0 | Log Level: {settings.LOG_LEVEL}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER} | Model: {settings.LLM_MODEL_NAME}")
    logger.info(f"Vector Store: {settings.VECTOR_STORE_PROVIDER} | Memory: {settings.MEMORY_PROVIDER}")
    logger.info("=" * 60)
    
    startup_errors = []
    
    try:
        # 1. 验证配置
        ConfigValidator.validate()
        logger.info("✓ Configuration validated")
        
        # 2. 初始化 LlamaIndex 设置
        init_settings()
        logger.info("✓ LlamaIndex settings initialized")
        
        # 3. 初始化向量索引连接
        try:
            get_index()
            logger.info(f"✓ Vector store initialized ({settings.VECTOR_STORE_PROVIDER})")
        except Exception as e:
            startup_errors.append(f"Vector store: {e}")
            logger.error(f"✗ Vector store initialization failed: {e}")
        
        # 4. 初始化 Redis 连接池
        try:
            print("DEBUG: Starting Redis health check...")
            await RedisConnectionPool.health_check()

            logger.info("✓ Redis connection pool initialized")
        except Exception as e:
            startup_errors.append(f"Redis: {e}")
            logger.warning(f"⚠ Redis connection check failed: {e}")
        
        logger.info("=" * 60)
        if startup_errors:
            logger.warning(f"Enterprise AI Brain started with {len(startup_errors)} warning(s)")
            for err in startup_errors:
                logger.warning(f"  - {err}")
        else:
            logger.info("Enterprise AI Brain started successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        raise
    
    yield
    
    # ==================== Shutdown ====================
    logger.info("=" * 60)
    logger.info("Initiating graceful shutdown...")
    
    await shutdown_manager.shutdown()
    
    logger.info("Shutdown complete")
    logger.info("=" * 60)

# 初始化 FastAPI 应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise RAG Backend with Multi-LLM, Multi-VectorDB & Multi-Memory Support",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 添加中间件（顺序很重要 - 按添加顺序的逆序执行）
app.add_middleware(RequestIDMiddleware)  # 最先添加，确保所有请求都有ID
app.add_middleware(LoggingMiddleware)   # 记录请求日志
app.add_middleware(MetricsMiddleware)   # 收集指标
app.add_middleware(RequestSizeMiddleware)  # 请求大小限制
app.add_middleware(RateLimitMiddleware, enabled=settings.RATE_LIMIT_ENABLED)  # 速率限制

# 配置 CORS (允许前端跨域访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # 生产环境应设置为具体域名列表
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

# 注册路由
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["Chat"])
app.include_router(ingest.router, prefix=f"{settings.API_V1_STR}/ingest", tags=["Ingest"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin"])
app.include_router(llm.router, prefix=f"{settings.API_V1_STR}/llm", tags=["LLM"])
app.include_router(vector_store.router, prefix=f"{settings.API_V1_STR}/vector-store", tags=["Vector Store"])
app.include_router(memory.router, prefix=f"{settings.API_V1_STR}/memory", tags=["Memory"])
# 注册异常处理器
add_exception_handlers(app)

@app.get("/health", response_model=None)
async def health_check(request: Request) -> Union[dict[str, Any], JSONResponse]:
    """
    健康检查端点 - 检查服务及其依赖的状态
    
    Returns:
        健康状态对象，包含各组件状态
    """
    # 检查是否正在关闭
    if shutdown_manager.is_shutting_down:
        return JSONResponse(
            status_code=503,
            content={
                "status": "shutting_down",
                "message": "Service is shutting down"
            }
        )
    
    health_status: dict[str, Any] = {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": "1.1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }
    
    all_healthy = True
    
    # 检查向量数据库连接
    vector_store_name = settings.VECTOR_STORE_PROVIDER
    try:
        get_index()
        health_status["checks"]["vector_store"] = {
            "status": "healthy",
            "provider": vector_store_name,
            "collection": settings.VECTOR_STORE_COLLECTION
        }
    except Exception as e:
        all_healthy = False
        health_status["checks"]["vector_store"] = {
            "status": "unhealthy",
            "provider": vector_store_name,
            "error": str(e)
        }
        logger.error(f"Vector store ({vector_store_name}) health check failed: {e}")
    
    # 检查 Redis 连接
    try:
        redis_healthy = await RedisConnectionPool.health_check()
        health_status["checks"]["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy"
        }
        if not redis_healthy:
            all_healthy = False
    except Exception as e:
        all_healthy = False
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        logger.error(f"Redis health check failed: {e}")
    
    # LLM 配置信息
    health_status["checks"]["llm"] = {
        "status": "configured",
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL_NAME
    }
    
    # Memory 配置信息
    health_status["checks"]["memory"] = {
        "status": "configured",
        "provider": settings.MEMORY_PROVIDER,
        "short_term": settings.SHORT_TERM_MEMORY_ENABLED,
        "long_term": settings.LONG_TERM_MEMORY_ENABLED
    }
    
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """
    获取服务指标
    
    返回请求统计、错误率和性能指标
    生产环境建议使用 Prometheus + Grafana
    """
    from app.core.cache import cache
    
    metrics: dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # 请求指标
    if MetricsMiddleware._instance:
        metrics["requests"] = MetricsMiddleware._instance.get_metrics()
    else:
        metrics["requests"] = {"message": "Metrics middleware not available"}
    
    # 缓存指标
    metrics["cache"] = cache.get_stats()
    
    # 速率限制指标
    from app.core.rate_limiter import rate_limiter
    metrics["rate_limiter"] = {
        "active_clients": len(rate_limiter._requests)
    }
    
    return metrics


@app.get("/ready", response_model=None)
async def readiness_check() -> Union[dict[str, str], JSONResponse]:
    """
    就绪检查端点 - 用于 Kubernetes 就绪探针
    
    只有当所有关键组件都准备好时才返回成功
    """
    if shutdown_manager.is_shutting_down:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "shutting_down"}
        )
    
    try:
        # 检查关键组件
        get_index()
        await RedisConnectionPool.health_check()
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": str(e)}
        )


@app.get("/live")
async def liveness_check() -> dict[str, str]:
    """
    存活检查端点 - 用于 Kubernetes 存活探针
    
    只要应用进程在运行就返回成功
    """
    return {"status": "alive"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
