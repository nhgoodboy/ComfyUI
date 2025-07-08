"""
API v1 模块

包含新的通用API：
- tasks: 任务管理API
- files: 文件管理API
- styles: 风格管理API
"""

__all__ = []

from fastapi import APIRouter
from .auth import router as auth_router
from .files import router as files_router
from .styles import router as styles_router
from .tasks import router as tasks_router
from .websocket_push import router as websocket_router

# 创建 v1 API 路由
v1_router = APIRouter()

# 包含各个子路由
v1_router.include_router(auth_router, prefix="/auth", tags=["认证"])
v1_router.include_router(files_router, prefix="/files", tags=["文件"])
v1_router.include_router(styles_router, prefix="/styles", tags=["风格"])
v1_router.include_router(tasks_router, prefix="/tasks", tags=["任务"])
v1_router.include_router(websocket_router, prefix="/ws", tags=["WebSocket推送"]) 