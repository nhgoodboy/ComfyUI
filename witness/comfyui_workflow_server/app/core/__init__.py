"""
核心业务逻辑模块

包含工作流管理的核心功能：
- workflow_manager: 工作流管理器
- workflow_registry: 工作流注册中心
- workflow_engine: 工作流执行引擎
- plugin_loader: 插件加载器
"""

from .workflow_manager import WorkflowManager, get_workflow_manager, set_workflow_manager
from .workflow_registry import workflow_registry

__all__ = [
    'WorkflowManager',
    'get_workflow_manager', 
    'set_workflow_manager',
    'workflow_registry'
] 