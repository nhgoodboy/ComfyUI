"""
工作流基础模块

定义工作流的基础类和类型：
- workflow_base: 工作流基类
- parameter_types: 参数类型定义
"""

from .workflow_base import (
    BaseWorkflow, WorkflowMetadata, WorkflowParameter, WorkflowType
)
from .parameter_types import ParameterType, ParameterValidator

__all__ = [
    'BaseWorkflow',
    'WorkflowMetadata', 
    'WorkflowParameter',
    'WorkflowType',
    'ParameterType',
    'ParameterValidator'
] 