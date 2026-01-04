"""
向量数据库管理器 - 向后兼容的Milvus管理器
"""
import threading
from typing import Optional
from pymilvus import MilvusClient
from app.core.config import settings
from app.core.logging import logger


class MilvusManager:
    """
    Milvus管理器（线程安全的单例模式）
    
    向后兼容的API，用于admin等模块直接访问Milvus
    """
    _instance: Optional['MilvusManager'] = None
    _client: Optional[MilvusClient] = None
    _lock = threading.Lock()
    _initialized = False

    @classmethod
    def get_instance(cls) -> 'MilvusManager':
        """获取Milvus管理器实例（线程安全的单例）"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = MilvusManager()
        return cls._instance

    def __init__(self) -> None:
        """初始化Milvus连接"""
        if MilvusManager._initialized:
            return
        
        with MilvusManager._lock:
            if MilvusManager._initialized:
                return
            
            logger.info(f"Connecting to Milvus at {settings.MILVUS_URI}...")
            try:
                MilvusManager._client = MilvusClient(
                    uri=settings.MILVUS_URI,
                    token=settings.MILVUS_TOKEN if settings.MILVUS_TOKEN else None
                )
                MilvusManager._initialized = True
                logger.info("Milvus client connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Milvus: {e}")
                raise
        
    @property
    def client(self) -> MilvusClient:
        """获取Milvus客户端"""
        if self._client is None:
            raise RuntimeError("Milvus client not initialized")
        return self._client
    
    def create_collection_if_not_exists(self, name: str, dim: int) -> None:
        """创建集合（如果不存在）"""
        if not self._client.has_collection(name):
            self._client.create_collection(
                collection_name=name,
                dimension=dim
            )
            logger.info(f"Created Milvus collection: {name}")
        else:
            logger.debug(f"Milvus collection {name} already exists")
    
    @classmethod
    def reset(cls) -> None:
        """重置管理器（用于测试）"""
        with cls._lock:
            if cls._client:
                try:
                    cls._client.close()
                except Exception:
                    pass
            cls._client = None
            cls._instance = None
            cls._initialized = False