"""
API v1 模块

包含新的通用工作流API：
- workflows: 通用工作流API
- tasks: 任务管理API
- system: 系统管理API
"""

from .workflows import router as workflows_router

__all__ = [
    'workflows_router'
] 