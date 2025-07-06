# tests_server/integration/test_security_middleware.py
import pytest
from httpx import AsyncClient

# 将测试标记为异步
pytestmark = pytest.mark.asyncio

# --- 测试 /api/v1/auth/token 端点，该端点是获取令牌的入口 ---

async def test_get_token_success(async_client: AsyncClient, get_secure_headers_for_test, test_user_id):
    """
    测试场景：一个拥有全部正确安全头的合法请求，应该能成功获取到JWT令牌。
    这是所有后续操作的基础。
    """
    path = "/api/v1/auth/token"
    method = "POST"
    body = {"user_id": test_user_id}
    headers = get_secure_headers_for_test(method, path, body)

    response = await async_client.post(path, json=body, headers=headers)
    
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert "token_type" in response_data
    assert response_data["token_type"] == "bearer"

async def test_get_token_invalid_signature(async_client: AsyncClient, get_secure_headers_for_test, test_user_id):
    """
    测试场景：请求签名不正确，应该被安全中间件拒绝，返回403 Forbidden。
    """
    path = "/api/v1/auth/token"
    method = "POST"
    body = {"user_id": test_user_id}
    headers = get_secure_headers_for_test(method, path, body)
    headers["x-signature"] = "invalid-signature" # 伪造签名

    response = await async_client.post(path, json=body, headers=headers)
    
    assert response.status_code == 403
    assert "Invalid signature" in response.text
    
# --- 测试一个受保护的端点，例如 /api/v1/styles ---

@pytest.fixture(scope="module")
async def auth_token(async_client: AsyncClient, get_secure_headers_for_test, test_user_id):
    """一个模块级别的夹具，用于为后续测试获取一个有效的JWT令牌。"""
    path = "/api/v1/auth/token"
    method = "POST"
    body = {"user_id": test_user_id}
    headers = get_secure_headers_for_test(method, path, body)
    response = await async_client.post(path, json=body, headers=headers)
    return response.json()["access_token"]


async def test_protected_route_success(async_client: AsyncClient, get_secure_headers_for_test, auth_token):
    """
    测试场景：使用有效的签名和有效的JWT令牌，应该能成功访问受保护的资源。
    """
    path = "/api/v1/styles"
    method = "GET"
    headers = get_secure_headers_for_test(method, path, token=auth_token)

    response = await async_client.get(path, headers=headers)
    
    assert response.status_code == 200
    # 期望返回一个列表（即使是空的）
    assert isinstance(response.json(), list)

async def test_protected_route_missing_token(async_client: AsyncClient, get_secure_headers_for_test):
    """
    测试场景：有合法的签名，但没有提供JWT令牌，访问受保护路由应该失败，返回401 Unauthorized。
    """
    path = "/api/v1/styles"
    method = "GET"
    # 注意：这里调用 get_secure_headers_for_test 时没有传入 token
    headers = get_secure_headers_for_test(method, path)

    response = await async_client.get(path, headers=headers)

    assert response.status_code == 401
    assert "Not authenticated" in response.text

async def test_protected_route_invalid_token(async_client: AsyncClient, get_secure_headers_for_test):
    """
    测试场景：提供了无效或伪造的JWT令牌，访问应该被拒绝。
    """
    path = "/api/v1/styles"
    method = "GET"
    invalid_token = "this.is.an.invalid.token"
    headers = get_secure_headers_for_test(method, path, token=invalid_token)

    response = await async_client.get(path, headers=headers)

    assert response.status_code == 401
    assert "Could not validate credentials" in response.text 