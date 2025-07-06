"""
加密工具模块

提供HMAC签名验证、加密解密等安全工具
支持时间戳防重放攻击和安全随机数生成
"""

import hmac
import hashlib
import time
import secrets
import base64
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class CryptoUtils:
    """加密工具类"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()
        self.fernet = self._create_fernet_cipher()
    
    def _create_fernet_cipher(self) -> Fernet:
        """创建Fernet加密器"""
        # 使用PBKDF2从密钥派生加密密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'comfyui_salt',  # 生产环境应使用随机salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
        return Fernet(key)
    
    def generate_signature(
        self, 
        timestamp: str, 
        method: str, 
        path: str, 
        query: str = "", 
        body_hash: str = ""
    ) -> str:
        """生成请求签名"""
        try:
            # 签名内容：timestamp + method + path + query + body_hash
            sign_content = f"{timestamp}{method}{path}{query}{body_hash}"
            
            signature = hmac.new(
                self.secret_key,
                sign_content.encode(),
                hashlib.sha256
            ).hexdigest()
            
            logger.debug("签名生成成功")
            return signature
            
        except Exception as e:
            logger.error(f"签名生成失败: {e}")
            raise
    
    def verify_signature(
        self,
        signature: str,
        timestamp: str,
        method: str,
        path: str,
        query: str = "",
        body_hash: str = "",
        timeout: int = 300
    ) -> bool:
        """验证请求签名"""
        try:
            # 时间戳验证（防重放攻击）
            if not self._verify_timestamp(timestamp, timeout):
                return False
            
            # 计算预期签名
            expected_signature = self.generate_signature(
                timestamp, method, path, query, body_hash
            )
            
            # 恒定时间比较防止时序攻击
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"签名验证失败: {e}")
            return False
    
    def _verify_timestamp(self, timestamp: str, timeout: int) -> bool:
        """验证时间戳（防重放攻击）"""
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            
            if abs(current_time - request_time) > timeout:
                logger.warning(f"时间戳过期: {request_time}, 当前: {current_time}")
                return False
            
            return True
            
        except (ValueError, TypeError):
            logger.warning("时间戳格式无效")
            return False
    
    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
            
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
            
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise
    
    def generate_secure_token(self, length: int = 32) -> str:
        """生成安全随机令牌"""
        return secrets.token_urlsafe(length)
    
    def generate_api_key(self, length: int = 32) -> str:
        """生成API密钥"""
        return secrets.token_hex(length)
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> Dict[str, str]:
        """哈希密码"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2哈希密码
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        
        hash_value = kdf.derive(password.encode())
        hash_hex = hash_value.hex()
        
        return {
            "hash": hash_hex,
            "salt": salt
        }
    
    def verify_password(self, password: str, hash_data: Dict[str, str]) -> bool:
        """验证密码"""
        try:
            stored_hash = hash_data["hash"]
            salt = hash_data["salt"]
            
            # 重新计算哈希
            computed_hash = self.hash_password(password, salt)["hash"]
            
            # 恒定时间比较
            return hmac.compare_digest(stored_hash, computed_hash)
            
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    def create_request_hash(self, method: str, path: str, body: bytes) -> str:
        """创建请求哈希"""
        content = f"{method}{path}".encode() + body
        return hashlib.sha256(content).hexdigest()
    
    def secure_compare(self, a: str, b: str) -> bool:
        """安全字符串比较（防时序攻击）"""
        return hmac.compare_digest(a.encode(), b.encode())


class SignatureHelper:
    """签名助手类 - 简化签名操作"""
    
    def __init__(self, secret_key: str):
        self.crypto = CryptoUtils(secret_key)
    
    def sign_request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        query: str = "",
        timestamp: Optional[str] = None
    ) -> Dict[str, str]:
        """签名请求并返回必需的头部"""
        if timestamp is None:
            timestamp = str(int(time.time()))
        
        # 计算body哈希
        body_hash = hashlib.sha256(body).hexdigest()
        
        # 生成签名
        signature = self.crypto.generate_signature(
            timestamp, method, path, query, body_hash
        )
        
        return {
            "x-timestamp": timestamp,
            "x-signature": signature
        }
    
    def verify_request(
        self,
        signature: str,
        timestamp: str,
        method: str,
        path: str,
        body: bytes = b"",
        query: str = "",
        timeout: int = 300
    ) -> bool:
        """验证请求签名"""
        # 计算body哈希
        body_hash = hashlib.sha256(body).hexdigest()
        
        return self.crypto.verify_signature(
            signature, timestamp, method, path, query, body_hash, timeout
        )


# 安全常量
class SecurityConstants:
    """安全常量定义"""
    
    # 签名相关
    SIGNATURE_HEADER = "x-signature"
    TIMESTAMP_HEADER = "x-timestamp"
    API_KEY_HEADER = "x-api-key"
    
    # 令牌相关
    BEARER_PREFIX = "Bearer "
    AUTHORIZATION_HEADER = "authorization"
    
    # 时间配置
    DEFAULT_SIGNATURE_TIMEOUT = 300  # 5分钟
    DEFAULT_TOKEN_EXPIRY = 3600      # 1小时
    
    # 安全级别
    MIN_API_KEY_LENGTH = 32
    MIN_JWT_SECRET_LENGTH = 32
    MIN_SIGNATURE_SECRET_LENGTH = 32
    
    # 速率限制
    DEFAULT_RATE_LIMIT_PER_IP = 60
    DEFAULT_RATE_LIMIT_PER_USER = 30


def generate_security_keys() -> Dict[str, str]:
    """生成安全密钥"""
    crypto = CryptoUtils("temp_key")
    
    return {
        "api_secret_key": crypto.generate_api_key(32),
        "jwt_secret_key": crypto.generate_secure_token(32),
        "encryption_key": crypto.generate_secure_token(32)
    }


def create_signature_helper(secret_key: str) -> SignatureHelper:
    """创建签名助手"""
    return SignatureHelper(secret_key)


# 全局实例
_crypto_utils = None
_signature_helper = None

def init_crypto_utils(secret_key: str):
    """初始化加密工具"""
    global _crypto_utils, _signature_helper
    _crypto_utils = CryptoUtils(secret_key)
    _signature_helper = SignatureHelper(secret_key)

def get_crypto_utils() -> CryptoUtils:
    """获取加密工具实例"""
    if _crypto_utils is None:
        raise RuntimeError("加密工具未初始化")
    return _crypto_utils

def get_signature_helper() -> SignatureHelper:
    """获取签名助手实例"""
    if _signature_helper is None:
        raise RuntimeError("签名助手未初始化")
    return _signature_helper 