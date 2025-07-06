"""
业务逻辑服务模块

包含核心业务逻辑和外部服务集成。
"""

from ..config import get_settings
from ..core.style_registry import style_registry

from .user_service import UserService
from .comfyui_service import ComfyUIService
from .user_file_service import UserFileService
from .user_task_service import UserTaskService
from .style_service import StyleService

# 只导出服务的类，实例将在app.main的lifespan中创建
__all__ = [
    "UserService",
    "ComfyUIService",
    "UserFileService",
    "UserTaskService",
    "StyleService",
    "style_registry", # style_registry 仍然可以作为单例导入
    "get_settings"
] 