"""
连接池和资源管理

提供线程安全的连接池管理，支持异步操作和健康检查
"""
import asyncio
import threading
from typing import Optional, AsyncIterator
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger
from app.core.retry import retry_with_backoff, RetryConfig


class RedisConnectionPool:
    """
    Redis连接池管理器（线程安全）
    
    使用双重检查锁定确保线程安全的单例模式
    """
    _pool: Optional[aioredis.ConnectionPool] = None
    _client: Optional[aioredis.Redis] = None
    _thread_lock = threading.RLock()
    _async_lock: Optional[asyncio.Lock] = None
    _initialized = False
    
    @classmethod
    def _get_async_lock(cls) -> asyncio.Lock:
        """
        获取异步锁（线程安全的延迟初始化）
        
        注意：这个方法本身使用线程锁保护
        """
        if cls._async_lock is None:
            with cls._thread_lock:
                if cls._async_lock is None:
                    cls._async_lock = asyncio.Lock()
        return cls._async_lock
    
    @classmethod
    def get_pool(cls) -> aioredis.ConnectionPool:
        """
        获取Redis连接池（线程安全的单例）
        
        Returns:
            Redis连接池实例
        """
        if cls._pool is None:
            with cls._thread_lock:
                if cls._pool is None:
                    cls._pool = aioredis.ConnectionPool.from_url(
                        settings.REDIS_URL,
                        max_connections=settings.REDIS_MAX_CONNECTIONS,
                        decode_responses=True,
                        #retry_on_timeout=True,
                        health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
                        socket_timeout=5.0,        # 连接超时 5秒
                        socket_connect_timeout=5.0 # 建立连接超时 5秒
                    )
                    logger.info(
                        f"Redis connection pool created: "
                        f"max_connections={settings.REDIS_MAX_CONNECTIONS}, "
                        f"url={settings.REDIS_URL[:20]}..."
                    )
        return cls._pool
    
    @classmethod
    def get_client(cls) -> aioredis.Redis:
        """
        获取Redis客户端（线程安全的单例）
        
        Returns:
            Redis客户端实例
        """
        if cls._client is None:
            with cls._thread_lock:
                if cls._client is None:
                    pool = cls.get_pool()
                    cls._client = aioredis.Redis(connection_pool=pool)
                    cls._initialized = True
                    logger.info("Redis client created")
        return cls._client
    
    @classmethod
    async def close(cls) -> None:
        """
        关闭连接池和客户端
        
        应在应用关闭时调用
        """
        async_lock = cls._get_async_lock()
        async with async_lock:
            if cls._client:
                try:
                    await cls._client.close()
                    logger.debug("Redis client closed")
                except Exception as e:
                    logger.warning(f"Error closing Redis client: {e}")
                finally:
                    cls._client = None
            
            if cls._pool:
                try:
                    await cls._pool.disconnect()
                    logger.info("Redis connection pool closed")
                except Exception as e:
                    logger.warning(f"Error disconnecting Redis pool: {e}")
                finally:
                    cls._pool = None
            
            cls._initialized = False
    
    @classmethod
    @asynccontextmanager
    async def get_connection(cls) -> AsyncIterator[aioredis.Redis]:
        """
        获取Redis连接（上下文管理器）
        
        使用方式:
            async with RedisConnectionPool.get_connection() as client:
                await client.get("key")
        
        Yields:
            Redis客户端实例
        """
        client = cls.get_client()
        try:
            yield client
        except aioredis.RedisError as e:
            logger.error(f"Redis operation error: {e}")
            raise
    
    @classmethod
    @retry_with_backoff(
        config=RetryConfig(max_retries=3, initial_delay=1.0),
        exceptions=(ConnectionError, TimeoutError, aioredis.RedisError)
    )
    async def health_check(cls) -> bool:
        """
        执行Redis健康检查
        
        Returns:
            True如果健康，False如果不健康
        """
        try:
            client = cls.get_client()
            result = await client.ping()
            return result is True or result == b'PONG' or result == 'PONG'
        except Exception as e:
            logger.error(f"Redis health check failed: {type(e).__name__}: {e}")
            raise
    
    @classmethod
    def is_initialized(cls) -> bool:
        """检查连接池是否已初始化"""
        return cls._initialized
    
    @classmethod
    async def get_info(cls) -> dict:
        """
        获取Redis连接信息（用于诊断）
        
        Returns:
            包含连接信息的字典
        """
        try:
            client = cls.get_client()
            info = await client.info("server")
            return {
                "connected": True,
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }

