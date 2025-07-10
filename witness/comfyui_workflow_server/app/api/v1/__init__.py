"""
API v1 模块

包含简化的微服务API：
- tasks: 用户任务管理API
- files: 用户文件管理API
- styles: 风格管理API
"""

__all__ = []

from fastapi import APIRouter
from .files import router as files_router
from .styles import router as styles_router
from .tasks import router as tasks_router
from .websocket_push import router as websocket_router

# 创建 v1 API 路由
v1_router = APIRouter()

# 包含各个子路由（注意路由内部已经定义了各自的前缀）
v1_router.include_router(files_router)  # files路由内部已经有/users前缀
v1_router.include_router(tasks_router)  # tasks路由内部已经有/users前缀  
v1_router.include_router(styles_router)  # styles路由内部已经有/styles前缀
v1_router.include_router(websocket_router, prefix="/ws", tags=["WebSocket推送"]) 