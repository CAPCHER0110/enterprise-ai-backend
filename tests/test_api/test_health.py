"""
健康检查API测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


def test_health_check_basic(client: TestClient):
    """测试基本健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data


@patch('app.core.connections.RedisConnectionPool.health_check')
def test_health_check_with_redis_healthy(mock_redis_health, client: TestClient):
    """测试Redis健康检查 - 健康状态"""
    mock_redis_health.return_value = AsyncMock(return_value=True)
    
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]


@patch('app.core.connections.RedisConnectionPool.health_check')
def test_health_check_with_redis_unhealthy(mock_redis_health, client: TestClient):
    """测试Redis健康检查 - 不健康状态"""
    mock_redis_health.side_effect = Exception("Redis connection failed")
    
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    # 即使Redis不健康，健康检查端点也应该返回200，但状态为degraded
    assert data["status"] == "degraded"


def test_root_endpoint(client: TestClient):
    """测试根端点"""
    response = client.get("/")
    assert response.status_code in [200, 404]  # 可能没有根端点

