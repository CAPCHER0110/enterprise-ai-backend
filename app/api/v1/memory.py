"""
记忆管理API - 查看和管理记忆配置
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_api_key
from app.core.config import settings
from app.utils.memory_providers import MemoryProviderFactory
from app.services.memory_service import MemoryService
from app.core.logging import logger

router = APIRouter()

@router.get("/providers")
async def list_providers():
    """
    列出所有支持的记忆提供商
    """
    providers = MemoryProviderFactory.get_supported_providers()
    provider_info = {}
    
    for provider in providers:
        try:
            provider_info[provider] = MemoryProviderFactory.get_provider_info(provider)
        except Exception as e:
            logger.error(f"Error getting info for provider {provider}: {e}")
            provider_info[provider] = {"error": str(e)}
    
    return {
        "supported_providers": providers,
        "current_provider": settings.MEMORY_PROVIDER,
        "short_term_enabled": settings.SHORT_TERM_MEMORY_ENABLED,
        "long_term_enabled": settings.LONG_TERM_MEMORY_ENABLED,
        "providers": provider_info
    }

@router.get("/current")
async def get_current_memory_config():
    """
    获取当前记忆配置
    """
    try:
        provider_info = MemoryProviderFactory.get_provider_info(settings.MEMORY_PROVIDER)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "provider": settings.MEMORY_PROVIDER,
        "short_term": {
            "enabled": settings.SHORT_TERM_MEMORY_ENABLED,
            "token_limit": settings.SHORT_TERM_TOKEN_LIMIT
        },
        "long_term": {
            "enabled": settings.LONG_TERM_MEMORY_ENABLED
        },
        "provider_info": provider_info
    }

@router.get("/provider/{provider_name}")
async def get_provider_info(provider_name: str):
    """
    获取指定提供商的信息
    
    Args:
        provider_name: 提供商名称 (llamaindex, langchain, mem0)
    """
    try:
        info = MemoryProviderFactory.get_provider_info(provider_name.lower())
        return info
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/session/{session_id}", dependencies=[Depends(get_api_key)])
async def clear_session_memory(session_id: str):
    """
    清空指定会话的记忆
    
    需要API密钥认证
    """
    try:
        memory_service = MemoryService()
        result = await memory_service.clear_memory(session_id)
        
        if result:
            return {
                "status": "success",
                "message": f"Memory cleared for session {session_id}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear memory"
            )
    except Exception as e:
        logger.error(f"Error clearing memory for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

