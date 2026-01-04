"""
文档切片策略工厂

提供多种文档分块策略：
- 句子切片：快速，基于固定窗口
- 语义切片：更智能，基于语义相似度
"""
from typing import List, Optional
from llama_index.core.node_parser import SentenceSplitter, SemanticSplitterNodeParser
from llama_index.core.schema import Document, BaseNode
from llama_index.core import Settings as LlamaSettings
from app.core.config import settings
from app.core.logging import logger


class ChunkingStrategy:
    """
    文档切片策略工厂
    
    提供不同的文档分块策略以适应不同场景
    """
    
    # 缓存语义切片器，避免重复创建
    _semantic_splitter: Optional[SemanticSplitterNodeParser] = None
    
    @staticmethod
    def get_sentence_splitter(
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> SentenceSplitter:
        """
        基于句子的固定窗口切片
        
        Args:
            chunk_size: 分块大小（默认使用配置）
            chunk_overlap: 重叠大小（默认使用配置）
            
        Returns:
            SentenceSplitter实例
        """
        return SentenceSplitter(
            chunk_size=chunk_size or settings.CHUNK_SIZE,
            chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP
        )

    @classmethod
    def get_semantic_splitter(
        cls,
        buffer_size: int = 1,
        breakpoint_percentile_threshold: int = 95
    ) -> SemanticSplitterNodeParser:
        """
        基于语义相似度的切片
        
        使用embedding模型计算语义相似度来决定切分点
        
        Args:
            buffer_size: 缓冲区大小
            breakpoint_percentile_threshold: 断点百分位阈值
            
        Returns:
            SemanticSplitterNodeParser实例
        """
        # 使用缓存的切片器
        if cls._semantic_splitter is not None:
            return cls._semantic_splitter
        
        # 获取全局embed_model（在init_settings时已初始化）
        embed_model = LlamaSettings.embed_model
        if embed_model is None:
            raise RuntimeError(
                "Embedding model not initialized. "
                "Call init_settings() first before using semantic chunking."
            )
        
        logger.info("Creating semantic splitter with embedding model")
        cls._semantic_splitter = SemanticSplitterNodeParser(
            buffer_size=buffer_size,
            breakpoint_percentile_threshold=breakpoint_percentile_threshold,
            embed_model=embed_model
        )
        
        return cls._semantic_splitter

    @classmethod
    def split_documents(
        cls, 
        documents: List[Document], 
        mode: str = "sentence",
        **kwargs
    ) -> List[BaseNode]:
        """
        分割文档为节点
        
        Args:
            documents: 文档列表
            mode: 切片模式 ('sentence' 或 'semantic')
            **kwargs: 传递给splitter的额外参数
            
        Returns:
            节点列表
        """
        if not documents:
            logger.warning("No documents to split")
            return []
        
        if mode == "semantic":
            splitter = cls.get_semantic_splitter(**kwargs)
        else:
            splitter = cls.get_sentence_splitter(**kwargs)
        
        nodes = splitter.get_nodes_from_documents(documents)
        logger.debug(f"Split {len(documents)} documents into {len(nodes)} nodes using {mode} mode")
        
        return nodes
    
    @classmethod
    def reset(cls) -> None:
        """重置缓存的切片器（用于测试）"""
        cls._semantic_splitter = None