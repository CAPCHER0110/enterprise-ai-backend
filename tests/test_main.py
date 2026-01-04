"""
主入口测试
"""
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


def test_health_check():
    """测试健康检查端点正常情况"""
    with patch("app.main.get_index") as mock_get_index, \
         patch("app.main.RedisConnectionPool.health_check", new_callable=AsyncMock) as mock_redis:
        mock_get_index.return_value = MagicMock()
        mock_redis.return_value = True
        
        from app.main import app
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "ok"
        assert "checks" in json_response
        assert json_response["checks"]["vector_store"]["status"] == "healthy"
        assert json_response["checks"]["redis"]["status"] == "healthy"


def test_health_check_vector_store_failure():
    """测试向量存储连接失败时的健康检查"""
    with patch("app.main.get_index") as mock_get_index, \
         patch("app.main.RedisConnectionPool.health_check", new_callable=AsyncMock) as mock_redis:
        mock_get_index.side_effect = Exception("Connection refused")
        mock_redis.return_value = True
        
        from app.main import app
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "degraded"
        assert json_response["checks"]["vector_store"]["status"] == "unhealthy"
        assert "Connection refused" in json_response["checks"]["vector_store"]["error"]


def test_health_check_redis_failure():
    """测试Redis连接失败时的健康检查"""
    with patch("app.main.get_index") as mock_get_index, \
         patch("app.main.RedisConnectionPool.health_check", new_callable=AsyncMock) as mock_redis:
        mock_get_index.return_value = MagicMock()
        mock_redis.side_effect = Exception("Redis connection failed")
        
        from app.main import app
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "degraded"
        assert json_response["checks"]["redis"]["status"] == "unhealthy"


def test_liveness_check():
    """测试存活检查端点"""
    from app.main import app
    client = TestClient(app)
    response = client.get("/live")
    
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_check_success():
    """测试就绪检查端点正常情况"""
    with patch("app.main.get_index") as mock_get_index, \
         patch("app.main.RedisConnectionPool.health_check", new_callable=AsyncMock) as mock_redis:
        mock_get_index.return_value = MagicMock()
        mock_redis.return_value = True
        
        from app.main import app
        client = TestClient(app)
        response = client.get("/ready")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


def test_readiness_check_failure():
    """测试就绪检查端点失败情况"""
    with patch("app.main.get_index") as mock_get_index:
        mock_get_index.side_effect = Exception("Vector store not ready")
        
        from app.main import app
        client = TestClient(app)
        response = client.get("/ready")
        
        assert response.status_code == 503
        json_response = response.json()
        assert json_response["status"] == "not_ready"
        assert "Vector store not ready" in json_response["reason"]


def test_metrics_endpoint():
    """测试指标端点"""
    from app.main import app
    client = TestClient(app)
    response = client.get("/metrics")
    
    assert response.status_code == 200
    json_response = response.json()
    assert "timestamp" in json_response
    assert "cache" in json_response
