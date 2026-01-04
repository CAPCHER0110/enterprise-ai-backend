"""
配置测试
"""
import pytest
from app.core.config import settings
from app.core.config_validator import ConfigValidator


class TestSettings:
    """测试配置类"""
    
    def test_settings_load(self):
        """测试配置加载"""
        assert settings.PROJECT_NAME
        assert settings.API_V1_STR
        assert settings.LOG_LEVEL
    
    def test_llm_provider_config(self):
        """测试LLM提供商配置"""
        assert settings.LLM_PROVIDER in ["openai", "anthropic", "vllm"]
        assert settings.LLM_MODEL_NAME
        assert settings.LLM_TEMPERATURE >= 0
        assert settings.LLM_MAX_TOKENS > 0
    
    def test_vector_store_config(self):
        """测试向量数据库配置"""
        assert settings.VECTOR_STORE_PROVIDER in ["milvus", "chroma", "pinecone", "qdrant"]
        assert settings.VECTOR_STORE_COLLECTION
        assert settings.VECTOR_STORE_DIM > 0
    
    def test_memory_config(self):
        """测试记忆配置"""
        assert settings.MEMORY_PROVIDER in ["llamaindex", "langchain", "mem0"]
        assert settings.SHORT_TERM_TOKEN_LIMIT > 0
    
    def test_retry_config(self):
        """测试重试配置"""
        assert settings.RETRY_MAX_ATTEMPTS > 0
        assert settings.RETRY_INITIAL_DELAY > 0
        assert settings.RETRY_MAX_DELAY >= settings.RETRY_INITIAL_DELAY
    
    def test_security_config(self):
        """测试安全配置"""
        assert isinstance(settings.ALLOWED_ORIGINS, list)
        assert isinstance(settings.API_KEY_REQUIRED, bool)
        if settings.API_KEY_REQUIRED:
            assert len(settings.API_KEYS) > 0


class TestConfigValidator:
    """测试配置验证器"""
    
    def test_validate_returns_tuple(self):
        """测试验证返回元组"""
        result = ConfigValidator.validate()
        assert isinstance(result, tuple)
        assert len(result) == 2
        is_valid, errors = result
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    
    def test_validate_llm_config(self):
        """测试LLM配置验证"""
        errors = ConfigValidator._validate_llm_config()
        assert isinstance(errors, list)
    
    def test_validate_vector_store_config(self):
        """测试向量数据库配置验证"""
        errors = ConfigValidator._validate_vector_store_config()
        assert isinstance(errors, list)
    
    def test_validate_memory_config(self):
        """测试记忆配置验证"""
        errors = ConfigValidator._validate_memory_config()
        assert isinstance(errors, list)
    
    def test_validate_security_config(self):
        """测试安全配置验证"""
        errors = ConfigValidator._validate_security_config()
        assert isinstance(errors, list)

