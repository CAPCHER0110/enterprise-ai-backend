"""
重试机制和断路器模式

提供可配置的重试策略和断路器模式，用于处理瞬时故障
"""
import asyncio
import time
import random
from typing import Callable, TypeVar, Optional, Any, Tuple, Type, Union, overload
from functools import wraps
from dataclasses import dataclass, field
from app.core.logging import logger

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class RetryConfig:
    """
    重试配置
    
    Attributes:
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数退避基数 (别名: backoff_factor)
        jitter: 是否添加随机抖动
        circuit_breaker_enabled: 是否启用断路器
    """
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    circuit_breaker_enabled: bool = False
    
    # 别名属性，为了兼容测试
    @property
    def backoff_factor(self) -> float:
        """exponential_base 的别名"""
        return self.exponential_base
    
    def __post_init__(self) -> None:
        """验证配置"""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        if self.exponential_base < 1:
            raise ValueError("exponential_base must be >= 1")


def _calculate_delay(config: RetryConfig, attempt: int) -> float:
    """计算延迟时间（带指数退避和可选抖动）"""
    delay = min(
        config.initial_delay * (config.exponential_base ** attempt),
        config.max_delay
    )
    
    if config.jitter:
        # 添加 0.5-1.0 的随机因子
        delay = delay * (0.5 + random.random() * 0.5)
    
    return delay


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable[[F], F]:
    """
    带指数退避的重试装饰器
    
    支持同步和异步函数，自动检测并应用正确的包装器。
    
    Args:
        config: 重试配置
        exceptions: 需要重试的异常类型元组
        on_retry: 重试时的回调函数 (exception, attempt_number) -> None
        
    Returns:
        装饰后的函数
        
    Example:
        @retry_with_backoff(
            config=RetryConfig(max_retries=3),
            exceptions=(ConnectionError, TimeoutError)
        )
        async def fetch_data():
            ...
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Optional[Exception] = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < config.max_retries:
                        wait_time = _calculate_delay(config, attempt)
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        else:
                            logger.warning(
                                f"Retry {attempt + 1}/{config.max_retries} for "
                                f"{func.__name__}: {type(e).__name__}: {str(e)}"
                            )
                        
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"Max retries ({config.max_retries}) exceeded for "
                            f"{func.__name__}: {type(e).__name__}: {str(e)}"
                        )
            
            # 所有重试都失败，抛出最后一个错误
            if last_error is not None:
                raise last_error
            # 理论上不会到达这里，但为了类型安全
            raise RuntimeError(f"Unexpected error in retry logic for {func.__name__}")
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Optional[Exception] = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < config.max_retries:
                        wait_time = _calculate_delay(config, attempt)
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        else:
                            logger.warning(
                                f"Retry {attempt + 1}/{config.max_retries} for "
                                f"{func.__name__}: {type(e).__name__}: {str(e)}"
                            )
                        
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"Max retries ({config.max_retries}) exceeded for "
                            f"{func.__name__}: {type(e).__name__}: {str(e)}"
                        )
            
            # 所有重试都失败，抛出最后一个错误
            if last_error is not None:
                raise last_error
            raise RuntimeError(f"Unexpected error in retry logic for {func.__name__}")
        
        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore
    
    return decorator


class CircuitBreakerError(Exception):
    """断路器打开时抛出的异常"""
    pass


class CircuitBreaker:
    """
    断路器模式实现
    
    状态转换:
    - CLOSED -> OPEN: 失败次数达到阈值
    - OPEN -> HALF_OPEN: 恢复超时后
    - HALF_OPEN -> CLOSED: 调用成功
    - HALF_OPEN -> OPEN: 调用失败
    
    Attributes:
        failure_threshold: 触发断路的失败次数
        recovery_timeout: 恢复超时时间（秒）
        expected_exception: 预期的异常类型
    """
    
    # 状态常量
    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self._state = self.STATE_CLOSED
    
    @property
    def state(self) -> str:
        """获取当前状态"""
        return self._state
    
    def _should_allow_request(self) -> bool:
        """检查是否应该允许请求"""
        if self._state == self.STATE_CLOSED:
            return True
        
        if self._state == self.STATE_OPEN:
            if self.last_failure_time is None:
                return True
            
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.recovery_timeout:
                self._state = self.STATE_HALF_OPEN
                logger.info(
                    f"Circuit breaker transitioning to HALF_OPEN "
                    f"after {elapsed:.1f}s"
                )
                return True
            return False
        
        # HALF_OPEN: 允许一个请求通过
        return True
    
    def record_success(self) -> None:
        """记录成功调用"""
        if self._state == self.STATE_HALF_OPEN:
            self._state = self.STATE_CLOSED
            self.failure_count = 0
            logger.info("Circuit breaker closed after successful call")
        elif self._state == self.STATE_CLOSED:
            # 成功时重置失败计数
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self._state == self.STATE_HALF_OPEN:
            self._state = self.STATE_OPEN
            logger.warning("Circuit breaker re-opened after failure in half-open state")
        elif self.failure_count >= self.failure_threshold:
            self._state = self.STATE_OPEN
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
    
    def can_execute(self) -> bool:
        """检查是否可以执行（用于速率限制测试兼容性）"""
        return self._should_allow_request()
    
    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        执行函数，应用断路器逻辑
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值
            
        Raises:
            CircuitBreakerError: 断路器打开时
            expected_exception: 函数抛出的异常
        """
        if not self._should_allow_request():
            raise CircuitBreakerError(
                f"Circuit breaker is OPEN. "
                f"Will retry after {self.recovery_timeout}s"
            )
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exception:
            self.record_failure()
            raise
    
    async def call_async(
        self, 
        func: Callable[..., Any], 
        *args: Any, 
        **kwargs: Any
    ) -> Any:
        """
        异步执行函数，应用断路器逻辑
        """
        if not self._should_allow_request():
            raise CircuitBreakerError(
                f"Circuit breaker is OPEN. "
                f"Will retry after {self.recovery_timeout}s"
            )
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exception:
            self.record_failure()
            raise
    
    def reset(self) -> None:
        """重置断路器状态"""
        self._state = self.STATE_CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker reset")

