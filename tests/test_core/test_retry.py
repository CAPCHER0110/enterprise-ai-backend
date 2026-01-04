"""
重试机制测试
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.core.retry import retry_with_backoff, RetryConfig, CircuitBreaker


class TestRetryConfig:
    """测试重试配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.circuit_breaker_enabled is False
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=30.0,
            backoff_factor=3.0
        )
        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0
        assert config.backoff_factor == 3.0


class TestRetryDecorator:
    """测试重试装饰器"""
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """测试第一次尝试成功"""
        call_count = 0
        
        @retry_with_backoff(config=RetryConfig(max_retries=3, initial_delay=0.1))
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """测试失败后重试成功"""
        call_count = 0
        
        @retry_with_backoff(
            config=RetryConfig(max_retries=3, initial_delay=0.1),
            exceptions=(ValueError,)
        )
        async def retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = await retry_func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """测试重试次数耗尽"""
        call_count = 0
        
        @retry_with_backoff(
            config=RetryConfig(max_retries=3, initial_delay=0.1),
            exceptions=(ValueError,)
        )
        async def fail_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError):
            await fail_func()
        
        assert call_count == 4  # 初始调用 + 3次重试
    
    def test_retry_sync_function(self):
        """测试同步函数重试"""
        call_count = 0
        
        @retry_with_backoff(
            config=RetryConfig(max_retries=3, initial_delay=0.1),
            exceptions=(ValueError,)
        )
        def sync_retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        result = sync_retry_func()
        assert result == "success"
        assert call_count == 2


class TestCircuitBreaker:
    """测试断路器"""
    
    def test_circuit_breaker_init(self):
        """测试断路器初始化"""
        cb = CircuitBreaker(failure_threshold=5, reset_timeout=60)
        assert cb.failure_count == 0
        assert cb.failure_threshold == 5
        assert cb.reset_timeout == 60
        assert cb.state == "closed"
    
    def test_circuit_breaker_records_failure(self):
        """测试断路器记录失败"""
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60)
        
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == "closed"
        
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 3
        assert cb.state == "open"
    
    def test_circuit_breaker_records_success(self):
        """测试断路器记录成功"""
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60)
        
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
        
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"
    
    def test_circuit_breaker_can_execute(self):
        """测试断路器是否允许执行"""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1)
        
        # 关闭状态允许执行
        assert cb.can_execute() is True
        
        # 达到失败阈值后断开
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False
        
        # 等待重置超时
        import time
        time.sleep(1.1)
        assert cb.can_execute() is True
        assert cb.state == "half_open"

