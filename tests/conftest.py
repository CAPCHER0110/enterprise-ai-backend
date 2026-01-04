"""
Pytest配置文件和共享fixtures
"""
import pytest
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
import redis.asyncio as aioredis

from app.main import app
from app.core.config import settings


@pytest.fixture
def client() -> Generator:
    """创建测试客户端"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    mock = AsyncMock(spec=aioredis.Redis)
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    return mock


@pytest.fixture
def mock_milvus():
    """模拟Milvus客户端"""
    mock = MagicMock()
    mock.has_collection.return_value = True
    mock.query.return_value = []
    mock.insert.return_value = MagicMock(insert_count=1)
    return mock


@pytest.fixture
def mock_llm():
    """模拟LLM"""
    mock = MagicMock()
    mock.complete.return_value = MagicMock(text="测试响应")
    mock.stream_complete = AsyncMock()
    async def stream_generator():
        yield "测"
        yield "试"
        yield "响应"
    mock.stream_complete.return_value = stream_generator()
    return mock


@pytest.fixture
def mock_embed_model():
    """模拟Embedding模型"""
    mock = MagicMock()
    mock.get_text_embedding.return_value = [0.1] * 1024
    return mock


@pytest.fixture
def sample_session_id() -> str:
    """示例会话ID"""
    return "test_session_123"


@pytest.fixture
def sample_query() -> str:
    """示例查询"""
    return "这是一个测试查询"


@pytest.fixture
def sample_document_content() -> str:
    """示例文档内容"""
    return """
    这是一个测试文档。
    它包含多个段落。
    用于测试文档处理功能。
    """


# 环境变量覆盖用于测试
@pytest.fixture(autouse=True)
def override_settings():
    """覆盖测试环境的配置"""
    original_values = {}
    
    # 保存原始值
    test_overrides = {
        'API_KEY_REQUIRED': False,
        'ENABLE_CACHE': False,
        'LOG_LEVEL': 'ERROR',
    }
    
    for key, value in test_overrides.items():
        original_values[key] = getattr(settings, key)
        setattr(settings, key, value)
    
    yield
    
    # 恢复原始值
    for key, value in original_values.items():
        setattr(settings, key, value)

