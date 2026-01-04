"""
向量数据库管理API - 查看和管理向量数据库配置
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_api_key
from app.core.config import settings
from app.utils.vector_store_providers import VectorStoreProviderFactory
from app.core.logging import logger

router = APIRouter()

@router.get("/providers")
async def list_providers():
    """
    列出所有支持的向量数据库提供商
    """
    providers = VectorStoreProviderFactory.get_supported_providers()
    provider_info = {}
    
    for provider in providers:
        try:
            provider_info[provider] = VectorStoreProviderFactory.get_provider_info(provider)
        except Exception as e:
            logger.error(f"Error getting info for provider {provider}: {e}")
            provider_info[provider] = {"error": str(e)}
    
    return {
        "supported_providers": providers,
        "current_provider": settings.VECTOR_STORE_PROVIDER,
        "providers": provider_info
    }

@router.get("/current")
async def get_current_vector_store_config():
    """
    获取当前向量数据库配置
    """
    try:
        provider_info = VectorStoreProviderFactory.get_provider_info(settings.VECTOR_STORE_PROVIDER)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    config = {
        "provider": settings.VECTOR_STORE_PROVIDER,
        "collection": settings.VECTOR_STORE_COLLECTION,
        "dimension": settings.VECTOR_STORE_DIM,
        "provider_info": provider_info
    }
    
    # 添加提供商特定的配置
    if settings.VECTOR_STORE_PROVIDER == "milvus":
        config["milvus"] = {
            "uri": settings.MILVUS_URI,
            "has_token": bool(settings.MILVUS_TOKEN)
        }
    elif settings.VECTOR_STORE_PROVIDER == "chroma":
        config["chroma"] = {
            "persist_dir": settings.CHROMA_PERSIST_DIR
        }
    elif settings.VECTOR_STORE_PROVIDER == "pinecone":
        config["pinecone"] = {
            "index": settings.PINECONE_INDEX,
            "has_api_key": bool(settings.PINECONE_API_KEY),
            "environment": settings.PINECONE_ENVIRONMENT
        }
    elif settings.VECTOR_STORE_PROVIDER == "qdrant":
        config["qdrant"] = {
            "url": settings.QDRANT_URL,
            "has_api_key": bool(settings.QDRANT_API_KEY)
        }
    
    return config

@router.get("/provider/{provider_name}")
async def get_provider_info(provider_name: str):
    """
    获取指定提供商的信息
    
    Args:
        provider_name: 提供商名称 (milvus, chroma, pinecone, qdrant)
    """
    try:
        info = VectorStoreProviderFactory.get_provider_info(provider_name.lower())
        return info
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

