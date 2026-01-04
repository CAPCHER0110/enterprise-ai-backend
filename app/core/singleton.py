"""
线程安全的单例模式实现
"""
import threading
from typing import TypeVar, Type, Optional, Dict, Any
from abc import ABC

T = TypeVar('T', bound='ThreadSafeSingleton')


class ThreadSafeSingleton(ABC):
    """
    线程安全的单例基类
    
    使用双重检查锁定模式确保线程安全
    """
    _instances: Dict[Type, Any] = {}
    _locks: Dict[Type, threading.Lock] = {}
    _init_lock = threading.Lock()
    
    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        # 快速路径：如果实例已存在，直接返回
        if cls in cls._instances:
            return cls._instances[cls]
        
        # 确保每个类有自己的锁
        with cls._init_lock:
            if cls not in cls._locks:
                cls._locks[cls] = threading.Lock()
        
        # 双重检查锁定
        with cls._locks[cls]:
            if cls not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[cls] = instance
            return cls._instances[cls]
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例（用于测试）
        """
        with cls._init_lock:
            if cls in cls._instances:
                del cls._instances[cls]
            if cls in cls._locks:
                del cls._locks[cls]
    
    @classmethod
    def get_instance(cls: Type[T]) -> Optional[T]:
        """
        获取现有实例（不创建新实例）
        """
        return cls._instances.get(cls)
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查是否已初始化
        """
        return cls in cls._instances


class SingletonMeta(type):
    """
    单例元类 - 另一种实现方式
    
    适用于不能继承ThreadSafeSingleton的情况
    """
    _instances: Dict[Type, Any] = {}
    _locks: Dict[Type, threading.Lock] = {}
    _init_lock = threading.Lock()
    
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls in cls._instances:
            return cls._instances[cls]
        
        with cls._init_lock:
            if cls not in cls._locks:
                cls._locks[cls] = threading.Lock()
        
        with cls._locks[cls]:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            return cls._instances[cls]

