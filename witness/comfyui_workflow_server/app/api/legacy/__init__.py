"""
Legacy API 模块

包含向后兼容的API：
- transform: 原有的图像风格转换API（保持向后兼容）
"""

from .transform import router as transform_router

__all__ = [
    'transform_router'
] 