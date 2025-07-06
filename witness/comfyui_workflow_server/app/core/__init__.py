"""
核心业务逻辑模块

包含业务注册表的核心功能：
- workflow_registry: 工作流注册中心
- style_registry: 风格注册中心
"""

from .workflow_registry import workflow_registry
from .style_registry import style_registry

__all__ = [
    'workflow_registry',
    'style_registry',
] 