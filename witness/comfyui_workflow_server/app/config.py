"""
应用配置

极简化风格转换API的配置管理
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基本配置
    APP_NAME: str = Field(default="ComfyUI风格转换API", description="应用名称")
    APP_VERSION: str = Field(default="2.0.0", description="应用版本")
    DEBUG: bool = Field(default=False, description="调试模式")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", description="服务器地址")
    PORT: int = Field(default=8000, description="服务器端口")
    WORKERS: int = Field(default=1, description="工作进程数")
    
    # 风格配置
    STYLE_CONFIG_FILE: str = Field(
        default="configs/style_configs.yaml",
        description="风格配置文件路径"
    )
    
    # ComfyUI配置
    COMFYUI_URL: str = Field(
        default="http://localhost:8188",
        description="ComfyUI服务器地址"
    )
    COMFYUI_TIMEOUT: int = Field(default=300, description="ComfyUI请求超时时间（秒）")
    COMFYUI_CLIENT_ID: Optional[str] = Field(default=None, description="ComfyUI客户端ID")
    MAX_RETRIES: int = Field(default=3, description="最大重试次数")
    
    # 任务配置
    MAX_CONCURRENT_TASKS: int = Field(default=10, description="最大并发任务数")
    TASK_CLEANUP_HOURS: int = Field(default=24, description="任务清理时间（小时）")
    MAX_COMPLETED_TASKS: int = Field(default=1000, description="最大保留已完成任务数")
    
    # 文件配置
    UPLOAD_DIR: str = Field(default="uploads", description="上传目录")
    OUTPUT_DIR: str = Field(default="outputs", description="输出目录")
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, description="最大文件大小（字节）")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
        description="允许的文件扩展名"
    )
    FILE_EXPIRE_HOURS: int = Field(default=24, description="文件过期时间（小时）")
    
    # 工作流模板目录
    WORKFLOW_DIR: str = Field(
        default="workflows",
        description="工作流模板目录"
    )
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    
    # 安全配置
    API_KEY: Optional[str] = Field(default=None, description="API密钥（可选）")
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="CORS允许的源"
    )
    
    # 多用户配置
    REQUIRE_USER_ID: bool = Field(default=True, description="是否要求用户身份验证")
    USER_ID_HEADER: str = Field(default="x-user-id", description="用户ID请求头名称")
    MIN_USER_ID_LENGTH: int = Field(default=3, description="用户ID最小长度")
    MAX_USER_ID_LENGTH: int = Field(default=64, description="用户ID最大长度")
    
    # 用户资源限制
    MAX_TASKS_PER_USER: int = Field(default=100, description="每个用户最大任务数")
    MAX_FILES_PER_USER: int = Field(default=1000, description="每个用户最大文件数")
    MAX_STORAGE_PER_USER: int = Field(default=1024 * 1024 * 1024, description="每个用户最大存储空间（字节）")
    
    # 清理配置
    USER_CLEANUP_HOURS: int = Field(default=24, description="用户数据清理时间（小时）")
    ORPHAN_CLEANUP_HOURS: int = Field(default=72, description="孤儿数据清理时间（小时）")
    
    # 性能配置
    REQUEST_TIMEOUT: int = Field(default=300, description="请求超时时间（秒）")
    ASYNC_TASK_TIMEOUT: int = Field(default=600, description="异步任务超时时间（秒）")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# 创建全局配置实例
settings = Settings()

def get_settings() -> Settings:
    """获取配置实例"""
    return settings 