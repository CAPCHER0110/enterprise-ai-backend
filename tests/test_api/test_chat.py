"""
聊天API测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


class TestChatAPI:
    """测试聊天API"""
    
    @patch('app.services.chat_service.ChatService.chat_stream')
    def test_chat_completions_valid_request(self, mock_chat_stream, client: TestClient):
        """测试有效的聊天请求"""
        # 模拟流式响应
        async def mock_stream():
            yield "测"
            yield "试"
            yield "响应"
        
        mock_chat_stream.return_value = mock_stream()
        
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "query": "你好",
                "session_id": "test_session_123",
                "stream": True
            }
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_chat_completions_invalid_query(self, client: TestClient):
        """测试无效查询"""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "query": "",  # 空查询
                "session_id": "test_session_123",
                "stream": True
            }
        )
        
        # 应该返回验证错误
        assert response.status_code in [400, 422]
    
    def test_chat_completions_invalid_session_id(self, client: TestClient):
        """测试无效会话ID"""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "query": "你好",
                "session_id": "invalid@session#id",  # 包含非法字符
                "stream": True
            }
        )
        
        # 应该返回验证错误
        assert response.status_code in [400, 422]
    
    def test_chat_completions_missing_required_fields(self, client: TestClient):
        """测试缺少必需字段"""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "query": "你好"
                # 缺少session_id
            }
        )
        
        # 应该返回验证错误
        assert response.status_code == 422
    
    @patch('app.services.chat_service.ChatService.chat_stream')
    def test_chat_with_custom_llm_params(self, mock_chat_stream, client: TestClient):
        """测试自定义LLM参数"""
        async def mock_stream():
            yield "响应"
        
        mock_chat_stream.return_value = mock_stream()
        
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "query": "你好",
                "session_id": "test_session_123",
                "stream": True,
                "llm_provider": "openai",
                "llm_model": "gpt-4",
                "temperature": 0.7
            }
        )
        
        assert response.status_code == 200
        
        # 验证是否调用了正确的参数
        mock_chat_stream.assert_called_once()
        call_args = mock_chat_stream.call_args
        assert call_args[1].get("llm_provider") == "openai"
        assert call_args[1].get("llm_model") == "gpt-4"
        assert call_args[1].get("temperature") == 0.7

