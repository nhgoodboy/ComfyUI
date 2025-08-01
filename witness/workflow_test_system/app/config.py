"""
Configuration settings for the workflow test system
"""

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
    COMFYUI_WORKFLOW_SERVER_URL: str = "http://localhost:8000"

    # 测试系统自身配置
    TEST_SYSTEM_HOST: str = "0.0.0.0"
    TEST_SYSTEM_PORT: int = 8001
    SESSION_SECRET_KEY: str = "workflow-test-system-secret-key"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # 应用基本配置
    APP_NAME: str = Field(default="ComfyUI Workflow Test System", description="应用名称")
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")
    
    # WebSocket配置
    WEBSOCKET_PING_INTERVAL: int = Field(default=30, description="WebSocket心跳间隔（秒）")
    WEBSOCKET_TIMEOUT: int = Field(default=60, description="WebSocket超时时间（秒）")
    
    # 会话配置
    SESSION_TIMEOUT: int = Field(default=3600, description="会话超时时间（秒）")
    MAX_SESSIONS: int = Field(default=100, description="最大会话数")
    
    # 安全配置
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:8001", "http://127.0.0.1:8001"],
        description="CORS允许的源"
    )
    
    # RPC客户端配置
    RPC_TIMEOUT: int = Field(default=60, description="RPC调用超时时间（秒）")
    RPC_MAX_RETRIES: int = Field(default=3, description="RPC最大重试次数")

# 创建一个全局可用的配置实例
settings = Settings()

# 为了向后兼容，保留旧的Config类
class Config:
    """向后兼容的配置类"""
    
    @property
    def COMFYUI_WORKFLOW_SERVER_URL(self):
        return settings.COMFYUI_WORKFLOW_SERVER_URL
    
    @property
    def TEST_SYSTEM_HOST(self):
        return settings.TEST_SYSTEM_HOST
    
    @property
    def TEST_SYSTEM_PORT(self):
        return settings.TEST_SYSTEM_PORT
    
    @property
    def WEBSOCKET_PING_INTERVAL(self):
        return settings.WEBSOCKET_PING_INTERVAL
    
    @property
    def WEBSOCKET_TIMEOUT(self):
        return settings.WEBSOCKET_TIMEOUT
    
    @property
    def SESSION_TIMEOUT(self):
        return settings.SESSION_TIMEOUT
    
    @property
    def MAX_SESSIONS(self):
        return settings.MAX_SESSIONS
    
    @property
    def LOG_LEVEL(self):
        return settings.LOG_LEVEL
    
    @property
    def CORS_ORIGINS(self):
        return settings.CORS_ORIGINS

config = Config()