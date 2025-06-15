import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基本配置
    APP_NAME: str = Field(default="Style Transform API", description="应用名称")
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")
    DEBUG: bool = Field(default=False, description="调试模式")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", description="服务器地址")
    PORT: int = Field(default=8000, description="服务器端口")
    WORKERS: int = Field(default=1, description="工作进程数")
    
    # ComfyUI配置
    COMFYUI_BASE_URL: str = Field(
        default="http://localhost:8188",
        description="ComfyUI服务器地址"
    )
    COMFYUI_TIMEOUT: int = Field(default=300, description="ComfyUI请求超时时间（秒）")
    
    # 任务配置
    MAX_CONCURRENT_TASKS: int = Field(default=10, description="最大并发任务数")
    TASK_CLEANUP_HOURS: int = Field(default=24, description="任务清理时间（小时）")
    
    # 文件配置
    MAX_IMAGE_SIZE: int = Field(default=10 * 1024 * 1024, description="最大图像大小（字节）")
    ALLOWED_IMAGE_TYPES: list = Field(
        default=["image/jpeg", "image/png", "image/webp"],
        description="允许的图像类型"
    )
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    
    # 安全配置
    API_KEY: Optional[str] = Field(default=None, description="API密钥")
    CORS_ORIGINS: list = Field(
        default=["*"],
        description="CORS允许的源"
    )
    
    # 限流配置
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="每分钟请求限制")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, description="每小时请求限制")
    
    class Config:
        from pathlib import Path
        env_file = Path(__file__).resolve().parent.parent / ".env"  # 绝对路径
        env_file_encoding = "utf-8"
        case_sensitive = True

# 创建全局配置实例
settings = Settings()

def get_settings() -> Settings:
    """获取配置实例"""
    return settings 