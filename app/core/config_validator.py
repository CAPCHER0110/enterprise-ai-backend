"""
配置验证器 - 启动时验证配置完整性

提供全面的配置验证，确保应用正确配置
"""
from typing import List, Tuple, Dict, Any
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ValidationException


class ConfigValidator:
    """
    配置验证器
    
    在应用启动时验证所有必需的配置是否正确设置
    """
    
    @staticmethod
    def validate() -> Tuple[bool, List[str]]:
        """
        验证配置完整性
        
        Returns:
            (is_valid, errors): 是否有效和错误/警告列表
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        # 验证LLM配置
        errors.extend(ConfigValidator._validate_llm_config())
        
        # 验证向量数据库配置
        errors.extend(ConfigValidator._validate_vector_store_config())
        
        # 验证记忆配置
        errors.extend(ConfigValidator._validate_memory_config())
        
        # 验证安全配置
        security_errors, security_warnings = ConfigValidator._validate_security_config_detailed()
        errors.extend(security_errors)
        warnings.extend(security_warnings)
        
        # 验证性能配置
        errors.extend(ConfigValidator._validate_performance_config())
        
        is_valid = len(errors) == 0
        
        # 记录结果
        if errors:
            logger.error(f"Configuration validation found {len(errors)} errors:")
            for error in errors:
                logger.error(f"  ✗ {error}")
        
        if warnings:
            logger.warning(f"Configuration validation found {len(warnings)} warnings:")
            for warning in warnings:
                logger.warning(f"  ⚠ {warning}")
        
        if is_valid and not warnings:
            logger.info("✓ Configuration validation passed")
        elif is_valid:
            logger.info("✓ Configuration validation passed with warnings")
        
        return is_valid, errors + warnings
    
    @staticmethod
    def get_config_summary() -> Dict[str, Any]:
        """
        获取配置摘要（用于诊断）
        
        Returns:
            配置摘要字典
        """
        return {
            "llm": {
                "provider": settings.LLM_PROVIDER,
                "model": settings.LLM_MODEL_NAME,
                "temperature": settings.LLM_TEMPERATURE,
                "max_tokens": settings.LLM_MAX_TOKENS,
                "has_api_key": bool(settings.LLM_API_KEY),
                "has_api_base": bool(settings.LLM_API_BASE),
            },
            "vector_store": {
                "provider": settings.VECTOR_STORE_PROVIDER,
                "collection": settings.VECTOR_STORE_COLLECTION,
                "dimension": settings.VECTOR_STORE_DIM,
            },
            "memory": {
                "provider": settings.MEMORY_PROVIDER,
                "short_term_enabled": settings.SHORT_TERM_MEMORY_ENABLED,
                "long_term_enabled": settings.LONG_TERM_MEMORY_ENABLED,
                "token_limit": settings.SHORT_TERM_TOKEN_LIMIT,
            },
            "security": {
                "api_key_required": settings.API_KEY_REQUIRED,
                "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
                "cors_origins": "restricted" if settings.ALLOWED_ORIGINS != ["*"] else "open",
            },
            "performance": {
                "cache_enabled": settings.ENABLE_CACHE,
                "cache_ttl": settings.CACHE_TTL,
                "cache_max_size": settings.CACHE_MAX_SIZE,
            }
        }
    
    @staticmethod
    def _validate_llm_config() -> List[str]:
        """验证LLM配置"""
        errors = []
        provider = settings.LLM_PROVIDER.lower()
        
        if provider == "openai":
            if not settings.OPENAI_API_KEY and not settings.LLM_API_KEY:
                errors.append("OpenAI API key is required when LLM_PROVIDER=openai")
        elif provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY and not settings.LLM_API_KEY:
                errors.append("Anthropic API key is required when LLM_PROVIDER=anthropic")
        elif provider == "vllm":
            if not settings.VLLM_API_BASE and not settings.LLM_API_BASE:
                errors.append("vLLM API base is required when LLM_PROVIDER=vllm")
        
        if not settings.LLM_MODEL_NAME:
            errors.append("LLM_MODEL_NAME is required")
        
        return errors
    
    @staticmethod
    def _validate_vector_store_config() -> List[str]:
        """验证向量数据库配置"""
        errors = []
        provider = settings.VECTOR_STORE_PROVIDER.lower()
        
        if provider == "milvus":
            if not settings.MILVUS_URI:
                errors.append("MILVUS_URI is required when VECTOR_STORE_PROVIDER=milvus")
        elif provider == "pinecone":
            if not settings.PINECONE_API_KEY:
                errors.append("PINECONE_API_KEY is required when VECTOR_STORE_PROVIDER=pinecone")
        elif provider == "qdrant":
            if not settings.QDRANT_URL:
                errors.append("QDRANT_URL is required when VECTOR_STORE_PROVIDER=qdrant")
        
        if not settings.VECTOR_STORE_COLLECTION:
            errors.append("VECTOR_STORE_COLLECTION is required")
        
        if settings.VECTOR_STORE_DIM <= 0:
            errors.append("VECTOR_STORE_DIM must be greater than 0")
        
        return errors
    
    @staticmethod
    def _validate_memory_config() -> List[str]:
        """验证记忆配置"""
        errors = []
        provider = settings.MEMORY_PROVIDER.lower()
        
        if provider in ["llamaindex", "langchain"]:
            if settings.LONG_TERM_MEMORY_ENABLED and not settings.REDIS_URL:
                errors.append("REDIS_URL is required when LONG_TERM_MEMORY_ENABLED=true")
        
        if settings.SHORT_TERM_TOKEN_LIMIT <= 0:
            errors.append("SHORT_TERM_TOKEN_LIMIT must be greater than 0")
        
        return errors
    
    @staticmethod
    def _validate_security_config_detailed() -> Tuple[List[str], List[str]]:
        """
        验证安全配置
        
        Returns:
            (errors, warnings): 错误和警告列表
        """
        errors = []
        warnings = []
        
        # CORS配置
        if settings.ALLOWED_ORIGINS == ["*"]:
            warnings.append("ALLOWED_ORIGINS is set to '*' - not recommended for production")
        
        # API密钥配置
        if not settings.API_KEY_REQUIRED:
            warnings.append("API_KEY_REQUIRED is false - API is publicly accessible")
        
        if settings.API_KEY_REQUIRED and not settings.API_KEYS:
            errors.append("API_KEYS is required when API_KEY_REQUIRED=true")
        
        if settings.API_KEY_REQUIRED and settings.API_KEYS:
            # 检查API密钥强度
            for i, key in enumerate(settings.API_KEYS):
                if len(key) < 16:
                    warnings.append(f"API key {i+1} is too short (< 16 chars) - consider using longer keys")
        
        # 速率限制
        if not settings.RATE_LIMIT_ENABLED:
            warnings.append("RATE_LIMIT_ENABLED is false - API may be vulnerable to abuse")
        
        return errors, warnings
    
    @staticmethod
    def _validate_performance_config() -> List[str]:
        """验证性能配置"""
        errors = []
        
        if settings.CACHE_TTL <= 0:
            errors.append("CACHE_TTL must be greater than 0")
        
        if settings.CACHE_MAX_SIZE <= 0:
            errors.append("CACHE_MAX_SIZE must be greater than 0")
        
        if settings.BATCH_SIZE <= 0:
            errors.append("BATCH_SIZE must be greater than 0")
        
        if settings.REQUEST_TIMEOUT <= 0:
            errors.append("REQUEST_TIMEOUT must be greater than 0")
        
        return errors
    
    @staticmethod
    def validate_and_raise() -> None:
        """验证配置并在失败时抛出异常"""
        is_valid, messages = ConfigValidator.validate()
        if not is_valid:
            # 只包含错误，不包含警告
            errors = [m for m in messages if not m.startswith("⚠")]
            if errors:
                error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
                raise ValidationException(error_msg)

