"""
优雅关闭管理器

提供应用程序关闭时的资源清理功能
"""
import asyncio
import signal
from typing import Callable, List, Awaitable, Optional
from app.core.logging import logger


class ShutdownManager:
    """
    优雅关闭管理器
    
    管理应用关闭时需要执行的清理任务
    支持同步和异步清理函数
    """
    
    def __init__(self) -> None:
        self._cleanup_tasks: List[Callable[[], Awaitable[None]]] = []
        self._is_shutting_down = False
        self._shutdown_timeout = 30.0  # 秒
    
    def register(self, cleanup_func: Callable[[], Awaitable[None]]) -> None:
        """
        注册清理函数
        
        Args:
            cleanup_func: 异步清理函数
        """
        self._cleanup_tasks.append(cleanup_func)
        logger.debug(f"Registered cleanup task: {cleanup_func.__name__}")
    
    def set_timeout(self, timeout: float) -> None:
        """设置关闭超时时间"""
        self._shutdown_timeout = timeout
    
    @property
    def is_shutting_down(self) -> bool:
        """是否正在关闭"""
        return self._is_shutting_down
    
    async def shutdown(self) -> None:
        """
        执行所有注册的清理任务
        """
        if self._is_shutting_down:
            logger.warning("Shutdown already in progress")
            return
        
        self._is_shutting_down = True
        logger.info(f"Starting graceful shutdown with {len(self._cleanup_tasks)} tasks...")
        
        # 逆序执行清理任务（后注册的先清理）
        for task in reversed(self._cleanup_tasks):
            try:
                logger.debug(f"Running cleanup task: {task.__name__}")
                await asyncio.wait_for(
                    task(),
                    timeout=self._shutdown_timeout / len(self._cleanup_tasks) if self._cleanup_tasks else 10
                )
            except asyncio.TimeoutError:
                logger.warning(f"Cleanup task {task.__name__} timed out")
            except Exception as e:
                logger.error(f"Error in cleanup task {task.__name__}: {e}", exc_info=True)
        
        logger.info("Graceful shutdown completed")
    
    def clear(self) -> None:
        """清空所有注册的清理任务"""
        self._cleanup_tasks.clear()
        self._is_shutting_down = False


# 全局关闭管理器实例
shutdown_manager = ShutdownManager()


def register_cleanup(func: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
    """
    装饰器：注册清理函数
    
    Example:
        @register_cleanup
        async def cleanup_redis():
            await RedisConnectionPool.close()
    """
    shutdown_manager.register(func)
    return func


async def graceful_shutdown() -> None:
    """执行优雅关闭"""
    await shutdown_manager.shutdown()

