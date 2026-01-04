"""
缓存测试
"""
import pytest
import time
from app.core.cache import SimpleCache


class TestSimpleCache:
    """测试简单缓存"""
    
    def setup_method(self):
        """每个测试前清空缓存"""
        cache = SimpleCache()
        cache.clear()
    
    def test_set_and_get(self):
        """测试设置和获取"""
        cache = SimpleCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        cache = SimpleCache()
        assert cache.get("nonexistent") is None
    
    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = SimpleCache()
        cache.set("key1", "value1", ttl=1)
        
        # 立即获取应该存在
        assert cache.get("key1") == "value1"
        
        # 等待过期
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_delete(self):
        """测试删除"""
        cache = SimpleCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.delete("key1")
        assert cache.get("key1") is None
    
    def test_clear(self):
        """测试清空"""
        cache = SimpleCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_overwrite_value(self):
        """测试覆盖值"""
        cache = SimpleCache()
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"
    
    def test_different_types(self):
        """测试不同数据类型"""
        cache = SimpleCache()
        
        cache.set("str", "string")
        cache.set("int", 123)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1})
        
        assert cache.get("str") == "string"
        assert cache.get("int") == 123
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1}

