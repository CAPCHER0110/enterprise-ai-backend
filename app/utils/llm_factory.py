from typing import Optional, Union
from llama_index.core.base.llms.types import BaseLLM
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings as LlamaSettings
from llama_index.core import VectorStoreIndex, StorageContext
from app.core.config import settings
from app.core.logging import logger
from app.core.retry import retry_with_backoff, RetryConfig
from app.utils.llm_providers import LLMProviderFactory
from app.utils.vector_store_providers import VectorStoreProviderFactory

_index: Optional[VectorStoreIndex] = None
_embed_model: Optional[HuggingFaceEmbedding] = None
_llm: Optional[BaseLLM] = None

def init_settings():
    """
    全局初始化 LlamaIndex Settings
    支持多种LLM提供商：OpenAI、Anthropic、vLLM
    """
    global _embed_model, _llm
    
    logger.info("Initializing LlamaIndex Settings...")
    
    try:
        # 1. 初始化 Embedding 模型 (本地运行)
        # cache_folder 可以指定模型下载位置
        _embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL_NAME,
            cache_folder=settings.EMBEDDING_CACHE_FOLDER
        )
        logger.info(f"Embedding model {settings.EMBEDDING_MODEL_NAME} initialized")
        
        # 2. 初始化 LLM（使用工厂模式支持多种提供商）
        _llm = LLMProviderFactory.create_llm(
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL_NAME,
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE if settings.LLM_API_BASE else None,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.REQUEST_TIMEOUT
        )
        logger.info(
            f"LLM initialized: provider={settings.LLM_PROVIDER}, "
            f"model={settings.LLM_MODEL_NAME}"
        )
        
        # 3. 绑定到全局设置
        LlamaSettings.embed_model = _embed_model
        LlamaSettings.llm = _llm
        logger.info("LlamaIndex Settings initialized successfully")
        return LlamaSettings
    except Exception as e:
        logger.error(f"Failed to initialize LlamaIndex Settings: {e}", exc_info=True)
        raise

def get_llm() -> BaseLLM:
    """
    获取当前LLM实例
    
    Returns:
        LLM实例
    """
    global _llm
    if _llm is None:
        raise RuntimeError("LLM not initialized. Call init_settings() first.")
    return _llm

def create_llm_instance(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> BaseLLM:
    """
    创建新的LLM实例（不替换全局实例）
    
    Args:
        provider: LLM提供商
        model: 模型名称
        **kwargs: 其他LLM参数
        
    Returns:
        新的LLM实例
    """
    return LLMProviderFactory.create_llm(
        provider=provider,
        model=model,
        **kwargs
    )

@retry_with_backoff(
    config=RetryConfig(max_retries=3, initial_delay=2.0),
    exceptions=(ConnectionError, TimeoutError, ValueError)
)
def get_index() -> VectorStoreIndex:
    """
    获取向量索引（单例模式）
    支持多种向量数据库：Milvus、ChromaDB、Pinecone、Qdrant
    
    Returns:
        VectorStoreIndex实例
        
    Raises:
        ConnectionError: 无法连接到向量数据库
        ValueError: 配置错误
    """
    global _index
    
    if _index is None:
        logger.info(
            f"Initializing Vector Store: provider={settings.VECTOR_STORE_PROVIDER}, "
            f"collection={settings.VECTOR_STORE_COLLECTION}"
        )
        
        try:
            # 使用工厂模式创建向量存储
            vector_store = VectorStoreProviderFactory.create_vector_store(
                provider=settings.VECTOR_STORE_PROVIDER,
                collection_name=settings.VECTOR_STORE_COLLECTION,
                dimension=settings.VECTOR_STORE_DIM
            )
            
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # 加载索引 (如果库里没数据，这里不会报错，只是索引默认建立)
            # 注意: 这里假设 Collection 已经存在或者自动创建。
            # 如果需要从大量文档第一次构建，通常使用 from_documents，但既然是 Service，
            # 我们假设是加载已有的 Store。
            _index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context
            )
            logger.info(
                f"Vector Store Index initialized successfully: "
                f"provider={settings.VECTOR_STORE_PROVIDER}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vector Store Index: {e}", exc_info=True)
            raise
    
    return _index

def reset_index():
    """重置索引（用于测试或重新初始化）"""
    global _index
    _index = None
    logger.info("Vector Store Index reset")

def create_vector_store_instance(
    provider: Optional[str] = None,
    collection_name: Optional[str] = None,
    **kwargs
):
    """
    创建新的向量存储实例（不替换全局实例）
    
    Args:
        provider: 向量数据库提供商
        collection_name: 集合名称
        **kwargs: 其他向量存储参数
        
    Returns:
        新的VectorStore实例
    """
    return VectorStoreProviderFactory.create_vector_store(
        provider=provider,
        collection_name=collection_name,
        **kwargs
    )
