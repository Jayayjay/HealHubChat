import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_register_user():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123",
                "full_name": "Test User"
            }
        )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_login():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # First register
        await ac.post(
            "/api/v1/auth/register",
            json={
                "username": "logintest",
                "email": "login@example.com",
                "password": "testpass123"
            }
        )
        
        # Then login
        response = await ac.post(
            "/api/v1/auth/login",
            data={
                "username": "logintest",
                "password": "testpass123"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_create_conversation():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Register and login
        await ac.post(
            "/api/v1/auth/register",
            json={
                "username": "convtest",
                "email": "conv@example.com",
                "password": "testpass123"
            }
        )
        
        login_response = await ac.post(
            "/api/v1/auth/login",
            data={"username": "convtest", "password": "testpass123"}
        )
        token = login_response.json()["access_token"]
        
        # Create conversation
        response = await ac.post(
            "/api/v1/conversations/",
            json={"title": "Test Conversation"},
            headers={"Authorization": f"Bearer {token}"}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Conversation"