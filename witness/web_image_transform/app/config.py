import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    应用配置类，使用pydantic-settings自动加载环境变量
    """
    # .env 文件路径和编码配置
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    # ComfyUI工作流服务器连接配置
    COMFYUI_WORKFLOW_SERVER_URL: str = "http://127.0.0.1:8000"
    API_KEY: str = "your-secret-api-key-here"
    API_USERNAME: str = "default_user"
    API_SECRET_KEY: str = "your-64-char-api-secret-key-change-in-production"

    # Web应用自身配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    SESSION_SECRET_KEY: str = "your-web-app-session-secret-key"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # 应用基本配置
    APP_NAME: str = Field(default="Web Image Transform", description="应用名称")
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")
    
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

# 创建一个全局可用的配置实例
settings = Settings()

# 确保目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True) 