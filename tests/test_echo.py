import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.echo_service import EchoService

@pytest.mark.asyncio
async def test_echo_service():
    """
    测试 EchoService 业务逻辑
    """
    service = EchoService()
    result = await service.process_echo("Hello")
    assert result == "Echo: Hello"

@pytest.mark.asyncio
async def test_health_check():
    """
    测试健康检查接口
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

# 注意：测试 MCP SSE 端点通常比较复杂，因为涉及长连接协议
# 这里我们主要测试 HTTP 层的健康检查和核心业务逻辑
