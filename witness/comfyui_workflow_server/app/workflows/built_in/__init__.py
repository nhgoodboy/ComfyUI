"""
内置工作流模块

包含预定义的常用工作流：
- clay_style_transform: 黏土风格转换工作流
- text_to_image: 文本生成图像工作流（待实现）
- image_upscale: 图像放大工作流（待实现）
- background_removal: 背景移除工作流（待实现）
"""

from .clay_style_transform import ClayStyleTransformWorkflow

# 导出所有内置工作流
__all__ = [
    'ClayStyleTransformWorkflow'
] 