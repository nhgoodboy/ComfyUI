import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """网页版图生图系统配置"""
    
    # 应用基本配置
    APP_NAME: str = Field(default="Web Image Transform", description="应用名称")
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")
    DEBUG: bool = Field(default=True, description="调试模式")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", description="服务器地址")
    PORT: int = Field(default=8080, description="服务器端口")
    
    # 风格变换API配置
    STYLE_API_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="风格变换API服务地址"
    )
    
    # 文件配置
    UPLOAD_DIR: str = Field(default="uploads", description="上传文件目录")
    OUTPUT_DIR: str = Field(default="outputs", description="输出文件目录")
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, description="最大文件大小（字节）")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["jpg", "jpeg", "png", "webp"],
        description="允许的文件扩展名"
    )
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    LOG_FILE: str = Field(default="logs/web_transform.log", description="日志文件路径")
    
    # WebSocket配置
    WS_HEARTBEAT_INTERVAL: int = Field(default=30, description="WebSocket心跳间隔（秒）")
    
    # 安全配置
    SECRET_KEY: str = Field(default="your-secret-key-here", description="密钥")
    CORS_ORIGINS: List[str] = Field(default=["*"], description="CORS允许的源")
    
    # 用户配置
    DEFAULT_USER_ID: str = Field(default="web_user", description="默认用户ID")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# 创建全局配置实例
settings = Settings()

# 确保目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True) 