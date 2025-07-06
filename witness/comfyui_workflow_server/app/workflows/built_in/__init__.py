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
- text_to_image: 文本生成图像工作流（待实现）
- image_upscale: 图像放大工作流（待实现）
- background_removal: 背景移除工作流（待实现）
"""

from .universal_style_transform import UniversalStyleTransformWorkflow
from .style_registry import (
    StyleRegistry,
    get_style_registry,
    register_all_style_workflows,
    get_all_registered_workflows,
    get_workflow_by_id
)

# 自动注册所有风格工作流
try:
    registration_results = register_all_style_workflows()
    print(f"🎨 风格工作流注册完成: {sum(registration_results.values())}/{len(registration_results)} 成功")
    
    # 显示注册成功的风格
    successful_styles = [style_id for style_id, result in registration_results.items() if result]
    if successful_styles:
        print(f"   已注册风格: {', '.join(successful_styles)}")
    
    # 显示注册失败的风格
    failed_styles = [style_id for style_id, result in registration_results.items() if not result]
    if failed_styles:
        print(f"   ⚠️  注册失败: {', '.join(failed_styles)}")
        
except Exception as e:
    print(f"❌ 风格工作流注册失败: {e}")
    registration_results = {}

# 导出所有类和函数
__all__ = [
    'UniversalStyleTransformWorkflow',
    'StyleRegistry',
    'get_style_registry',
    'register_all_style_workflows',
    'get_all_registered_workflows',
    'get_workflow_by_id'
] 