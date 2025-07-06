"""
应用配置管理

新增多层安全防护配置：
- API密钥认证
- JWT令牌验证
- IP白名单控制
- 请求签名验证
- 速率限制配置
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import secrets
import logging
import json
import sys

logger = logging.getLogger(__name__)

class SecurityConfig:
    """安全配置类"""
    
    def __init__(self):
        # 基础安全配置
        self.api_secret_key = os.getenv("API_SECRET_KEY", self._generate_secret_key())
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", self._generate_secret_key())
        self.encryption_key = os.getenv("ENCRYPTION_KEY", self._generate_secret_key())
        
        # IP白名单配置
        self.allowed_ips = self._parse_ip_list(
            os.getenv("ALLOWED_IPS", "127.0.0.1,::1,192.168.0.0/24,10.0.0.0/8")
        )
        
        # 认证配置
        self.signature_timeout = int(os.getenv("SIGNATURE_TIMEOUT", "300"))  # 5分钟
        self.token_expiry_minutes = int(os.getenv("TOKEN_EXPIRY_MINUTES", "60"))  # 1小时
        
        # 速率限制配置
        self.rate_limit_per_ip = int(os.getenv("RATE_LIMIT_PER_IP", "60"))  # 每IP每分钟
        self.rate_limit_per_ip_hour = int(os.getenv("RATE_LIMIT_PER_IP_HOUR", "600")) # 每IP每小时
        self.rate_limit_per_user = int(os.getenv("RATE_LIMIT_PER_USER", "30"))  # 每用户每分钟
        
        # 安全选项
        self.enforce_https = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"
        self.secure_cookies = os.getenv("SECURE_COOKIES", "true").lower() == "true"
        self.cors_origins = self._parse_cors_origins(os.getenv("CORS_ORIGINS", ""))
        
        # 多用户配置
        self.api_users = self._parse_api_users(os.getenv("API_USERS"))
        
        # 验证配置
        self._validate_security_config()
    
    def _generate_secret_key(self) -> str:
        """生成安全密钥"""
        return secrets.token_hex(32)
    
    def _parse_ip_list(self, ip_string: str) -> List[str]:
        """解析IP白名单"""
        if not ip_string:
            return ["127.0.0.1", "::1"]
        
        return [ip.strip() for ip in ip_string.split(",") if ip.strip()]
    
    def _parse_cors_origins(self, cors_string: str) -> List[str]:
        """解析CORS源列表"""
        if not cors_string:
            return []
        
        return [origin.strip() for origin in cors_string.split(",") if origin.strip()]
    
    def _parse_api_users(self, users_json_string: Optional[str]) -> Dict[str, Dict]:
        """解析API用户配置"""
        if not users_json_string:
            logger.warning("API_USERS环境变量未设置，将使用默认的示例用户。")
            return {
                "user_01_key": {
                    "username": "default_user",
                    "permissions": ["read", "write"]
                }
            }
        
        try:
            users = json.loads(users_json_string)
            if not isinstance(users, dict):
                raise ValueError("API_USERS必须是一个JSON对象的字符串")
            return users
        except json.JSONDecodeError:
            logger.error("API_USERS环境变量包含无效的JSON，将使用默认用户。")
            return {
                "user_01_key": {
                    "username": "default_user",
                    "permissions": ["read", "write"]
                }
            }
    
    def _validate_security_config(self):
        """验证安全配置"""
        # 检查密钥长度
        if len(self.api_secret_key) < 32:
            logger.warning("API密钥长度不足32字符，安全性可能降低")
        
        if len(self.jwt_secret_key) < 32:
            logger.warning("JWT密钥长度不足32字符，安全性可能降低")
        
        # 检查IP白名单
        if not self.allowed_ips:
            logger.warning("IP白名单为空，将拒绝所有请求")
        
        # 检查超时设置
        if self.signature_timeout < 60:
            logger.warning("签名超时时间过短，可能导致网络延迟问题")
        
        if self.signature_timeout > 3600:
            logger.warning("签名超时时间过长，可能降低安全性")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """获取安全配置摘要"""
        return {
            "api_key_configured": bool(self.api_secret_key),
            "jwt_configured": bool(self.jwt_secret_key),
            "ip_whitelist_count": len(self.allowed_ips),
            "signature_timeout": self.signature_timeout,
            "token_expiry_minutes": self.token_expiry_minutes,
            "rate_limit_per_ip": self.rate_limit_per_ip,
            "rate_limit_per_ip_hour": self.rate_limit_per_ip_hour,
            "rate_limit_per_user": self.rate_limit_per_user,
            "https_enforced": self.enforce_https,
            "secure_cookies": self.secure_cookies
        }


class ComfyUIConfig:
    """ComfyUI服务配置"""
    
    def __init__(self):
        self.host = os.getenv("COMFYUI_HOST", "127.0.0.1")
        self.port = int(os.getenv("COMFYUI_PORT", "8188"))
        self.timeout = int(os.getenv("COMFYUI_TIMEOUT", "300"))
        self.max_retries = int(os.getenv("COMFYUI_MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("COMFYUI_RETRY_DELAY", "5"))
        self.client_id = os.getenv("COMFYUI_CLIENT_ID")  # 允许为空，服务层会处理
        
        # 构建完整URL
        self.base_url = f"http://{self.host}:{self.port}"
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return {
            "host": self.host,
            "port": self.port,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "client_id": self.client_id
        }


class StorageConfig:
    """存储配置"""
    
    def __init__(self):
        self.uploads_dir = Path(os.getenv("UPLOADS_DIR", "uploads"))
        self.outputs_dir = Path(os.getenv("OUTPUTS_DIR", "outputs"))
        self.workflows_dir = Path(os.getenv("WORKFLOWS_DIR", "workflows"))
        self.configs_dir = Path(os.getenv("CONFIGS_DIR", "configs"))
        
        # 确保目录存在
        self._ensure_directories()
        
        # 文件大小限制
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
        self.allowed_extensions = self._parse_extensions(
            os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,gif,bmp,webp")
        )
    
    def _ensure_directories(self):
        """确保所有目录存在"""
        for directory in [self.uploads_dir, self.outputs_dir, self.workflows_dir, self.configs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _parse_extensions(self, extensions_string: str) -> List[str]:
        """解析允许的文件扩展名"""
        return [ext.strip().lower() for ext in extensions_string.split(",") if ext.strip()]
    
    def get_user_upload_dir(self, user_id: str) -> Path:
        """获取用户上传目录"""
        user_dir = self.uploads_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def get_user_output_dir(self, user_id: str) -> Path:
        """获取用户输出目录"""
        user_dir = self.outputs_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir


class AppConfig:
    """应用主配置"""
    
    def __init__(self):
        # 基础配置
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.workers = int(os.getenv("WORKERS", "1"))
    
    # 日志配置
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_file = os.getenv("LOG_FILE", "app.log")
        
        # 子配置
        self.security = SecurityConfig()
        self.comfyui = ComfyUIConfig()
        self.storage = StorageConfig()
        
        # 应用信息
        self.app_name = "ComfyUI Workflow Server"
        self.version = "2.0.0"
        self.description = "多用户安全图像处理工作流服务"
        
        # 配置摘要
        self._log_config_summary()
    
    def _log_config_summary(self):
        """记录配置摘要"""
        logger.info(f"=== {self.app_name} v{self.version} ===")
        logger.info(f"运行模式: {'开发' if self.debug else '生产'}")
        logger.info(f"服务地址: {self.host}:{self.port}")
        logger.info(f"日志级别: {self.log_level}")
        logger.info(f"ComfyUI: {self.comfyui.base_url}")
        logger.info(f"安全配置: {self.security.get_security_summary()}")
    
    def get_fastapi_config(self) -> Dict[str, Any]:
        """获取FastAPI配置"""
        return {
            "title": self.app_name,
            "description": self.description,
            "version": self.version,
            "debug": self.debug,
            "docs_url": "/docs" if self.debug else None,
            "redoc_url": "/redoc" if self.debug else None,
            "openapi_url": "/openapi.json" if self.debug else None
        }
    
    def is_production(self) -> bool:
        """是否生产环境"""
        return not self.debug
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return {
            "level": self.log_level,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "handlers": [
                {
                    "class": "logging.StreamHandler",
                    "level": self.log_level,
                    "formatter": "default"
                },
                {
                    "class": "logging.FileHandler",
                    "level": self.log_level,
                    "filename": self.log_file,
                    "formatter": "default"
                }
            ]
        }


# 全局配置实例
config = AppConfig()

# 快捷访问
security_config = config.security
comfyui_config = config.comfyui
storage_config = config.storage

# 配置验证函数
def validate_config() -> bool:
    """验证配置有效性"""
    try:
        # 检查必需的安全配置
        if not security_config.api_secret_key:
            logger.error("API密钥未配置")
            return False
        
        if not security_config.jwt_secret_key:
            logger.error("JWT密钥未配置")
            return False
        
        if not security_config.allowed_ips:
            logger.error("IP白名单未配置")
            return False
        
        # 检查ComfyUI连接
        # TODO: 添加ComfyUI健康检查
        
        logger.info("配置验证通过")
        return True
        
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        return False


def get_environment_info() -> Dict[str, Any]:
    """获取环境信息"""
    return {
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "environment_variables": {
            key: value for key, value in os.environ.items()
            if not key.endswith("_KEY") and not key.endswith("_SECRET")
        }
    }


# 导出配置
__all__ = [
    "config",
    "security_config", 
    "comfyui_config",
    "storage_config",
    "validate_config",
    "get_environment_info"
] 