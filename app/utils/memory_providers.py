"""
记忆提供商工厂 - 支持LlamaIndex、LangChain、Mem0
支持短期记忆（会话内）和长期记忆（跨会话）
"""
from typing import Optional, Literal, Any, Protocol
from abc import ABC, abstractmethod
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ValidationException


MemoryProvider = Literal["llamaindex", "langchain", "mem0"]


class MemoryInterface(Protocol):
    """记忆接口协议"""
    
    def get_memory(self, session_id: str) -> Any:
        """获取记忆对象"""
        ...
    
    async def clear_memory(self, session_id: str) -> bool:
        """清空记忆"""
        ...
    
    async def save_memory(self, session_id: str, messages: list) -> bool:
        """保存记忆"""
        ...


class MemoryProviderFactory:
    """记忆提供商工厂类"""
    
    @staticmethod
    def create_memory_provider(
        provider: Optional[str] = None,
        short_term_token_limit: Optional[int] = None,
        long_term_enabled: Optional[bool] = None,
        **kwargs
    ) -> MemoryInterface:
        """
        创建记忆提供商实例
        
        Args:
            provider: 记忆提供商 ("llamaindex", "langchain", "mem0")
            short_term_token_limit: 短期记忆token限制
            long_term_enabled: 是否启用长期记忆
            **kwargs: 其他提供商特定参数
            
        Returns:
            记忆提供商实例
        """
        provider = (provider or settings.MEMORY_PROVIDER).lower()
        short_term_token_limit = short_term_token_limit or settings.SHORT_TERM_TOKEN_LIMIT
        long_term_enabled = long_term_enabled if long_term_enabled is not None else settings.LONG_TERM_MEMORY_ENABLED
        
        try:
            if provider == "llamaindex":
                return MemoryProviderFactory._create_llamaindex_provider(
                    short_term_token_limit=short_term_token_limit,
                    long_term_enabled=long_term_enabled,
                    **kwargs
                )
            elif provider == "langchain":
                return MemoryProviderFactory._create_langchain_provider(
                    short_term_token_limit=short_term_token_limit,
                    long_term_enabled=long_term_enabled,
                    **kwargs
                )
            elif provider == "mem0":
                return MemoryProviderFactory._create_mem0_provider(
                    short_term_token_limit=short_term_token_limit,
                    long_term_enabled=long_term_enabled,
                    **kwargs
                )
            else:
                raise ValidationException(
                    f"Unsupported memory provider: {provider}. "
                    f"Supported providers: llamaindex, langchain, mem0"
                )
        except Exception as e:
            logger.error(f"Failed to create memory provider {provider}: {e}")
            raise
    
    @staticmethod
    def _create_llamaindex_provider(
        short_term_token_limit: int,
        long_term_enabled: bool,
        **kwargs
    ) -> MemoryInterface:
        """
        创建LlamaIndex记忆提供商
        
        LlamaIndex使用ChatMemoryBuffer实现短期记忆（滑动窗口）
        使用RedisChatStore实现长期记忆持久化
        """
        try:
            from llama_index.storage.chat_store.redis import RedisChatStore
            from llama_index.core.memory import ChatMemoryBuffer
        except ImportError:
            raise ValidationException(
                "LlamaIndex memory dependencies not installed. "
                "Please install: pip install llama-index-storage-chat-store-redis"
            )
        
        logger.info("Creating LlamaIndex memory provider")
        
        # 创建Redis存储（用于长期记忆）
        chat_store = None
        if long_term_enabled:
            chat_store = RedisChatStore(redis_url=settings.REDIS_URL)
            logger.info("Long-term memory enabled with Redis")
        
        return LlamaIndexMemoryProvider(
            chat_store=chat_store,
            short_term_token_limit=short_term_token_limit,
            long_term_enabled=long_term_enabled
        )
    
    @staticmethod
    def _create_langchain_provider(
        short_term_token_limit: int,
        long_term_enabled: bool,
        **kwargs
    ) -> MemoryInterface:
        """
        创建LangChain记忆提供商
        
        LangChain使用ConversationBufferWindowMemory实现短期记忆
        使用RedisChatMessageHistory实现长期记忆持久化
        """
        try:
            from langchain.memory import ConversationBufferWindowMemory
            from langchain_community.chat_message_histories import RedisChatMessageHistory
        except ImportError:
            raise ValidationException(
                "LangChain memory dependencies not installed. "
                "Please install: pip install langchain langchain-community"
            )
        
        logger.info("Creating LangChain memory provider")
        
        return LangChainMemoryProvider(
            short_term_token_limit=short_term_token_limit,
            long_term_enabled=long_term_enabled,
            redis_url=settings.REDIS_URL if long_term_enabled else None
        )
    
    @staticmethod
    def _create_mem0_provider(
        short_term_token_limit: int,
        long_term_enabled: bool,
        **kwargs
    ) -> MemoryInterface:
        """
        创建Mem0记忆提供商
        
        Mem0提供高级记忆管理，包括：
        - 短期记忆：会话内上下文
        - 长期记忆：跨会话的语义记忆
        """
        try:
            import mem0
        except ImportError:
            raise ValidationException(
                "Mem0 dependencies not installed. "
                "Please install: pip install mem0ai"
            )
        
        logger.info("Creating Mem0 memory provider")
        
        # Mem0配置
        mem0_config = {
            "vector_store": {
                "provider": settings.VECTOR_STORE_PROVIDER,
                "config": {}
            }
        }
        
        return Mem0MemoryProvider(
            config=mem0_config,
            short_term_token_limit=short_term_token_limit,
            long_term_enabled=long_term_enabled
        )
    
    @staticmethod
    def get_supported_providers() -> list[str]:
        """获取支持的记忆提供商列表"""
        return ["llamaindex", "langchain", "mem0"]
    
    @staticmethod
    def get_provider_info(provider: str) -> dict:
        """
        获取提供商信息
        
        Args:
            provider: 提供商名称
            
        Returns:
            提供商信息字典
        """
        provider = provider.lower()
        
        info_map = {
            "llamaindex": {
                "name": "LlamaIndex",
                "description": "LlamaIndex记忆管理（ChatMemoryBuffer + Redis）",
                "features": ["滑动窗口", "Redis持久化", "Token限制", "与LlamaIndex集成"],
                "short_term": "ChatMemoryBuffer（滑动窗口）",
                "long_term": "RedisChatStore（持久化）",
                "requires_redis": True
            },
            "langchain": {
                "name": "LangChain",
                "description": "LangChain记忆管理（ConversationBufferWindowMemory + Redis）",
                "features": ["滑动窗口", "Redis持久化", "Token限制", "与LangChain集成"],
                "short_term": "ConversationBufferWindowMemory（滑动窗口）",
                "long_term": "RedisChatMessageHistory（持久化）",
                "requires_redis": True
            },
            "mem0": {
                "name": "Mem0",
                "description": "Mem0高级记忆管理（语义记忆 + 向量存储）",
                "features": ["语义记忆", "向量存储", "长期记忆", "记忆检索"],
                "short_term": "会话内上下文",
                "long_term": "向量存储的语义记忆",
                "requires_redis": False
            }
        }
        
        if provider not in info_map:
            raise ValidationException(f"Unknown provider: {provider}")
        
        return info_map[provider]


class LlamaIndexMemoryProvider:
    """LlamaIndex记忆提供商实现"""
    
    def __init__(
        self,
        chat_store: Optional[Any],
        short_term_token_limit: int,
        long_term_enabled: bool
    ):
        self.chat_store = chat_store
        self.short_term_token_limit = short_term_token_limit
        self.long_term_enabled = long_term_enabled
    
    def get_memory(self, session_id: str) -> Any:
        """获取LlamaIndex ChatMemoryBuffer"""
        from llama_index.core.memory import ChatMemoryBuffer
        
        chat_store_key = f"chat_history_{session_id}"
        
        return ChatMemoryBuffer.from_defaults(
            token_limit=self.short_term_token_limit,
            chat_store=self.chat_store if self.long_term_enabled else None,
            chat_store_key=chat_store_key if self.long_term_enabled else None
        )
    
    async def clear_memory(self, session_id: str) -> bool:
        """清空记忆"""
        if self.chat_store and self.long_term_enabled:
            chat_store_key = f"chat_history_{session_id}"
            try:
                self.chat_store.delete_messages(chat_store_key)
                logger.info(f"Cleared LlamaIndex memory for session {session_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to clear memory: {e}")
                return False
        return True
    
    async def save_memory(self, session_id: str, messages: list) -> bool:
        """保存记忆（LlamaIndex自动管理）"""
        return True


class LangChainMemoryProvider:
    """LangChain记忆提供商实现"""
    
    # 最大缓存会话数，防止内存泄漏
    MAX_CACHED_SESSIONS = 1000
    
    def __init__(
        self,
        short_term_token_limit: int,
        long_term_enabled: bool,
        redis_url: Optional[str] = None
    ):
        self.short_term_token_limit = short_term_token_limit
        self.long_term_enabled = long_term_enabled
        self.redis_url = redis_url
        self._memories: dict[str, Any] = {}
        self._access_order: list[str] = []  # LRU顺序追踪
    
    def get_memory(self, session_id: str) -> Any:
        """获取LangChain记忆对象"""
        from langchain.memory import ConversationBufferWindowMemory
        from langchain_community.chat_message_histories import RedisChatMessageHistory
        
        if session_id not in self._memories:
            # LRU淘汰：如果超过最大缓存数，删除最旧的
            if len(self._memories) >= self.MAX_CACHED_SESSIONS:
                oldest_session = self._access_order.pop(0)
                if oldest_session in self._memories:
                    del self._memories[oldest_session]
                    logger.debug(f"Evicted oldest session from memory cache: {oldest_session}")
            
            # 长期记忆（Redis）
            message_history = None
            if self.long_term_enabled and self.redis_url:
                message_history = RedisChatMessageHistory(
                    session_id=session_id,
                    url=self.redis_url
                )
            
            # 短期记忆（滑动窗口）
            memory = ConversationBufferWindowMemory(
                k=self.short_term_token_limit // 100,  # 估算窗口大小
                chat_memory=message_history,
                return_messages=True
            )
            
            self._memories[session_id] = memory
            self._access_order.append(session_id)
        else:
            # 更新LRU顺序
            if session_id in self._access_order:
                self._access_order.remove(session_id)
            self._access_order.append(session_id)
        
        return self._memories[session_id]
    
    async def clear_memory(self, session_id: str) -> bool:
        """清空记忆"""
        try:
            if session_id in self._memories:
                memory = self._memories[session_id]
                memory.clear()
                del self._memories[session_id]
            
            # 清空Redis中的长期记忆
            if self.long_term_enabled and self.redis_url:
                from langchain_community.chat_message_histories import RedisChatMessageHistory
                message_history = RedisChatMessageHistory(
                    session_id=session_id,
                    url=self.redis_url
                )
                message_history.clear()
            
            logger.info(f"Cleared LangChain memory for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
            return False
    
    async def save_memory(self, session_id: str, messages: list) -> bool:
        """保存记忆（LangChain自动管理）"""
        return True


class Mem0MemoryProvider:
    """Mem0记忆提供商实现"""
    
    def __init__(
        self,
        config: dict,
        short_term_token_limit: int,
        long_term_enabled: bool
    ):
        import mem0
        self.config = config
        self.short_term_token_limit = short_term_token_limit
        self.long_term_enabled = long_term_enabled
        self.mem0_client = mem0.Mem0(config=config)
        self._short_term_memories: dict[str, list] = {}
    
    def get_memory(self, session_id: str) -> Any:
        """获取Mem0记忆对象"""
        # Mem0返回一个记忆管理器对象
        return Mem0MemoryWrapper(
            client=self.mem0_client,
            user_id=session_id,
            short_term_memory=self._short_term_memories.get(session_id, []),
            long_term_enabled=self.long_term_enabled
        )
    
    async def clear_memory(self, session_id: str) -> bool:
        """清空记忆"""
        try:
            # 清空短期记忆
            if session_id in self._short_term_memories:
                del self._short_term_memories[session_id]
            
            # 清空长期记忆
            if self.long_term_enabled:
                self.mem0_client.delete_all_memories(user_id=session_id)
            
            logger.info(f"Cleared Mem0 memory for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
            return False
    
    async def save_memory(self, session_id: str, messages: list) -> bool:
        """保存记忆到Mem0"""
        try:
            if self.long_term_enabled:
                # 将消息转换为Mem0记忆
                for message in messages:
                    self.mem0_client.add_memory(
                        user_id=session_id,
                        memory=message.get("content", ""),
                        metadata=message.get("metadata", {})
                    )
            return True
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False


class Mem0MemoryWrapper:
    """Mem0记忆包装器（用于兼容LlamaIndex接口）"""
    
    def __init__(
        self,
        client: Any,
        user_id: str,
        short_term_memory: list,
        long_term_enabled: bool
    ):
        self.client = client
        self.user_id = user_id
        self.short_term_memory = short_term_memory
        self.long_term_enabled = long_term_enabled
    
    def get_all(self) -> list:
        """获取所有记忆"""
        memories = self.short_term_memory.copy()
        
        if self.long_term_enabled:
            try:
                long_term = self.client.get_all_memories(user_id=self.user_id)
                memories.extend(long_term)
            except Exception:
                pass
        
        return memories
    
    def add(self, message: dict):
        """添加记忆"""
        self.short_term_memory.append(message)
        
        if self.long_term_enabled:
            try:
                self.client.add_memory(
                    user_id=self.user_id,
                    memory=message.get("content", ""),
                    metadata=message.get("metadata", {})
                )
            except Exception:
                pass

