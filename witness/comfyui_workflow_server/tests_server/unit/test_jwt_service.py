# tests_server/unit/test_jwt_service.py
import pytest
import time
from jose import jwt, JWTError

from app.services.jwt_service import create_token, verify_token
from app.config import settings

def test_create_and_verify_token_happy_path(test_user_id):
    """测试一个成功创建的令牌可以通过验证，并返回正确的用户ID。"""
    token = create_token({"sub": test_user_id})
    payload = verify_token(token)
    assert payload is not None
    assert payload.get("sub") == test_user_id

def test_verify_token_expired():
    """测试一个已过期的令牌无法通过验证。"""
    # 使用极短的过期时间创建一个令牌
    short_expiry_token = jwt.encode(
        {"sub": "test-user", "exp": int(time.time()) - 1},
        settings.JWT_SECRET_KEY,
        algorithm="HS256"
    )
    
    with pytest.raises(JWTError):
        verify_token(short_expiry_token)

def test_verify_token_invalid_signature():
    """测试使用错误密钥签名的令牌无法通过验证。"""
    payload = {"sub": "test-user", "exp": int(time.time()) + 100}
    invalid_token = jwt.encode(payload, "this-is-the-wrong-key", algorithm="HS256")
    
    with pytest.raises(JWTError):
        verify_token(invalid_token)

def test_verify_token_malformed():
    """测试一个格式错误的令牌字符串无法通过验证。"""
    malformed_token = "this.is.not.a.valid.token"
    with pytest.raises(JWTError):
        verify_token(malformed_token)

def test_verify_token_missing_sub_claim():
    """测试一个缺少'sub'声明的令牌无法通过验证。"""
    token_no_sub = jwt.encode(
        {"exp": int(time.time()) + 100},
        settings.JWT_SECRET_KEY,
        algorithm="HS256"
    )
    
    with pytest.raises(ValueError, match="Token is missing user identifier"):
        verify_token(token_no_sub) 