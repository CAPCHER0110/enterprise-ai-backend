"""
LLM提供商工厂 - 支持OpenAI、Anthropic、vLLM

提供统一的LLM创建接口，支持多种提供商和配置选项
"""
from typing import Optional, Literal, Union
from llama_index.core.base.llms.types import LLMMetadata
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ValidationException, ConnectionException


LLMProvider = Literal["openai", "anthropic", "vllm"]


class LLMProviderFactory:
    """
    LLM提供商工厂类
    
    支持创建和管理不同LLM提供商的实例
    """
    
    @staticmethod
    def create_llm(
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> Union[OpenAI, Anthropic]:
        """
        创建LLM实例
        
        Args:
            provider: LLM提供商 ("openai", "anthropic", "vllm")
            model: 模型名称
            api_key: API密钥
            api_base: API基础URL（用于vLLM或自定义OpenAI兼容端点）
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 请求超时时间（秒）
            
        Returns:
            LLM实例
            
        Raises:
            ValidationException: 配置错误
            ConnectionException: 连接失败
        """
        # 使用配置中的默认值
        provider = (provider or settings.LLM_PROVIDER).lower()
        model = model or settings.LLM_MODEL_NAME
        api_key = api_key or settings.LLM_API_KEY
        api_base = api_base or settings.LLM_API_BASE
        temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        timeout = timeout or settings.REQUEST_TIMEOUT
        
        # 验证必要参数
        if not model:
            raise ValidationException("Model name is required", field="model")
        
        try:
            if provider == "openai":
                if not api_key:
                    raise ValidationException(
                        "OpenAI API key is required", 
                        field="api_key"
                    )
                return LLMProviderFactory._create_openai_llm(
                    model=model,
                    api_key=api_key,
                    api_base=api_base if api_base else None,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
            elif provider == "anthropic":
                if not api_key:
                    raise ValidationException(
                        "Anthropic API key is required", 
                        field="api_key"
                    )
                return LLMProviderFactory._create_anthropic_llm(
                    model=model,
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
            elif provider == "vllm":
                if not api_base:
                    raise ValidationException(
                        "vLLM API base URL is required", 
                        field="api_base"
                    )
                return LLMProviderFactory._create_vllm_llm(
                    model=model,
                    api_key=api_key or "not-needed",  # vLLM通常不需要真正的key
                    api_base=api_base,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
            else:
                raise ValidationException(
                    f"Unsupported LLM provider: {provider}. "
                    f"Supported providers: openai, anthropic, vllm"
                )
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to create LLM instance for provider {provider}: {e}")
            raise ConnectionException(str(e), service=f"LLM:{provider}")
    
    @staticmethod
    def _create_openai_llm(
        model: str,
        api_key: str,
        api_base: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        timeout: int = 30
    ) -> OpenAI:
        """
        创建OpenAI LLM实例
        
        支持：
        - OpenAI官方API (api_base=None)
        - vLLM或其他OpenAI兼容API (指定api_base)
        """
        llm_kwargs = {
            "model": model,
            "api_key": api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout
        }
        
        # 如果指定了api_base，使用自定义端点（如vLLM）
        if api_base:
            llm_kwargs["api_base"] = api_base
            logger.info(f"Creating OpenAI-compatible LLM: {model} at {api_base}")
        else:
            logger.info(f"Creating OpenAI LLM: {model}")
        
        return OpenAI(**llm_kwargs)
    
    @staticmethod
    def _create_anthropic_llm(
        model: str,
        api_key: str,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        timeout: int = 30
    ) -> Anthropic:
        """
        创建Anthropic Claude LLM实例
        """
        logger.info(f"Creating Anthropic LLM: {model}")
        
        return Anthropic(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
    
    @staticmethod
    def _create_vllm_llm(
        model: str,
        api_key: str,
        api_base: str,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        timeout: int = 30
    ) -> OpenAI:
        """
        创建vLLM LLM实例（通过OpenAI兼容接口）
        
        vLLM使用OpenAI兼容的API，所以使用OpenAI客户端
        """
        if not api_base:
            raise ValidationException(
                "api_base is required for vLLM provider. "
                "Please set LLM_API_BASE in configuration."
            )
        
        logger.info(f"Creating vLLM LLM: {model} at {api_base}")
        
        return OpenAI(
            model=model,
            api_base=api_base,
            api_key=api_key,  # vLLM通常可以接受任意值，但必须有
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
    
    @staticmethod
    def get_supported_providers() -> list[str]:
        """获取支持的LLM提供商列表"""
        return ["openai", "anthropic", "vllm"]
    
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
            "openai": {
                "name": "OpenAI",
                "description": "OpenAI官方API",
                "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                "requires_api_key": True,
                "requires_api_base": False,
                "supports_custom_endpoint": True
            },
            "anthropic": {
                "name": "Anthropic",
                "description": "Anthropic Claude API",
                "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
                "requires_api_key": True,
                "requires_api_base": False,
                "supports_custom_endpoint": False
            },
            "vllm": {
                "name": "vLLM",
                "description": "vLLM推理服务器（OpenAI兼容）",
                "models": ["自定义模型路径，如 Qwen/Qwen2.5-1.5B-Instruct"],
                "requires_api_key": True,
                "requires_api_base": True,
                "supports_custom_endpoint": True
            }
        }
        
        if provider not in info_map:
            raise ValidationException(f"Unknown provider: {provider}")
        
        return info_map[provider]

