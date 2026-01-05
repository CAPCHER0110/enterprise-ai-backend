from typing import Dict, Any, List
from pydantic import model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类
    
    使用Pydantic Settings管理环境变量和配置
    支持多种LLM、向量数据库和记忆提供商
    """
    PROJECT_NAME: str = "Enterprise AI Brain"
    API_V1_STR: str = "/api/v1"
    
    # --- 向量数据库配置 ---
    # 向量数据库提供商: "milvus", "chroma", "pinecone", "qdrant"
    VECTOR_STORE_PROVIDER: str = "milvus"  # 默认使用Milvus
    
    # Milvus配置
    MILVUS_URI: str = "./milvus_data.db"  # 开发环境用本地文件，生产环境换成 "http://milvus:19530"
    MILVUS_TOKEN: str = ""  # 如果有鉴权则填写
    MILVUS_COLLECTION: str = "enterprise_knowledge"
    MILVUS_DIM: int = 1024
    
    # ChromaDB配置
    CHROMA_PERSIST_DIR: str = "./chroma_db"  # ChromaDB持久化目录
    
    # Pinecone配置
    PINECONE_API_KEY: str = ""  # Pinecone API密钥
    PINECONE_ENVIRONMENT: str = ""  # Pinecone环境（旧版API）或留空使用新版API
    PINECONE_INDEX: str = "enterprise-knowledge"  # Pinecone索引名称
    
    # Qdrant配置
    QDRANT_URL: str = "http://localhost:6333"  # Qdrant服务器URL
    QDRANT_API_KEY: str = ""  # Qdrant API密钥（可选）
    QDRANT_COLLECTION: str = "enterprise_knowledge"  # Qdrant集合名称
    
    # 通用向量数据库配置（根据provider自动选择对应的配置）
    VECTOR_STORE_COLLECTION: str = ""  # 自动设置，或手动指定
    VECTOR_STORE_DIM: int = 1024  # 向量维度
    
    # Redis 配置 (用于长期记忆)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # --- 记忆配置 ---
    # 记忆提供商: "llamaindex", "langchain", "mem0"
    MEMORY_PROVIDER: str = "llamaindex"  # 默认使用LlamaIndex
    
    # 短期记忆配置（会话内上下文）
    SHORT_TERM_TOKEN_LIMIT: int = 3000  # 短期记忆token限制（滑动窗口）
    SHORT_TERM_MEMORY_ENABLED: bool = True  # 是否启用短期记忆
    
    # 长期记忆配置（跨会话持久化）
    LONG_TERM_MEMORY_ENABLED: bool = True  # 是否启用长期记忆
    
    # Mem0配置
    MEM0_CONFIG: Dict[str, Any] = Field(default_factory=dict)  # Mem0自定义配置
    
    # --- LLM 配置 ---
    # LLM提供商: "openai", "anthropic", "vllm"
    LLM_PROVIDER: str = "vllm"  # 默认使用vLLM
    
    # OpenAI配置
    OPENAI_API_KEY: str = ""  # OpenAI API密钥
    OPENAI_MODEL: str = "gpt-3.5-turbo"  # OpenAI模型名称
    OPENAI_API_BASE: str = ""  # 可选：自定义OpenAI兼容端点
    
    # Anthropic配置
    ANTHROPIC_API_KEY: str = ""  # Anthropic API密钥
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"  # Anthropic模型名称
    
    # vLLM配置（OpenAI兼容）
    VLLM_API_BASE: str = "http://localhost:8000/v1"  # vLLM服务器地址
    VLLM_API_KEY: str = "sk-local-dev"  # vLLM通常可以接受任意值，但必须有
    VLLM_MODEL: str = "Qwen/Qwen2.5-1.5B-Instruct"  # vLLM模型路径
    
    # 通用LLM配置（根据provider自动选择对应的配置）
    LLM_API_BASE: str = ""  # 自动设置，或手动指定
    LLM_API_KEY: str = ""  # 自动设置，或手动指定
    LLM_MODEL_NAME: str = ""  # 自动设置，或手动指定
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024
    
    # Embedding 模型 (建议使用 HuggingFace 本地运行)
    #EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_CACHE_FOLDER: str = "./model_cache"
    
    # RAG 参数
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    SIMILARITY_TOP_K: int = 5
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # 重试和超时配置
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_INITIAL_DELAY: float = 1.0
    RETRY_MAX_DELAY: float = 60.0
    REQUEST_TIMEOUT: int = 30  # 秒
    
    # 连接池配置
    REDIS_MAX_CONNECTIONS: int = 20
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    
    # 安全配置
    ALLOWED_ORIGINS: List[str] = Field(default=["*"])  # 生产环境应设置为具体域名
    API_KEY_REQUIRED: bool = False  # 生产环境应设置为True
    API_KEYS: List[str] = Field(default=["sk-admin-secret"])  # 生产环境应从环境变量或数据库读取
    
    # 性能配置
    ENABLE_CACHE: bool = True
    CACHE_TTL: int = 3600  # 秒
    CACHE_MAX_SIZE: int = 10000  # LRU缓存最大条目数
    BATCH_SIZE: int = 100  # 批量操作大小
    
    # 速率限制配置
    RATE_LIMIT_ENABLED: bool = False  # 生产环境建议启用
    RATE_LIMIT_REQUESTS: int = 100  # 时间窗口内允许的请求数
    RATE_LIMIT_WINDOW: int = 60  # 时间窗口（秒）

    # 允许 Pydantic 读取 .env 文件
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    @model_validator(mode='after')
    def _setup_all_configs(self):
        """
        统一配置验证器
        
        按顺序设置LLM和向量数据库配置，避免多个验证器的执行顺序问题
        """
        self._setup_llm_config()
        self._setup_vector_store_config()
        return self
    
    def _setup_llm_config(self) -> None:
        """根据provider自动设置LLM配置"""
        provider = self.LLM_PROVIDER.lower()
        
        if provider == "openai":
            if not self.LLM_API_KEY:
                object.__setattr__(self, 'LLM_API_KEY', self.OPENAI_API_KEY)
            if not self.LLM_MODEL_NAME:
                object.__setattr__(self, 'LLM_MODEL_NAME', self.OPENAI_MODEL)
            if not self.LLM_API_BASE:
                object.__setattr__(self, 'LLM_API_BASE', self.OPENAI_API_BASE or "")
        elif provider == "anthropic":
            if not self.LLM_API_KEY:
                object.__setattr__(self, 'LLM_API_KEY', self.ANTHROPIC_API_KEY)
            if not self.LLM_MODEL_NAME:
                object.__setattr__(self, 'LLM_MODEL_NAME', self.ANTHROPIC_MODEL)
            object.__setattr__(self, 'LLM_API_BASE', "")  # Anthropic不需要api_base
        elif provider == "vllm":
            if not self.LLM_API_KEY:
                object.__setattr__(self, 'LLM_API_KEY', self.VLLM_API_KEY)
            if not self.LLM_MODEL_NAME:
                object.__setattr__(self, 'LLM_MODEL_NAME', self.VLLM_MODEL)
            if not self.LLM_API_BASE:
                object.__setattr__(self, 'LLM_API_BASE', self.VLLM_API_BASE)
        else:
            # 如果provider未设置或无效，尝试使用vLLM配置作为默认值
            if not self.LLM_API_KEY:
                object.__setattr__(self, 'LLM_API_KEY', self.VLLM_API_KEY)
            if not self.LLM_MODEL_NAME:
                object.__setattr__(self, 'LLM_MODEL_NAME', self.VLLM_MODEL)
            if not self.LLM_API_BASE:
                object.__setattr__(self, 'LLM_API_BASE', self.VLLM_API_BASE)
    
    def _setup_vector_store_config(self) -> None:
        """根据provider自动设置向量数据库配置"""
        provider = self.VECTOR_STORE_PROVIDER.lower()
        
        collection_map = {
            "milvus": self.MILVUS_COLLECTION,
            "chroma": "enterprise_knowledge",
            "pinecone": self.PINECONE_INDEX,
            "qdrant": self.QDRANT_COLLECTION,
        }
        
        if not self.VECTOR_STORE_COLLECTION:
            collection = collection_map.get(provider, self.MILVUS_COLLECTION)
            object.__setattr__(self, 'VECTOR_STORE_COLLECTION', collection)


# 全局配置实例
settings = Settings()
