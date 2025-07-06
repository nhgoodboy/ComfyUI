import time
import pytest
from unittest.mock import MagicMock

from app.utils.crypto_utils import verify_signature
from app.config import settings

def test_verify_signature_valid(get_secure_headers_for_test):
    """测试一个完全合法的签名能够通过验证。"""
    headers = get_secure_headers_for_test("POST", "/api/v1/test", {"data": "value"})
    request = MagicMock()
    request.headers = headers
    request.state.body = b'{"data":"value"}'
    
    # 不应该抛出任何异常
    verify_signature(request)

def test_verify_signature_tampered_body(get_secure_headers_for_test):
    """测试在签名后篡改请求体，会导致验证失败。"""
    headers = get_secure_headers_for_test("POST", "/api/v1/test", {"data": "value"})
    request = MagicMock()
    request.headers = headers
    # 请求体与签名时不一致
    request.state.body = b'{"data":"tampered_value"}' 
    
    with pytest.raises(Exception, match="Invalid signature"):
        verify_signature(request)

def test_verify_signature_replay_attack(get_secure_headers_for_test):
    """测试使用一个过期的timestamp会导致验证失败，防止重放攻击。"""
    headers = get_secure_headers_for_test("POST", "/api/v1/test", {"data": "value"})
    
    # 模拟时间流逝，使时间戳过期
    expired_timestamp = int(headers['x-timestamp']) - settings.SIGNATURE_TIMEOUT - 1
    headers['x-timestamp'] = str(expired_timestamp)
    
    request = MagicMock()
    request.headers = headers
    request.state.body = b'{"data":"value"}'
    
    with pytest.raises(Exception, match="Request timestamp has expired"):
        verify_signature(request)

def test_verify_signature_invalid_signature_format(get_secure_headers_for_test):
    """测试一个格式错误的签名会导致验证失败。"""
    headers = get_secure_headers_for_test("POST", "/api/v1/test", {"data": "value"})
    headers['x-signature'] = "not-a-valid-signature"
    
    request = MagicMock()
    request.headers = headers
    request.state.body = b'{"data":"value"}'
    
    with pytest.raises(Exception, match="Invalid signature"):
        verify_signature(request)

def test_verify_signature_missing_headers():
    """测试缺少必要的安全头会导致验证失败。"""
    request = MagicMock()
    
    # 缺少 x-signature
    request.headers = {'x-api-key': 'test', 'x-timestamp': str(int(time.time()))}
    with pytest.raises(Exception, match="Missing required security headers"):
        verify_signature(request)
        
    # 缺少 x-timestamp
    request.headers = {'x-api-key': 'test', 'x-signature': 'sig'}
    with pytest.raises(Exception, match="Missing required security headers"):
        verify_signature(request) 