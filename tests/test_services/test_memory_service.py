"""
记忆服务测试
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.memory_service import MemoryService


class TestMemoryService:
    """测试记忆服务"""
    
    def test_memory_service_singleton(self):
        """测试单例模式"""
        service1 = MemoryService()
        service2 = MemoryService()
        assert service1 is service2
    
    @patch('app.services.memory_service.MemoryProviderFactory.create_short_term_memory')
    def test_get_memory_buffer(self, mock_create_memory):
        """测试获取记忆缓冲区"""
        # 模拟记忆提供商
        mock_memory = MagicMock()
        mock_memory_buffer = MagicMock()
        mock_memory.get_chat_memory_buffer.return_value = mock_memory_buffer
        mock_create_memory.return_value = mock_memory
        
        # 重新初始化服务以使用模拟
        service = MemoryService()
        service._short_term_memory = mock_memory
        
        result = service.get_memory_buffer("test_session")
        assert result == mock_memory_buffer
        mock_memory.get_chat_memory_buffer.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.memory_service.MemoryProviderFactory.create_short_term_memory')
    async def test_clear_memory(self, mock_create_memory):
        """测试清除记忆"""
        # 模拟记忆提供商
        mock_memory = MagicMock()
        mock_memory.clear_messages = AsyncMock(return_value=True)
        mock_create_memory.return_value = mock_memory
        
        # 重新初始化服务以使用模拟
        service = MemoryService()
        service._short_term_memory = mock_memory
        service._long_term_memory = None
        
        result = await service.clear_memory("test_session")
        assert result is True
        mock_memory.clear_messages.assert_called_once_with("test_session")
    
    @pytest.mark.asyncio
    @patch('app.services.memory_service.MemoryProviderFactory.create_short_term_memory')
    @patch('app.services.memory_service.MemoryProviderFactory.create_long_term_memory')
    async def test_clear_both_memories(self, mock_create_long, mock_create_short):
        """测试清除短期和长期记忆"""
        # 模拟短期记忆
        mock_short_memory = MagicMock()
        mock_short_memory.clear_messages = AsyncMock(return_value=True)
        mock_create_short.return_value = mock_short_memory
        
        # 模拟长期记忆
        mock_long_memory = MagicMock()
        mock_long_memory.clear_messages = AsyncMock(return_value=True)
        mock_create_long.return_value = mock_long_memory
        
        # 重新初始化服务以使用模拟
        service = MemoryService()
        service._short_term_memory = mock_short_memory
        service._long_term_memory = mock_long_memory
        
        result = await service.clear_memory("test_session")
        assert result is True
        mock_short_memory.clear_messages.assert_called_once()
        mock_long_memory.clear_messages.assert_called_once()

