from typing import Optional, AsyncGenerator, Any, Union
from llama_index.core import VectorStoreIndex
from llama_index.core.llms import LLM as BaseLLM
from llama_index.core.memory import ChatMemoryBuffer
from app.core.config import settings
from app.utils.llm_factory import get_index, create_llm_instance
from app.core.logging import logger
from app.services.memory_service import MemoryService
from app.core.retry import retry_with_backoff, RetryConfig
from app.core.singleton import ThreadSafeSingleton


class ChatService(ThreadSafeSingleton):
    """
    聊天服务 - 处理RAG对话
    
    使用线程安全的单例模式，确保并发安全
    """
    _init_done: bool = False
    
    def __init__(self) -> None:
        # 避免重复初始化
        if self._init_done:
            return
        
        # 使用单例索引，避免重复连接数据库
        try:
            self.index = get_index()
        except Exception as e:
            logger.error(f"Failed to initialize index: {e}")
            raise
        self.memory_service = MemoryService()
        self._init_done = True
        logger.info("ChatService initialized")

    def _get_chat_memory(
        self, 
        session_id: str, 
        token_limit: Optional[int] = None
    ) -> Union[ChatMemoryBuffer, Any]:
        """
        获取记忆对象（支持多种记忆提供商）
        
        Args:
            session_id: 会话ID
            token_limit: Token限制（可选）
            
        Returns:
            ChatMemoryBuffer（LlamaIndex）或其他记忆对象
        """
        return self.memory_service.get_memory(
            session_id=session_id,
            token_limit=token_limit or settings.SHORT_TERM_TOKEN_LIMIT
        )
    
    @classmethod
    def reset(cls) -> None:
        """重置单例（用于测试）"""
        cls.reset_instance()
        cls._init_done = False

    @retry_with_backoff(
        config=RetryConfig(max_retries=2, initial_delay=1.0),
        exceptions=(ConnectionError, TimeoutError, ValueError)
    )
    async def chat_stream(
        self, 
        query: str, 
        session_id: str,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        核心流式对话逻辑 (Async)
        
        Args:
            query: 用户查询
            session_id: 会话ID
            llm_provider: 可选的LLM提供商（覆盖默认配置）
            llm_model: 可选的LLM模型（覆盖默认配置）
            temperature: 可选的温度参数（覆盖默认配置）
            
        Yields:
            流式返回的token字符串
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if not session_id or not session_id.strip():
            raise ValueError("Session ID cannot be empty")
        
        try:
            memory = self._get_chat_memory(session_id)
            
            # 如果指定了自定义LLM参数，创建临时LLM实例
            custom_llm: Optional[BaseLLM] = None
            if llm_provider or llm_model or temperature is not None:
                logger.info(
                    f"Using custom LLM: provider={llm_provider}, "
                    f"model={llm_model}, temperature={temperature}"
                )
                custom_llm = create_llm_instance(
                    provider=llm_provider,
                    model=llm_model,
                    temperature=temperature
                )
            
            # 初始化聊天引擎
            # condense_plus_context 模式：先总结历史，再检索
            chat_engine_kwargs = {
                "chat_mode": "condense_plus_context",
                "memory": memory,
                "similarity_top_k": settings.SIMILARITY_TOP_K,
                "verbose": False  # 生产环境关闭详细日志
            }
            
            # 如果指定了自定义LLM，使用它
            if custom_llm:
                chat_engine_kwargs["llm"] = custom_llm
            
            chat_engine = self.index.as_chat_engine(**chat_engine_kwargs)
            
            # 执行流式推理 (Async)
            streaming_response = await chat_engine.astream_chat(query)
            
            # 生成器：逐步返回 Token
            async for token in streaming_response.async_response_gen:
                yield token
                
        except Exception as e:
            logger.error(f"Error in chat_stream for session {session_id}: {e}", exc_info=True)
            raise
