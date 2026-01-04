"""
LLM管理API - 查看和管理LLM配置
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_api_key
from app.core.config import settings
from app.utils.llm_providers import LLMProviderFactory
from app.core.logging import logger

router = APIRouter()


def _mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """屏蔽敏感信息"""
    if not value:
        return ""
    if len(value) <= visible_chars * 2:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars * 2) + value[-visible_chars:]


@router.get("/providers")
async def list_providers():
    """
    列出所有支持的LLM提供商
    """
    providers = LLMProviderFactory.get_supported_providers()
    provider_info = {}
    
    for provider in providers:
        try:
            provider_info[provider] = LLMProviderFactory.get_provider_info(provider)
        except Exception as e:
            logger.error(f"Error getting info for provider {provider}: {e}")
            provider_info[provider] = {"error": str(e)}
    
    return {
        "supported_providers": providers,
        "current_provider": settings.LLM_PROVIDER,
        "providers": provider_info
    }


@router.get("/current")
async def get_current_llm_config():
    """
    获取当前LLM配置（敏感信息已屏蔽）
    """
    try:
        provider_info = LLMProviderFactory.get_provider_info(settings.LLM_PROVIDER)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL_NAME,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "api_base": settings.LLM_API_BASE if settings.LLM_API_BASE else None,
        "api_key_configured": bool(settings.LLM_API_KEY),
        "api_key_preview": _mask_sensitive(settings.LLM_API_KEY) if settings.LLM_API_KEY else None,
        "provider_info": provider_info
    }

@router.get("/provider/{provider_name}")
async def get_provider_info(provider_name: str):
    """
    获取指定提供商的信息
    
    Args:
        provider_name: 提供商名称 (openai, anthropic, vllm)
    """
    try:
        info = LLMProviderFactory.get_provider_info(provider_name.lower())
        return info
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

