"""
风格服务

提供风格发现、验证和转换功能
"""

from typing import List, Optional, Dict, Any
import logging
from ..core.style_registry import style_registry
from ..models.api_models import StyleInfo

logger = logging.getLogger(__name__)

class StyleService:
    """风格服务"""
    
    def __init__(self):
        # 不再需要工作流处理器，职责分离
        pass
    
    async def get_all_styles(self) -> List[StyleInfo]:
        """获取所有可用风格"""
        try:
            return style_registry.get_all_styles()
        except Exception as e:
            logger.error(f"获取所有风格失败: {e}")
            return []
    
    async def get_style(self, style_id: str) -> Optional[StyleInfo]:
        """获取特定风格信息"""
        try:
            return style_registry.get_style(style_id)
        except Exception as e:
            logger.error(f"获取风格 {style_id} 失败: {e}")
            return None
    
    async def validate_style(self, style_id: str) -> bool:
        """验证风格是否存在"""
        try:
            return style_registry.style_exists(style_id)
        except Exception as e:
            logger.error(f"验证风格 {style_id} 失败: {e}")
            return False
    
    async def search_styles(self, query: str) -> List[StyleInfo]:
        """搜索风格"""
        try:
            return style_registry.search_styles(query)
        except Exception as e:
            logger.error(f"搜索风格失败: {e}")
            return []
    
    async def get_style_count(self) -> int:
        """获取风格数量"""
        try:
            return style_registry.get_style_count()
        except Exception as e:
            logger.error(f"获取风格数量失败: {e}")
            return 0
    
    async def get_workflow_file(self, style_id: str) -> Optional[str]:
        """获取工作流文件路径"""
        try:
            return style_registry.get_workflow_file(style_id)
        except Exception as e:
            logger.error(f"获取工作流文件失败: {e}")
            return None
    
    async def reload_styles(self):
        """重新加载风格配置"""
        try:
            style_registry.reload_styles()
            logger.info("风格配置重新加载完成")
        except Exception as e:
            logger.error(f"重新加载风格配置失败: {e}")
            raise

# 创建全局风格服务实例
style_service = StyleService() 