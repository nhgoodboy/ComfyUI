"""
内置工作流模块

基于配置驱动的通用风格转换系统：
- 支持多种风格转换工作流
- 自动从配置文件加载和注册工作流
- 新增风格只需添加JSON文件和配置项

当前支持的风格：
- clay_style_transform: 黏土风格转换工作流
- anime_style_transform: 动漫风格转换工作流
- 更多风格可通过配置文件轻松添加...

未来计划：
- text_to_image: 文本生成图像工作流
- image_upscale: 图像放大工作流
- background_removal: 背景移除工作流
"""

from .universal_style_transform import UniversalStyleTransformWorkflow
from ..base import BaseWorkflow

# 导出所有类和函数
__all__ = [
    'UniversalStyleTransformWorkflow',
    'BaseWorkflow'
] 