"""
速率限制器测试
"""
import pytest
import time
from app.core.rate_limiter import RateLimiter, RateLimitRule


class TestRateLimitRule:
    """测试速率限制规则"""
    
    def test_rate_limit_rule_creation(self):
        """测试规则创建"""
        rule = RateLimitRule(requests=100, window=60)
        assert rule.requests == 100
        assert rule.window == 60
    
    def test_rate_limit_rule_str(self):
        """测试规则字符串表示"""
        rule = RateLimitRule(requests=100, window=60)
        assert str(rule) == "100 requests per 60s"


class TestRateLimiter:
    """测试速率限制器"""
    
    def setup_method(self):
        """每个测试前重置限流器"""
        self.limiter = RateLimiter()
        self.limiter.reset()
    
    def test_default_rule(self):
        """测试默认规则"""
        limiter = RateLimiter()
        assert limiter._default_rule.requests == 100
        assert limiter._default_rule.window == 60
    
    def test_set_default_rule(self):
        """测试设置默认规则"""
        self.limiter.set_default_rule(requests=10, window=1)
        assert self.limiter._default_rule.requests == 10
        assert self.limiter._default_rule.window == 1
    
    def test_set_custom_rule(self):
        """测试设置自定义规则"""
        self.limiter.set_rule("client1", requests=20, window=2)
        assert "client1" in self.limiter._custom_rules
        assert self.limiter._custom_rules["client1"].requests == 20
    
    def test_is_allowed_within_limit(self):
        """测试在限制内"""
        self.limiter.set_default_rule(requests=5, window=60)
        
        for _ in range(5):
            is_allowed, retry_after = self.limiter.is_allowed("client1")
            assert is_allowed is True
            assert retry_after is None
    
    def test_is_allowed_exceeds_limit(self):
        """测试超过限制"""
        self.limiter.set_default_rule(requests=3, window=60)
        
        # 前3次应该成功
        for _ in range(3):
            is_allowed, _ = self.limiter.is_allowed("client1")
            assert is_allowed is True
        
        # 第4次应该失败
        is_allowed, retry_after = self.limiter.is_allowed("client1")
        assert is_allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    def test_window_sliding(self):
        """测试滑动窗口"""
        self.limiter.set_default_rule(requests=2, window=1)
        
        # 前2次成功
        assert self.limiter.is_allowed("client1")[0] is True
        assert self.limiter.is_allowed("client1")[0] is True
        
        # 第3次失败
        assert self.limiter.is_allowed("client1")[0] is False
        
        # 等待窗口过期
        time.sleep(1.1)
        
        # 应该可以再次请求
        assert self.limiter.is_allowed("client1")[0] is True
    
    def test_get_remaining(self):
        """测试获取剩余请求数"""
        self.limiter.set_default_rule(requests=5, window=60)
        
        assert self.limiter.get_remaining("client1") == 5
        
        self.limiter.is_allowed("client1")
        assert self.limiter.get_remaining("client1") == 4
        
        self.limiter.is_allowed("client1")
        assert self.limiter.get_remaining("client1") == 3
    
    def test_reset_specific_client(self):
        """测试重置特定客户端"""
        self.limiter.set_default_rule(requests=2, window=60)
        
        self.limiter.is_allowed("client1")
        self.limiter.is_allowed("client1")
        assert self.limiter.get_remaining("client1") == 0
        
        self.limiter.reset("client1")
        assert self.limiter.get_remaining("client1") == 2
    
    def test_reset_all(self):
        """测试重置所有客户端"""
        self.limiter.set_default_rule(requests=2, window=60)
        
        self.limiter.is_allowed("client1")
        self.limiter.is_allowed("client2")
        
        self.limiter.reset()
        assert self.limiter.get_remaining("client1") == 2
        assert self.limiter.get_remaining("client2") == 2
    
    def test_different_clients_independent(self):
        """测试不同客户端独立计数"""
        self.limiter.set_default_rule(requests=2, window=60)
        
        assert self.limiter.is_allowed("client1")[0] is True
        assert self.limiter.is_allowed("client1")[0] is True
        assert self.limiter.is_allowed("client1")[0] is False
        
        # client2应该不受影响
        assert self.limiter.is_allowed("client2")[0] is True
        assert self.limiter.is_allowed("client2")[0] is True
    
    def test_cleanup(self):
        """测试清理过期记录"""
        self.limiter.set_default_rule(requests=2, window=1)
        
        # 添加一些请求
        self.limiter.is_allowed("client1")
        self.limiter.is_allowed("client2")
        
        # 等待过期
        time.sleep(1.1)
        
        # 清理
        self.limiter.cleanup(max_age=1)
        
        # 检查是否清理
        assert "client1" not in self.limiter._requests or not self.limiter._requests["client1"]

