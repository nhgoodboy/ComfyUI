"""
API v1 模块

RPC架构下的辅助API，仅保留WebSocket推送功能
"""

__all__ = []

from fastapi import APIRouter
from .websocket_push import router as websocket_router

# 创建 v1 API 路由
v1_router = APIRouter()

# 仅包含WebSocket推送路由
v1_router.include_router(websocket_router, prefix="/ws", tags=["WebSocket推送"]) 