from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

def test_health_check():
    # Mock the get_index to avoid connecting to real Milvus
    with patch("app.main.get_index") as mock_get_index:
        mock_get_index.return_value = MagicMock()
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["milvus"] == "connected"

def test_health_check_failure():
    # Mock get_index to raise exception
    with patch("app.main.get_index") as mock_get_index:
        mock_get_index.side_effect = Exception("Connection refused")
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        assert "Connection refused" in response.json()["milvus"]
