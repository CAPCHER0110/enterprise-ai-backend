"""
Prometheus指标集成
"""
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client import CollectorRegistry, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response
from app.core.logging import logger


# 创建自定义registry（可选，避免与其他库冲突）
# registry = CollectorRegistry()

# 请求计数器
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟直方图
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# 正在处理的请求数
http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# LLM相关指标
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request latency',
    ['provider', 'model']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens processed',
    ['provider', 'model', 'type']  # type: input/output
)

# 向量数据库指标
vector_db_operations_total = Counter(
    'vector_db_operations_total',
    'Total vector database operations',
    ['provider', 'operation', 'status']
)

vector_db_operation_duration_seconds = Histogram(
    'vector_db_operation_duration_seconds',
    'Vector database operation latency',
    ['provider', 'operation']
)

# Redis指标
redis_operations_total = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)

redis_connection_pool_size = Gauge(
    'redis_connection_pool_size',
    'Redis connection pool size',
    ['state']  # state: active/idle
)

# 应用指标
app_info = Gauge(
    'app_info',
    'Application information',
    ['version', 'python_version']
)

# 缓存指标
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits'
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses'
)

# 速率限制指标
rate_limit_exceeded_total = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded events',
    ['client_id']
)


class PrometheusMetrics:
    """Prometheus指标管理器"""
    
    @staticmethod
    def record_request(method: str, endpoint: str, status: int, duration: float):
        """记录HTTP请求"""
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    @staticmethod
    def record_llm_request(provider: str, model: str, status: str, duration: float, 
                          input_tokens: Optional[int] = None, output_tokens: Optional[int] = None):
        """记录LLM请求"""
        llm_requests_total.labels(provider=provider, model=model, status=status).inc()
        llm_request_duration_seconds.labels(provider=provider, model=model).observe(duration)
        
        if input_tokens:
            llm_tokens_total.labels(provider=provider, model=model, type='input').inc(input_tokens)
        if output_tokens:
            llm_tokens_total.labels(provider=provider, model=model, type='output').inc(output_tokens)
    
    @staticmethod
    def record_vector_db_operation(provider: str, operation: str, status: str, duration: float):
        """记录向量数据库操作"""
        vector_db_operations_total.labels(provider=provider, operation=operation, status=status).inc()
        vector_db_operation_duration_seconds.labels(provider=provider, operation=operation).observe(duration)
    
    @staticmethod
    def record_redis_operation(operation: str, status: str):
        """记录Redis操作"""
        redis_operations_total.labels(operation=operation, status=status).inc()
    
    @staticmethod
    def update_redis_pool_size(active: int, idle: int):
        """更新Redis连接池大小"""
        redis_connection_pool_size.labels(state='active').set(active)
        redis_connection_pool_size.labels(state='idle').set(idle)
    
    @staticmethod
    def record_cache_hit():
        """记录缓存命中"""
        cache_hits_total.inc()
    
    @staticmethod
    def record_cache_miss():
        """记录缓存未命中"""
        cache_misses_total.inc()
    
    @staticmethod
    def record_rate_limit_exceeded(client_id: str):
        """记录速率限制超出"""
        rate_limit_exceeded_total.labels(client_id=client_id).inc()
    
    @staticmethod
    def set_app_info(version: str, python_version: str):
        """设置应用信息"""
        app_info.labels(version=version, python_version=python_version).set(1)


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus指标端点"""
    try:
        metrics = generate_latest(REGISTRY)
        return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}", exc_info=True)
        return Response(content=b"", status_code=500)


# 初始化应用信息
import sys
from app.core.config import settings

PrometheusMetrics.set_app_info(
    version="1.0.0",  # 可以从配置或版本文件读取
    python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
)

logger.info("Prometheus metrics initialized")

