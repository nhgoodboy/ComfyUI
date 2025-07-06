"""
风格注册表

自动扫描并注册所有风格工作流的注册表系统。
基于配置文件动态加载和注册工作流，支持热更新。
"""

import os
import yaml
from typing import Dict, List, Any
import logging

from .universal_style_transform import UniversalStyleTransformWorkflow

logger = logging.getLogger(__name__)

class StyleRegistry:
    """风格工作流注册表"""
    
    def __init__(self):
        self.registered_styles: Dict[str, UniversalStyleTransformWorkflow] = {}
        self.style_configs: Dict[str, Dict[str, Any]] = {}
        self.config_file_path = None
        
    def get_config_path(self) -> str:
        """获取配置文件路径"""
        if self.config_file_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(
                current_dir, 
                "../../../configs/style_configs.yaml"
            )
            self.config_file_path = os.path.normpath(config_path)
        
        return self.config_file_path
    
    def load_style_configs(self) -> Dict[str, Any]:
        """加载风格配置文件"""
        config_path = self.get_config_path()
        
        try:
            logger.info(f"加载风格配置文件: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                configs = yaml.safe_load(f)
            
            if not isinstance(configs, dict):
                raise ValueError("配置文件格式错误：根节点必须是字典")
            
            if 'styles' not in configs:
                raise ValueError("配置文件格式错误：缺少'styles'节点")
            
            styles = configs['styles']
            if not isinstance(styles, dict):
                raise ValueError("配置文件格式错误：'styles'节点必须是字典")
            
            logger.info(f"成功加载风格配置文件，包含 {len(styles)} 种风格")
            return configs
            
        except FileNotFoundError:
            logger.error(f"风格配置文件不存在: {config_path}")
            raise FileNotFoundError(f"风格配置文件不存在: {config_path}")
        except yaml.YAMLError as e:
            logger.error(f"配置文件YAML解析错误: {e}")
            raise ValueError(f"配置文件YAML解析错误: {e}")
        except Exception as e:
            logger.error(f"加载风格配置文件时发生错误: {e}")
            raise RuntimeError(f"加载风格配置文件失败: {e}")
    
    def validate_style_config(self, style_id: str, style_config: Dict[str, Any]) -> bool:
        """验证单个风格配置"""
        # 只验证核心必需字段
        required_fields = ['name', 'description', 'workflow_file']
        
        for field in required_fields:
            if field not in style_config:
                logger.warning(f"风格配置 {style_id} 缺少必需字段: {field}")
                return False
        
        # 验证workflow_file是否存在
        workflow_file = style_config.get('workflow_file')
        if workflow_file:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            workflow_path = os.path.join(
                current_dir, 
                "../../../workflows",
                workflow_file
            )
            workflow_path = os.path.normpath(workflow_path)
            
            if not os.path.exists(workflow_path):
                logger.warning(f"风格配置 {style_id} 的工作流文件不存在: {workflow_path}")
                return False
        
        return True
    
    def register_style(self, style_id: str, style_config: Dict[str, Any]) -> bool:
        """注册单个风格工作流"""
        try:
            # 验证配置
            if not self.validate_style_config(style_id, style_config):
                logger.error(f"风格配置验证失败: {style_id}")
                return False
            
            # 创建工作流实例
            workflow = UniversalStyleTransformWorkflow(style_id, style_config)
            
            # 验证工作流要求
            missing_requirements = workflow.validate_requirements()
            if missing_requirements:
                logger.warning(f"风格工作流 {style_id} 存在未满足的要求: {missing_requirements}")
                # 这里可以选择是否继续注册，目前选择继续
            
            # 注册工作流
            self.registered_styles[style_id] = workflow
            self.style_configs[style_id] = style_config
            
            logger.info(f"成功注册风格工作流: {style_id} - {style_config.get('name', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"注册风格工作流失败 {style_id}: {e}")
            return False
    
    def register_all_styles(self) -> Dict[str, bool]:
        """注册所有风格工作流"""
        logger.info("开始注册所有风格工作流...")
        
        try:
            # 加载配置
            configs = self.load_style_configs()
            styles = configs.get('styles', {})
            
            # 注册结果
            registration_results = {}
            
            # 逐个注册
            for style_id, style_config in styles.items():
                result = self.register_style(style_id, style_config)
                registration_results[style_id] = result
            
            # 统计结果
            successful_count = sum(1 for result in registration_results.values() if result)
            total_count = len(registration_results)
            
            logger.info(f"风格工作流注册完成: {successful_count}/{total_count} 成功")
            
            if successful_count < total_count:
                failed_styles = [style_id for style_id, result in registration_results.items() if not result]
                logger.warning(f"注册失败的风格: {failed_styles}")
            
            return registration_results
            
        except Exception as e:
            logger.error(f"批量注册风格工作流失败: {e}")
            return {}
    
    def get_registered_styles(self) -> List[str]:
        """获取已注册的风格列表"""
        return list(self.registered_styles.keys())
    
    def get_style_workflow(self, style_id: str) -> UniversalStyleTransformWorkflow:
        """获取指定风格的工作流实例"""
        if style_id not in self.registered_styles:
            raise ValueError(f"未注册的风格: {style_id}")
        
        return self.registered_styles[style_id]
    
    def get_style_config(self, style_id: str) -> Dict[str, Any]:
        """获取指定风格的配置"""
        if style_id not in self.style_configs:
            raise ValueError(f"未注册的风格: {style_id}")
        
        return self.style_configs[style_id]
    
    def get_all_style_metadata(self) -> Dict[str, Dict[str, Any]]:
        """获取所有风格的元数据"""
        metadata = {}
        
        for style_id, workflow in self.registered_styles.items():
            try:
                workflow_metadata = workflow.get_metadata()
                metadata[style_id] = {
                    "id": workflow_metadata.id,
                    "name": workflow_metadata.name,
                    "description": workflow_metadata.description,
                    "tags": workflow_metadata.tags,
                    "estimated_time": workflow_metadata.estimated_time,
                    "input_types": workflow_metadata.input_types,
                    "output_types": workflow_metadata.output_types
                }
            except Exception as e:
                logger.error(f"获取风格元数据失败 {style_id}: {e}")
                metadata[style_id] = {
                    "id": style_id,
                    "name": "Unknown",
                    "description": f"获取元数据失败: {e}",
                    "error": True
                }
        
        return metadata
    
    def reload_styles(self) -> Dict[str, bool]:
        """重新加载所有风格（热更新）"""
        logger.info("重新加载所有风格工作流...")
        
        # 清空现有注册
        self.registered_styles.clear()
        self.style_configs.clear()
        
        # 重新注册
        return self.register_all_styles()
    
    def is_style_registered(self, style_id: str) -> bool:
        """检查指定风格是否已注册"""
        return style_id in self.registered_styles
    
    def get_registration_summary(self) -> Dict[str, Any]:
        """获取注册摘要信息"""
        return {
            "total_styles": len(self.registered_styles),
            "registered_styles": list(self.registered_styles.keys()),
            "config_file": self.get_config_path(),
            "last_reload": None  # 可以添加时间戳
        }

# 全局注册表实例
_global_style_registry = StyleRegistry()

def get_style_registry() -> StyleRegistry:
    """获取全局风格注册表实例"""
    return _global_style_registry

def register_all_style_workflows() -> Dict[str, bool]:
    """注册所有风格工作流（便捷函数）"""
    return _global_style_registry.register_all_styles()

def get_all_registered_workflows() -> List[UniversalStyleTransformWorkflow]:
    """获取所有已注册的工作流实例"""
    return list(_global_style_registry.registered_styles.values())

def get_workflow_by_id(style_id: str) -> UniversalStyleTransformWorkflow:
    """根据ID获取工作流实例"""
    return _global_style_registry.get_style_workflow(style_id) 