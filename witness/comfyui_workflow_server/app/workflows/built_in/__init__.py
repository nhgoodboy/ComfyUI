"""
内置工作流模块

包含预定义的常用工作流：
- style_transform: 风格转换工作流
- text_to_image: 文本生成图像工作流
- image_upscale: 图像放大工作流
- background_removal: 背景移除工作流
"""

from .style_transform import StyleTransformWorkflow

# 导出所有内置工作流
__all__ = [
    'StyleTransformWorkflow'
] 