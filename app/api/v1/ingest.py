"""
文档摄取API端点 - 处理文档上传和索引
"""
import os
from typing import List, Set
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from app.services.ingest_service import IngestService
from app.core.logging import logger
from app.core.exceptions import ValidationException, AppException
from app.core.security import get_api_key
from app.core.config import settings

router = APIRouter()

# 允许的文件扩展名
ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".html"}

# 最大文件大小（字节）
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def get_ingest_service() -> IngestService:
    """依赖注入：获取IngestService实例"""
    return IngestService()


async def validate_file(file: UploadFile) -> int:
    """
    验证上传的文件
    
    Args:
        file: 上传的文件
        
    Returns:
        文件大小（字节）
        
    Raises:
        ValidationException: 如果文件无效
    """
    if not file.filename:
        raise ValidationException("Filename is empty")
    
    # 检查文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValidationException(
            f"File type '{file_ext}' not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    
    # 检查文件大小
    # 方法1：使用file.size属性（如果可用）
    if hasattr(file, 'size') and file.size is not None:
        if file.size > MAX_FILE_SIZE:
            raise ValidationException(
                f"File size ({file.size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            )
        return file.size
    
    # 方法2：读取内容长度头
    content_length = file.headers.get('content-length') if hasattr(file, 'headers') else None
    if content_length:
        size = int(content_length)
        if size > MAX_FILE_SIZE:
            raise ValidationException(
                f"File size ({size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            )
        return size
    
    # 方法3：通过seek获取大小
    try:
        file.file.seek(0, 2)  # 移到文件末尾
        size = file.file.tell()
        file.file.seek(0)  # 重置到开头
        
        if size > MAX_FILE_SIZE:
            raise ValidationException(
                f"File size ({size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            )
        return size
    except Exception:
        # 如果无法确定大小，允许上传但记录警告
        logger.warning(f"Could not determine file size for {file.filename}")
        return 0

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    chunk_mode: str = Query("sentence", description="Chunking mode: 'sentence' or 'semantic'"),
    service: IngestService = Depends(get_ingest_service),
    # api_key: str = Depends(get_api_key)  # 可选：需要API密钥
):
    """
    上传文档并建立索引
    
    支持的文件格式: PDF, DOCX, TXT, MD, CSV, JSON, HTML
    最大文件大小: 50MB
    """
    # 验证文件
    try:
        file_size = await validate_file(file)
        logger.info(f"Received file: {file.filename}, size: {file_size} bytes")
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message)
    
    # 验证分块模式
    if chunk_mode not in ["sentence", "semantic"]:
        raise HTTPException(
            status_code=400,
            detail="chunk_mode must be 'sentence' or 'semantic'"
        )
    
    try:
        logger.info(f"Processing file upload: {file.filename}")
        node_count = await service.process_file(file, chunk_mode=chunk_mode)
        
        logger.info(f"Successfully indexed {node_count} nodes from {file.filename}")
        
        return {
            "filename": file.filename,
            "status": "success",
            "indexed_nodes": node_count,
            "chunk_mode": chunk_mode,
            "message": "Document processed and indexed successfully."
        }
    except ValidationException as e:
        logger.warning(f"Validation error during file upload: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except AppException as e:
        logger.error(f"Application error during file upload: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing the file")