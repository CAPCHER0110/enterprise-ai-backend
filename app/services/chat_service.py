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
from llama_index.core import PromptTemplate
from llama_index.core.base.response.schema import Response # 引入 Response 类型
from llama_index.core.memory import ChatMemoryBuffer


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

    def _create_chat_engine(
        self,
        session_id: str,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        memory = self._get_chat_memory(session_id)
            
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
        
        # ------------------------------------------------------------------
        # 【关键优化】定义防呆 Prompt (防止小模型复读)
        # ------------------------------------------------------------------
        
        # Condense Prompt: 强制模型只改写，不回答，不加废话
        custom_condense_prompt = PromptTemplate(
            template=(
                "任务：将用户的【后续问题】重写为一个独立的搜索查询。\n"
                "规则：\n"
                "1. 仅输出重写后的句子，不要回答问题。\n"
                "2. 结合【历史摘要】将指代词（如'它'、'这个'）替换为具体名称。\n"
                "3. 如果问题已经独立，请原样输出。\n\n"
                "【历史摘要】：\n{chat_history}\n\n"
                "【后续问题】：{question}\n\n"
                "【独立查询】： " 
            )
        )

        # QA Prompt: 强制模型基于上下文回答，防止幻觉
        text_qa_template = PromptTemplate(
            template=(
                "背景信息如下：\n"
                "---------------------\n"
                "{context_str}\n"
                "---------------------\n"
                "请严格基于上述背景信息回答用户的问题。\n"
                "如果背景信息中不包含答案，请直接回答“我无法回答该问题”，不要编造。\n\n"
                "用户问题：{query_str}\n"
                "你的回答："
            )
        )

        # 初始化聊天引擎参数
        chat_engine_kwargs = {
            "chat_mode": "condense_plus_context", # 或者你目前使用的 "simple" / "context"
            "memory": memory,
            "similarity_top_k": settings.SIMILARITY_TOP_K,
            "verbose": True,
            "condense_question_prompt": custom_condense_prompt,
            "text_qa_template": text_qa_template,
            "skip_condense": False
        }
        
        if custom_llm:
            chat_engine_kwargs["llm"] = custom_llm
            
        return self.index.as_chat_engine(**chat_engine_kwargs)

    # --- 修改：chat_stream 使用提取的逻辑 ---
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
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if not session_id or not session_id.strip():
            raise ValueError("Session ID cannot be empty")
        
        try:
            # 使用提取的方法创建引擎
            chat_engine = self._create_chat_engine(session_id, llm_provider, llm_model, temperature)
            
            # 执行流式推理
            streaming_response = await chat_engine.astream_chat(query)
            
            # 这里的 () 是你之前修复的 bug
            async for token in streaming_response.async_response_gen():
                yield token
                
        except Exception as e:
            logger.error(f"Error in chat_stream for session {session_id}: {e}", exc_info=True)
            raise

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
            # 使用提取的方法创建引擎
            chat_engine = self._create_chat_engine(session_id, llm_provider, llm_model, temperature)
            
            # 执行流式推理
            streaming_response = await chat_engine.astream_chat(query)
            
            # 这里的 () 是你之前修复的 bug
            async for token in streaming_response.async_response_gen():
                yield token
                
        except Exception as e:
            logger.error(f"Error in chat_stream for session {session_id}: {e}", exc_info=True)
            raise


    # --- 新增：chat 方法用于非流式对话 ---
    @retry_with_backoff(
        config=RetryConfig(max_retries=2, initial_delay=1.0),
        exceptions=(ConnectionError, TimeoutError, ValueError)
    )
    async def chat(
        self,
        query: str,
        session_id: str,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Response:
        """非流式对话"""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if not session_id or not session_id.strip():
            raise ValueError("Session ID cannot be empty")

        try:
            chat_engine = self._create_chat_engine(session_id, llm_provider, llm_model, temperature)

            # 使用 achat 获取完整响应
            response = await chat_engine.achat(query)
            return response

        except Exception as e:
            logger.error(f"Error in chat for session {session_id}: {e}", exc_info=True)
            raise
