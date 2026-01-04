from typing import Optional, Any
from app.core.config import settings
from app.core.logging import logger
from app.core.retry import retry_with_backoff, RetryConfig
from app.utils.memory_providers import MemoryProviderFactory, MemoryInterface
from app.core.singleton import ThreadSafeSingleton


class MemoryService(ThreadSafeSingleton):
    """
    记忆服务 - 支持多种记忆提供商（LlamaIndex、LangChain、Mem0）
    
    使用线程安全的单例模式
    """
    _memory_provider: Optional[MemoryInterface] = None
    _init_done: bool = False
    
    def __init__(self) -> None:
        if not self._init_done:
            self._initialize()
            self._init_done = True
    
    def _initialize(self):
        """延迟初始化记忆提供商"""
        if self._memory_provider is None:
            try:
                self._memory_provider = MemoryProviderFactory.create_memory_provider(
                    provider=settings.MEMORY_PROVIDER,
                    short_term_token_limit=settings.SHORT_TERM_TOKEN_LIMIT,
                    long_term_enabled=settings.LONG_TERM_MEMORY_ENABLED
                )
                logger.info(
                    f"Memory provider initialized: {settings.MEMORY_PROVIDER} "
                    f"(short_term={settings.SHORT_TERM_MEMORY_ENABLED}, "
                    f"long_term={settings.LONG_TERM_MEMORY_ENABLED})"
                )
            except Exception as e:
                logger.error(f"Failed to initialize memory provider: {e}")
                raise

    @retry_with_backoff(
        config=RetryConfig(max_retries=2, initial_delay=0.5),
        exceptions=(ConnectionError, TimeoutError)
    )
    def get_memory(self, session_id: str, token_limit: Optional[int] = None) -> Any:
        """
        获取指定 Session 的记忆对象
        
        Args:
            session_id: 会话ID
            token_limit: Token限制（可选，覆盖默认配置）
            
        Returns:
            记忆对象（根据提供商类型不同）
        """
        if self._memory_provider is None:
            raise RuntimeError("Memory provider not initialized")
        
        try:
            memory = self._memory_provider.get_memory(session_id)
            
            # 如果指定了自定义token_limit且是LlamaIndex，需要重新创建
            if token_limit and settings.MEMORY_PROVIDER == "llamaindex":
                try:
                    from llama_index.core.memory import ChatMemoryBuffer
                    # 获取原始memory的chat_store
                    if hasattr(memory, 'chat_store'):
                        chat_store = memory.chat_store
                        chat_store_key = getattr(memory, '_chat_store_key', None)
                        if not chat_store_key:
                            # 尝试从memory中提取key
                            chat_store_key = f"chat_history_{session_id}"
                        return ChatMemoryBuffer.from_defaults(
                            token_limit=token_limit,
                            chat_store=chat_store,
                            chat_store_key=chat_store_key
                        )
                except ImportError:
                    # 如果无法导入，返回原始memory
                    pass
            
            return memory
        except Exception as e:
            logger.error(f"Failed to get memory for session {session_id}: {e}")
            raise
    
    def get_memory_buffer(self, session_id: str, token_limit: int = 3000):
        """
        获取记忆Buffer（向后兼容方法，主要用于LlamaIndex）
        
        Args:
            session_id: 会话ID
            token_limit: Token限制
            
        Returns:
            ChatMemoryBuffer实例（LlamaIndex）或其他记忆对象
        """
        return self.get_memory(session_id, token_limit)
    
    @retry_with_backoff(
        config=RetryConfig(max_retries=2, initial_delay=0.5),
        exceptions=(ConnectionError, TimeoutError)
    )
    async def clear_memory(self, session_id: str) -> bool:
        """
        清空指定会话的记忆
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功
        """
        if self._memory_provider is None:
            raise RuntimeError("Memory provider not initialized")
        
        try:
            result = await self._memory_provider.clear_memory(session_id)
            logger.info(f"Cleared memory for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to clear memory for session {session_id}: {e}")
            return False
    
    async def save_memory(self, session_id: str, messages: list) -> bool:
        """
        保存记忆（用于长期记忆持久化）
        
        Args:
            session_id: 会话ID
            messages: 消息列表
            
        Returns:
            是否成功
        """
        if self._memory_provider is None:
            raise RuntimeError("Memory provider not initialized")
        
        try:
            result = await self._memory_provider.save_memory(session_id, messages)
            return result
        except Exception as e:
            logger.error(f"Failed to save memory for session {session_id}: {e}")
            return False
    
    @classmethod
    def reset(cls) -> None:
        """重置单例（用于测试）"""
        cls.reset_instance()
        cls._memory_provider = None
        cls._init_done = False