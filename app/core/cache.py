"""
LRU缓存实现

提供线程安全的内存缓存，支持TTL过期和LRU淘汰策略
生产环境建议使用 Redis 作为缓存后端
"""
import time
from typing import Any, Optional, Dict, Tuple
from threading import Lock
from collections import OrderedDict
from dataclasses import dataclass
from app.core.config import settings
from app.core.logging import logger


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    expiry: float
    created_at: float
    access_count: int = 0


class LRUCache:
    """
    带TTL的LRU缓存（线程安全）
    
    特性:
    - 支持TTL过期
    - LRU淘汰策略
    - 最大条目数限制
    - 访问计数统计
    """
    
    def __init__(
        self, 
        default_ttl: int = 3600,
        max_size: int = 10000
    ) -> None:
        """
        初始化缓存
        
        Args:
            default_ttl: 默认过期时间（秒）
            max_size: 最大缓存条目数
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self.default_ttl = default_ttl
        self.max_size = max_size
        
        # 统计信息
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        如果命中，会更新LRU顺序和访问计数
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            current_time = time.time()
            
            # 检查是否过期
            if current_time > entry.expiry:
                del self._cache[key]
                self._misses += 1
                return None
            
            # 更新LRU顺序（移到末尾表示最近使用）
            self._cache.move_to_end(key)
            entry.access_count += 1
            
            self._hits += 1
            return entry.value
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
        """
        if not settings.ENABLE_CACHE:
            return
        
        ttl = ttl if ttl is not None else self.default_ttl
        current_time = time.time()
        expiry = current_time + ttl
        
        with self._lock:
            # 如果key已存在，更新它
            if key in self._cache:
                self._cache[key] = CacheEntry(
                    value=value,
                    expiry=expiry,
                    created_at=current_time
                )
                self._cache.move_to_end(key)
                return
            
            # 检查是否需要淘汰
            while len(self._cache) >= self.max_size:
                # 淘汰最旧的条目（OrderedDict的第一个）
                evicted_key, _ = self._cache.popitem(last=False)
                self._evictions += 1
                logger.debug(f"Cache eviction: {evicted_key}")
            
            # 添加新条目
            self._cache[key] = CacheEntry(
                value=value,
                expiry=expiry,
                created_at=current_time
            )
    
    def delete(self, key: str) -> bool:
        """
        删除缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    def cleanup_expired(self) -> int:
        """
        清理过期的缓存项
        
        Returns:
            清理的条目数
        """
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in list(self._cache.items()):
                if current_time > entry.expiry:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            包含统计信息的字典
        """
        with self._lock:
            current_time = time.time()
            total = len(self._cache)
            expired = sum(
                1 for entry in self._cache.values() 
                if current_time > entry.expiry
            )
            
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "evictions": self._evictions,
                "cache_enabled": settings.ENABLE_CACHE
            }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0
    
    def contains(self, key: str) -> bool:
        """
        检查键是否存在且未过期
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if time.time() > entry.expiry:
                del self._cache[key]
                return False
            
            return True
    
    def size(self) -> int:
        """获取当前缓存大小"""
        with self._lock:
            return len(self._cache)


# 为了向后兼容，保留SimpleCache别名
SimpleCache = LRUCache

# 全局缓存实例
cache = LRUCache(
    default_ttl=settings.CACHE_TTL,
    max_size=getattr(settings, 'CACHE_MAX_SIZE', 10000)
)

