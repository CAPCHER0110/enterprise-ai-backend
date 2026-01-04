"""
速率限制器 - 防止API滥用
"""
import time
from typing import Dict, Optional
from collections import defaultdict
from dataclasses import dataclass
from app.core.logging import logger


@dataclass
class RateLimitRule:
    """速率限制规则"""
    requests: int  # 允许的请求数
    window: int  # 时间窗口（秒）
    
    def __str__(self):
        return f"{self.requests} requests per {self.window}s"


class RateLimiter:
    """
    基于内存的速率限制器
    
    使用滑动窗口算法跟踪请求
    注意：这是单进程实现，生产环境建议使用Redis实现分布式限流
    """
    
    def __init__(self):
        # 存储每个客户端的请求时间戳
        # key: client_id, value: list of timestamps
        self._requests: Dict[str, list] = defaultdict(list)
        
        # 默认规则
        self._default_rule = RateLimitRule(requests=100, window=60)
        
        # 自定义规则
        self._custom_rules: Dict[str, RateLimitRule] = {}
    
    def set_default_rule(self, requests: int, window: int):
        """设置默认规则"""
        self._default_rule = RateLimitRule(requests, window)
        logger.info(f"Rate limit default rule set: {self._default_rule}")
    
    def set_rule(self, client_id: str, requests: int, window: int):
        """为特定客户端设置规则"""
        self._custom_rules[client_id] = RateLimitRule(requests, window)
        logger.info(f"Rate limit rule set for {client_id}: {self._custom_rules[client_id]}")
    
    def is_allowed(self, client_id: str) -> tuple[bool, Optional[int]]:
        """
        检查是否允许请求
        
        Args:
            client_id: 客户端标识（IP地址、用户ID、API Key等）
        
        Returns:
            (is_allowed, retry_after): 是否允许和重试时间（秒）
        """
        current_time = time.time()
        
        # 获取适用的规则
        rule = self._custom_rules.get(client_id, self._default_rule)
        
        # 获取该客户端的请求历史
        request_times = self._requests[client_id]
        
        # 清理过期的请求记录（超出时间窗口）
        cutoff_time = current_time - rule.window
        request_times[:] = [t for t in request_times if t > cutoff_time]
        
        # 检查是否超过限制
        if len(request_times) >= rule.requests:
            # 计算需要等待的时间
            oldest_request = request_times[0]
            retry_after = int(oldest_request + rule.window - current_time) + 1
            
            logger.warning(
                f"Rate limit exceeded for {client_id}: "
                f"{len(request_times)}/{rule.requests} in {rule.window}s window"
            )
            return False, retry_after
        
        # 记录本次请求
        request_times.append(current_time)
        
        return True, None
    
    def get_remaining(self, client_id: str) -> int:
        """获取剩余可用请求数"""
        current_time = time.time()
        rule = self._custom_rules.get(client_id, self._default_rule)
        
        request_times = self._requests[client_id]
        cutoff_time = current_time - rule.window
        valid_requests = [t for t in request_times if t > cutoff_time]
        
        return max(0, rule.requests - len(valid_requests))
    
    def reset(self, client_id: Optional[str] = None):
        """重置限流器"""
        if client_id:
            self._requests.pop(client_id, None)
            logger.info(f"Rate limit reset for {client_id}")
        else:
            self._requests.clear()
            logger.info("Rate limit reset for all clients")
    
    def cleanup(self, max_age: int = 3600) -> int:
        """
        清理过期的客户端记录
        
        Args:
            max_age: 最大保留时间（秒）
            
        Returns:
            清理的客户端数量
        """
        current_time = time.time()
        cutoff_time = current_time - max_age
        
        clients_to_remove = []
        for client_id, request_times in self._requests.items():
            # 如果客户端最后一次请求是很久以前，则删除
            if not request_times or max(request_times) < cutoff_time:
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self._requests[client_id]
        
        if clients_to_remove:
            logger.info(f"Cleaned up {len(clients_to_remove)} inactive clients from rate limiter")
        
        return len(clients_to_remove)
    
    def get_stats(self) -> dict:
        """
        获取速率限制器统计信息
        
        Returns:
            统计信息字典
        """
        current_time = time.time()
        active_clients = 0
        total_requests = 0
        
        for client_id, request_times in self._requests.items():
            cutoff_time = current_time - self._default_rule.window
            valid_requests = [t for t in request_times if t > cutoff_time]
            if valid_requests:
                active_clients += 1
                total_requests += len(valid_requests)
        
        return {
            "active_clients": active_clients,
            "total_requests_in_window": total_requests,
            "default_limit": self._default_rule.requests,
            "default_window": self._default_rule.window,
            "custom_rules_count": len(self._custom_rules)
        }


# 全局速率限制器实例
rate_limiter = RateLimiter()

