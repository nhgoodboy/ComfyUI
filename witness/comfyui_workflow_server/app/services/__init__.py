"""
业务逻辑服务模块

包含核心业务逻辑和外部服务集成。
"""

from .user_task_service import UserTaskService
from .user_file_service import UserFileService
from .comfyui_service import ComfyUIService
from ..core.style_registry import style_registry
from ..config import storage_config

# 创建全局服务实例
comfyui_service = ComfyUIService()

user_task_service = UserTaskService(comfyui_service, style_registry)
user_file_service = UserFileService(
    base_upload_dir=storage_config.uploads_dir,
    base_output_dir=storage_config.outputs_dir
) 