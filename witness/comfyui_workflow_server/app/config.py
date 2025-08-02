"""
应用配置管理

简化配置，专注于微服务核心功能：
- ComfyUI服务连接
- 存储管理
- 基础应用配置
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

class WorkflowConfig:
    """工作流任务配置"""
    
    def __init__(self):
        self.max_concurrent_tasks = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "3"))
        self.task_timeout = int(os.getenv("WORKFLOW_TASK_TIMEOUT", "300"))
        self.status_check_interval = int(os.getenv("WORKFLOW_STATUS_CHECK_INTERVAL", "2"))


class WebSocketConfig:
    """WebSocket配置"""
    
    def __init__(self):
        self.connection_timeout = int(os.getenv("WEBSOCKET_CONNECTION_TIMEOUT", "30"))
        self.ping_interval = int(os.getenv("WEBSOCKET_PING_INTERVAL", "30"))
        self.ping_timeout = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "10"))
        self.max_connections = int(os.getenv("WEBSOCKET_MAX_CONNECTIONS", "100"))
        self.service_client_id = os.getenv("WEBSOCKET_SERVICE_CLIENT_ID", "workflow_test_system")


class MonitoringConfig:
    """监控配置"""
    
    def __init__(self):
        self.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
        self.enable_detailed_stats = os.getenv("ENABLE_DETAILED_STATS", "true").lower() == "true"
        
        # 文件清理配置
        self.enable_auto_cleanup = os.getenv("ENABLE_AUTO_CLEANUP", "true").lower() == "true"
        self.temp_file_retention_hours = int(os.getenv("TEMP_FILE_RETENTION_HOURS", "2"))
        self.input_file_retention_days = int(os.getenv("INPUT_FILE_RETENTION_DAYS", "7"))
        self.output_file_retention_days = int(os.getenv("OUTPUT_FILE_RETENTION_DAYS", "30"))
        self.cleanup_interval_hours = int(os.getenv("CLEANUP_INTERVAL_HOURS", "6"))


class SecurityConfig:
    """安全配置"""
    
    def __init__(self):
        self.enable_rate_limiting = os.getenv("ENABLE_RATE_LIMITING", "false").lower() == "true"
        self.max_requests_per_minute = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
        self.check_file_mime_type = os.getenv("CHECK_FILE_MIME_TYPE", "true").lower() == "true"
        self.max_filename_length = int(os.getenv("MAX_FILENAME_LENGTH", "255"))


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
    

class AppConfig:
    """应用主配置类"""
    
    def __init__(self):
        # 基础配置
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.external_host = os.getenv("EXTERNAL_HOST", "").strip() or None
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # 服务器配置
        self.workers = int(os.getenv("WORKERS", "1"))
        
        # 服务配置
        self.comfyui = ComfyUIConfig()
        self.storage = StorageConfig()
        self.workflow = WorkflowConfig()
        self.websocket = WebSocketConfig()
        self.monitoring = MonitoringConfig()
        self.security = SecurityConfig()
        
        # 日志配置
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "json")
        
        # CORS配置（简化）
        self.cors_origins = self._parse_cors_origins(os.getenv("CORS_ORIGINS", "*"))
        
        # 记录配置摘要
        self._log_config_summary()
    
    def get_external_base_url(self) -> str:
        """获取外部访问的基础URL"""
        if self.external_host:
            return f"http://{self.external_host}:{self.port}"
        elif self.host == "0.0.0.0":
            # 如果绑定0.0.0.0且没有设置external_host，尝试自动检测本机IP
            import socket
            try:
                # 创建一个UDP socket来获取本机IP
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))  # 连接到Google DNS
                    local_ip = s.getsockname()[0]
                return f"http://{local_ip}:{self.port}"
            except Exception:
                # 如果获取失败，使用localhost作为fallback
                return f"http://localhost:{self.port}"
        else:
            return f"http://{self.host}:{self.port}"
    
    def _parse_cors_origins(self, cors_string: str) -> List[str]:
        """解析CORS源列表"""
        if not cors_string or cors_string == "*":
            return ["*"]
        
        return [origin.strip() for origin in cors_string.split(",") if origin.strip()]
    
    def _log_config_summary(self):
        """记录配置摘要"""
        logger.info(f"应用配置初始化完成")
        logger.info(f"环境: {self.environment}")
        logger.info(f"服务地址: {self.host}:{self.port}")
        logger.info(f"ComfyUI地址: {self.comfyui.base_url}")
        logger.info(f"调试模式: {self.debug}")
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        if self.log_format == "json":
            formatter_config = {
                "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
            }
        else:
            formatter_config = {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": formatter_config
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": self.log_level
                }
            },
            "root": {
                "level": self.log_level,
                "handlers": ["console"]
            },
            "loggers": {
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False
                },
                "fastapi": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False
                }
            }
        }
    
    def get_fastapi_config(self) -> Dict[str, Any]:
        """获取FastAPI配置"""
        return {
            "title": "ComfyUI Workflow Server",
            "description": "ComfyUI工作流微服务",
            "version": "2.0.0",
            "debug": self.debug,
            "openapi_url": "/openapi.json" if self.debug else None,
            "docs_url": "/docs" if self.debug else None,
            "redoc_url": "/redoc" if self.debug else None,
        }
    
    def is_production(self) -> bool:
        """检查是否为生产环境"""
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> AppConfig:
    """获取全局配置实例"""
    return AppConfig()


def validate_config(settings: AppConfig) -> bool:
    """验证配置有效性"""
    try:
        # 验证端口范围
        if not (1 <= settings.port <= 65535):
            logger.error(f"无效的端口号: {settings.port}")
            return False
        
        if not (1 <= settings.comfyui.port <= 65535):
            logger.error(f"无效的ComfyUI端口号: {settings.comfyui.port}")
            return False
        
        # 验证存储目录
        if not settings.storage.uploads_dir.exists():
            logger.error(f"上传目录不存在: {settings.storage.uploads_dir}")
            return False
        
        # 验证文件大小限制
        if settings.storage.max_file_size <= 0:
            logger.error(f"无效的文件大小限制: {settings.storage.max_file_size}")
            return False
        
        logger.info("配置验证通过")
        return True
        
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        return False


def get_environment_info() -> Dict[str, Any]:
    """获取环境信息"""
    settings = get_settings()
    
    return {
        "environment": settings.environment,
        "debug_mode": settings.debug,
        "comfyui_url": settings.comfyui.base_url,
        "storage_config": {
            "uploads_dir": str(settings.storage.uploads_dir),
            "outputs_dir": str(settings.storage.outputs_dir),
            "max_file_size": settings.storage.max_file_size,
            "allowed_extensions": settings.storage.allowed_extensions
        }
    } 