# tests_server/conftest.py
import pytest
import time
import hmac
import hashlib
import json
from typing import Dict, Any, Generator

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.config import settings
from .test_config import test_settings

# --- 重大核心：在所有测试运行前，用测试配置覆盖应用的主配置 ---
@pytest.fixture(scope="session", autouse=True)
def override_settings():
    """
    在整个测试会话期间，用测试配置覆盖应用配置。
    """
    # 保存原始值
    original_values = settings.model_dump()
    
    # 应用测试配置
    for key, value in test_settings.model_dump().items():
        setattr(settings, key, value)
        
    yield # 测试将在此处运行
    
    # 测试结束后恢复原始值
    for key, value in original_values.items():
        setattr(settings, key, value)

# --- 可重用的测试客户端夹具 ---
@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """
    提供一个FastAPI的TestClient实例。
    这个客户端是同步的，用于简单的API测试。
    """
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
async def async_client() -> Generator[AsyncClient, None, None]:
    """
    提供一个httpx的AsyncClient实例。
    这个客户端是异步的，用于需要异步操作的测试。
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# --- 可重用的辅助函数 ---
@pytest.fixture(scope="session")
def get_secure_headers_for_test():
    """
    提供一个用于生成安全头部的辅助函数。
    与主代码中的函数类似，但使用固定的测试密钥。
    """
    def _get_headers(
        method: str,
        path: str,
        body: Dict[str, Any] = None,
        token: str = None
    ) -> Dict[str, str]:
        
        timestamp = str(int(time.time()))
        body_str = ""
        if body:
            body_str = json.dumps(body, separators=(',', ':'), ensure_ascii=False)

        message_to_sign = f"{method.upper()}\n{path}\n{timestamp}\n{body_str}"
        
        signature = hmac.new(
            test_settings.API_SECRET_KEY.encode('utf-8'),
            message_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'x-api-key': 'test-api-key', # 使用一个虚拟的key
            'x-timestamp': timestamp,
            'x-signature': signature,
            'Content-Type': 'application/json',
        }
        
        if token:
            headers['Authorization'] = f"Bearer {token}"
            
        return headers
        
    return _get_headers

@pytest.fixture(scope="session")
def test_user_id():
    """提供一个固定的测试用户ID。"""
    return "test-user-for-pytest" 