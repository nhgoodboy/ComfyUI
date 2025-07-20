"""
风格注册系统

基于YAML配置文件的风格发现和管理系统
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
import logging
from ..models.api_models import StyleInfo
from ..services.comfyui_service import ComfyUIService
from ..workflows.built_in import UniversalStyleTransformWorkflow

logger = logging.getLogger(__name__)

class StyleRegistry:
    """风格注册系统"""
    
    def __init__(self, config_file: str, comfyui_service: ComfyUIService):
        self.config_file = Path(config_file)
        self.comfyui_service = comfyui_service
        self.styles: Dict[str, StyleInfo] = {}
        self.workflows: Dict[str, UniversalStyleTransformWorkflow] = {}
        self._load_styles()
    
    def _load_styles(self):
        """从配置文件加载风格信息"""
        try:
            if not self.config_file.exists():
                logger.warning(f"配置文件不存在: {self.config_file}")
                return
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config or 'styles' not in config:
                logger.warning("配置文件中没有找到styles配置")
                return
            
            for style_id, style_data in config['styles'].items():
                try:
                    # 验证必要字段
                    required_fields = ['name', 'description', 'workflow_file', 'estimated_time', 'tags']
                    for field in required_fields:
                        if field not in style_data:
                            logger.error(f"风格 {style_id} 缺少必要字段: {field}")
                            continue
                    
                    # 创建StyleInfo对象 (API元数据)
                    self.styles[style_id] = StyleInfo(
                        id=style_id,
                        name=style_data['name'],
                        description=style_data['description'],
                        estimated_time=style_data['estimated_time'],
                        tags=style_data.get('tags', [])
                    )
                    
                    # 创建可执行的工作流实例
                    self.workflows[style_id] = UniversalStyleTransformWorkflow(
                        style_id=style_id,
                        style_config=style_data,
                        comfyui_service=self.comfyui_service
                    )
                    
                    logger.info(f"成功加载风格: {style_id}")
                    
                except Exception as e:
                    logger.error(f"加载风格 {style_id} 失败: {e}")
                    continue
            
            logger.info(f"总共加载了 {len(self.styles)} 个风格")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    
    def get_all_styles(self) -> List[StyleInfo]:
        """获取所有风格"""
        return list(self.styles.values())
    
    def get_style(self, style_id: str) -> Optional[StyleInfo]:
        """获取特定风格"""
        return self.styles.get(style_id)
    
    def get_workflow(self, style_id: str) -> Optional[UniversalStyleTransformWorkflow]:
        """获取可执行的工作流实例"""
        return self.workflows.get(style_id)
    
    def get_workflow_file(self, style_id: str) -> Optional[str]:
        """获取工作流文件路径"""
        if style_id not in self.styles:
            return None
        
        try:
            # 重新读取配置文件获取workflow_file
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            return config.get('styles', {}).get(style_id, {}).get('workflow_file')
        except Exception as e:
            logger.error(f"获取工作流文件失败: {e}")
            return None
    
    def style_exists(self, style_id: str) -> bool:
        """检查风格是否存在"""
        return style_id in self.styles
    
    def reload_styles(self):
        """重新加载配置文件"""
        self.styles.clear()
        self.workflows.clear()
        self._load_styles()
    
    def get_style_count(self) -> int:
        """获取风格数量"""
        return len(self.styles)
    
    def search_styles(self, query: str) -> List[StyleInfo]:
        """搜索风格"""
        if not query:
            return self.get_all_styles()
        
        query_lower = query.lower()
        results = []
        
        for style in self.styles.values():
            # 在名称、描述和标签中搜索
            if (query_lower in style.name.lower() or 
                query_lower in style.description.lower() or
                any(query_lower in tag.lower() for tag in style.tags)):
                results.append(style)
        
        return results