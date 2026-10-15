import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.deps import get_current_user

@pytest.mark.asyncio
async def test_dataset_summary_auth():
    """Test that the summary endpoint requires authentication"""
    # Clear overrides for this test
    app.dependency_overrides = {}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/teacher/datasets/summary")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_dataset_viewer_404():
    """Test invalid dataset type returns 404"""
    def override_get_current_user():
        return {"id": "mock_id", "identifier": "T123", "role": "teacher", "name": "Test Teacher", "year": "2023-2024", "subject": "Math"}
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/teacher/datasets/invalid_type?page=1&limit=50")
    
    app.dependency_overrides = {}
    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset type not found."

@pytest.mark.asyncio
async def test_dataset_summary_empty():
    """Test dataset summary returns 0 for a new teacher"""
    def override_get_current_user():
        return {"id": "mock_id", "identifier": "T_NEW", "role": "teacher", "name": "New Teacher", "year": "2024", "subject": "Science"}
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/teacher/datasets/summary")
    
    app.dependency_overrides = {}
    assert response.status_code == 200
    data = response.json()
    assert data["interactions"] == 0
    assert data["transcripts"] == 0
    assert data["concepts"] == 0
    assert data["mappings"] == 0
    assert data["difficulty"] == 0
