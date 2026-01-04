import os
import shutil
import tempfile
from typing import Optional
from fastapi import UploadFile
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from app.core.config import settings
from app.utils.llm_factory import get_index
from app.utils.chunking import ChunkingStrategy
from app.core.logging import logger
from app.core.retry import retry_with_backoff, RetryConfig
from app.core.exceptions import ValidationException, ConnectionException
from app.core.singleton import ThreadSafeSingleton


class IngestService(ThreadSafeSingleton):
    """
    文档摄取服务
    
    使用线程安全的单例模式
    负责文档的读取、分块、向量化和存储
    """
    _init_done: bool = False
    
    def __init__(self) -> None:
        # 避免重复初始化
        if self._init_done:
            return
        
        try:
            self.index = get_index()
        except Exception as e:
            logger.error(f"Failed to initialize index in IngestService: {e}")
            raise ConnectionException("Failed to connect to vector database", service="VectorStore")
        
        self._init_done = True
        logger.info("IngestService initialized")
    
    @classmethod
    def reset(cls) -> None:
        """重置单例（用于测试）"""
        cls.reset_instance()
        cls._init_done = False

    def _process_file_sync(
        self, 
        temp_path: str, 
        filename: str, 
        chunk_mode: str = "sentence"
    ) -> int:
        """
        同步处理逻辑，将在线程池中运行
        
        Args:
            temp_path: 临时文件路径
            filename: 原始文件名
            chunk_mode: 分块模式 ('sentence' 或 'semantic')
            
        Returns:
            处理的节点数量
            
        Raises:
            Exception: 处理失败时抛出异常
        """
        try:
            # 1. 读取文件 (自动识别 PDF/Docx/TXT)
            logger.info(f"Reading file: {filename}")
            reader = SimpleDirectoryReader(input_files=[temp_path])
            documents = reader.load_data()
            
            if not documents:
                raise ValidationException(f"No content extracted from file: {filename}")
            
            logger.info(f"Extracted {len(documents)} documents from {filename}")
            
            # 2. 智能切片
            if chunk_mode == "semantic":
                logger.info("Using semantic chunking")
                nodes = ChunkingStrategy.split_documents(documents, mode="semantic")
            else:
                logger.info("Using sentence chunking")
                splitter = SentenceSplitter(
                    chunk_size=settings.CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP
                )
                nodes = splitter.get_nodes_from_documents(documents)
            
            if not nodes:
                raise ValidationException(f"No nodes generated from file: {filename}")
            
            logger.info(f"Generated {len(nodes)} nodes from {filename}")
            
            # 3. 插入向量库（带重试）
            @retry_with_backoff(
                config=RetryConfig(max_retries=3, initial_delay=2.0),
                exceptions=(ConnectionError, TimeoutError)
            )
            def insert_nodes():
                self.index.insert_nodes(nodes)
            
            insert_nodes()
            logger.info(f"Successfully ingested {len(nodes)} nodes from {filename}")
            
            return len(nodes)
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}", exc_info=True)
            raise
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"Removed temporary file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {temp_path}: {e}")

    async def process_file(
        self, 
        file: UploadFile, 
        chunk_mode: str = "sentence"
    ) -> int:
        """
        读取文件 -> 切片 -> 向量化 -> 存入 Milvus
        
        Args:
            file: 上传的文件
            chunk_mode: 分块模式 ('sentence' 或 'semantic')
            
        Returns:
            处理的切片(Nodes)数量
            
        Raises:
            ValidationException: 文件处理失败
            ConnectionException: 数据库连接失败
        """
        # 使用临时目录保存文件
        temp_dir = tempfile.mkdtemp(prefix="ingest_")
        temp_path = os.path.join(temp_dir, file.filename or "uploaded_file")
        
        try:
            # 1. 保存临时文件 (LlamaIndex Reader 需要文件路径)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"Saved temporary file: {temp_path}")
            
            # 2. 在线程池中运行耗时的同步任务
            from fastapi.concurrency import run_in_threadpool
            return await run_in_threadpool(
                self._process_file_sync, 
                temp_path, 
                file.filename or "unknown",
                chunk_mode
            )
        except Exception as e:
            logger.error(f"Error in process_file: {e}", exc_info=True)
            raise
        finally:
            # 确保清理临时目录（即使成功也需要清理目录）
            self._cleanup_temp_dir(temp_dir)
    
    def _cleanup_temp_dir(self, temp_dir: str) -> None:
        """安全清理临时目录"""
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
