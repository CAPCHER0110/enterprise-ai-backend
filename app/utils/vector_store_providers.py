"""
向量数据库提供商工厂 - 支持Milvus、ChromaDB、Pinecone、Qdrant
"""
from typing import Optional, Literal, Any
from llama_index.core import StorageContext
from llama_index.core.vector_stores.types import VectorStore
from llama_index.vector_stores.milvus import MilvusVectorStore
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ValidationException


VectorStoreProvider = Literal["milvus", "chroma", "pinecone", "qdrant"]


class VectorStoreProviderFactory:
    """向量数据库提供商工厂类"""
    
    @staticmethod
    def create_vector_store(
        provider: Optional[str] = None,
        collection_name: Optional[str] = None,
        dimension: Optional[int] = None,
        **kwargs
    ) -> VectorStore:
        """
        创建向量数据库实例
        
        Args:
            provider: 向量数据库提供商 ("milvus", "chroma", "pinecone", "qdrant")
            collection_name: 集合/索引名称
            dimension: 向量维度
            **kwargs: 其他提供商特定参数
            
        Returns:
            VectorStore实例
            
        Raises:
            ValidationException: 配置错误
        """
        # 使用配置中的默认值
        provider = (provider or settings.VECTOR_STORE_PROVIDER).lower()
        collection_name = collection_name or settings.VECTOR_STORE_COLLECTION
        dimension = dimension or settings.MILVUS_DIM
        
        try:
            if provider == "milvus":
                return VectorStoreProviderFactory._create_milvus_store(
                    collection_name=collection_name,
                    dimension=dimension,
                    **kwargs
                )
            elif provider == "chroma":
                return VectorStoreProviderFactory._create_chroma_store(
                    collection_name=collection_name,
                    **kwargs
                )
            elif provider == "pinecone":
                return VectorStoreProviderFactory._create_pinecone_store(
                    index_name=collection_name,
                    dimension=dimension,
                    **kwargs
                )
            elif provider == "qdrant":
                return VectorStoreProviderFactory._create_qdrant_store(
                    collection_name=collection_name,
                    dimension=dimension,
                    **kwargs
                )
            else:
                raise ValidationException(
                    f"Unsupported vector store provider: {provider}. "
                    f"Supported providers: milvus, chroma, pinecone, qdrant"
                )
        except Exception as e:
            logger.error(f"Failed to create vector store for provider {provider}: {e}")
            raise
    
    @staticmethod
    def _create_milvus_store(
        collection_name: str,
        dimension: int,
        uri: Optional[str] = None,
        token: Optional[str] = None,
        **kwargs
    ) -> MilvusVectorStore:
        """
        创建Milvus向量存储
        
        Args:
            collection_name: 集合名称
            dimension: 向量维度
            uri: Milvus URI
            token: Milvus认证令牌
        """
        uri = uri or settings.MILVUS_URI
        token = token or (settings.MILVUS_TOKEN if settings.MILVUS_TOKEN else None)
        
        logger.info(f"Creating Milvus vector store: {collection_name} at {uri}")
        
        return MilvusVectorStore(
            uri=uri,
            token=token,
            collection_name=collection_name,
            dim=dimension,
            overwrite=False,
            **kwargs
        )
    
    @staticmethod
    def _create_chroma_store(
        collection_name: str,
        persist_dir: Optional[str] = None,
        **kwargs
    ) -> VectorStore:
        """
        创建ChromaDB向量存储
        
        Args:
            collection_name: 集合名称
            persist_dir: 持久化目录
        """
        try:
            from llama_index.vector_stores.chroma import ChromaVectorStore
            import chromadb
        except ImportError:
            raise ValidationException(
                "ChromaDB dependencies not installed. "
                "Please install: pip install chromadb llama-index-vector-stores-chroma"
            )
        
        persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        
        logger.info(f"Creating ChromaDB vector store: {collection_name} at {persist_dir}")
        
        # 创建ChromaDB客户端（使用PersistentClient支持持久化）
        try:
            chroma_client = chromadb.PersistentClient(
                path=persist_dir
            )
        except AttributeError:
            # 旧版本API
            chroma_client = chromadb.Client(
                settings=chromadb.Settings(
                    persist_directory=persist_dir,
                    anonymized_telemetry=False
                )
            )
        
        # 获取或创建集合
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        return ChromaVectorStore(chroma_collection=collection, **kwargs)
    
    @staticmethod
    def _create_pinecone_store(
        index_name: str,
        dimension: int,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
        **kwargs
    ) -> VectorStore:
        """
        创建Pinecone向量存储
        
        Args:
            index_name: 索引名称
            dimension: 向量维度
            api_key: Pinecone API密钥
            environment: Pinecone环境（旧版API）或host（新版API）
        """
        try:
            from llama_index.vector_stores.pinecone import PineconeVectorStore
            import pinecone
        except ImportError:
            raise ValidationException(
                "Pinecone dependencies not installed. "
                "Please install: pip install pinecone-client"
            )
        
        api_key = api_key or settings.PINECONE_API_KEY
        environment = environment or settings.PINECONE_ENVIRONMENT
        
        if not api_key:
            raise ValidationException("Pinecone API key is required")
        
        logger.info(f"Creating Pinecone vector store: {index_name}")
        
        # 初始化Pinecone（新版API使用Pinecone类）
        try:
            from pinecone import Pinecone as PineconeClient
            pc = PineconeClient(api_key=api_key)
            
            # 获取或创建索引
            if index_name not in [idx.name for idx in pc.list_indexes()]:
                pc.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric="cosine"
                )
            
            index = pc.Index(index_name)
        except ImportError:
            # 旧版API
            pinecone.init(api_key=api_key, environment=environment)
            
            # 获取或创建索引
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric="cosine"
                )
            
            index = pinecone.Index(index_name)
        
        return PineconeVectorStore(
            pinecone_index=index,
            **kwargs
        )
    
    @staticmethod
    def _create_qdrant_store(
        collection_name: str,
        dimension: int,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> VectorStore:
        """
        创建Qdrant向量存储
        
        Args:
            collection_name: 集合名称
            dimension: 向量维度
            url: Qdrant服务器URL
            api_key: Qdrant API密钥（可选）
        """
        try:
            from llama_index.vector_stores.qdrant import QdrantVectorStore
            from qdrant_client import QdrantClient
        except ImportError:
            raise ValidationException(
                "Qdrant dependencies not installed. "
                "Please install: pip install qdrant-client"
            )
        
        url = url or settings.QDRANT_URL
        
        if not url:
            raise ValidationException("Qdrant URL is required")
        
        logger.info(f"Creating Qdrant vector store: {collection_name} at {url}")
        
        # 创建Qdrant客户端
        client_kwargs = {"url": url}
        if api_key:
            client_kwargs["api_key"] = api_key
        
        client = QdrantClient(**client_kwargs)
        
        return QdrantVectorStore(
            collection_name=collection_name,
            client=client,
            **kwargs
        )
    
    @staticmethod
    def get_supported_providers() -> list[str]:
        """获取支持的向量数据库提供商列表"""
        return ["milvus", "chroma", "pinecone", "qdrant"]
    
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
            "milvus": {
                "name": "Milvus",
                "description": "Milvus向量数据库（开源、高性能）",
                "features": ["分布式", "高可用", "高性能", "云原生"],
                "requires_uri": True,
                "requires_token": False,
                "supports_local": True,
                "supports_cloud": True
            },
            "chroma": {
                "name": "ChromaDB",
                "description": "ChromaDB向量数据库（轻量级、易用）",
                "features": ["轻量级", "易用", "本地部署", "Python原生"],
                "requires_uri": False,
                "requires_token": False,
                "supports_local": True,
                "supports_cloud": False
            },
            "pinecone": {
                "name": "Pinecone",
                "description": "Pinecone托管向量数据库（全托管、易用）",
                "features": ["全托管", "易用", "高可用", "自动扩展"],
                "requires_uri": False,
                "requires_token": True,
                "supports_local": False,
                "supports_cloud": True
            },
            "qdrant": {
                "name": "Qdrant",
                "description": "Qdrant向量数据库（高性能、Rust实现）",
                "features": ["高性能", "Rust实现", "REST API", "Docker支持"],
                "requires_uri": True,
                "requires_token": False,
                "supports_local": True,
                "supports_cloud": True
            }
        }
        
        if provider not in info_map:
            raise ValidationException(f"Unknown provider: {provider}")
        
        return info_map[provider]

