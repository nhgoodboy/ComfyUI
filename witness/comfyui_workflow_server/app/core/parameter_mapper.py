"""
参数映射器

负责将用户提供的参数映射到ComfyUI工作流JSON的具体节点
支持嵌套路径映射，如 "24.inputs.clip_l" -> prompt
"""

import copy
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ParameterMapper:
    """参数映射器 - 将用户参数映射到工作流JSON节点"""
    
    @staticmethod
    def apply_parameters(workflow_json: Dict, params: Dict[str, Any], 
                        parameter_mappings: Dict[str, str]) -> Dict:
        """
        将用户参数映射到工作流JSON节点
        
        Args:
            workflow_json: 工作流JSON模板
            params: 用户提供的参数 {"prompt": "Clay Style", "guidance": 12}
            parameter_mappings: 参数映射配置 {"prompt": "24.inputs.clip_l", "guidance": "24.inputs.guidance"}
        
        Returns:
            Dict: 应用参数后的工作流JSON
        """
        result = copy.deepcopy(workflow_json)
        
        for param_name, param_value in params.items():
            if param_name in parameter_mappings:
                node_path = parameter_mappings[param_name]
                try:
                    ParameterMapper._set_nested_value(result, node_path, param_value)
                    logger.debug(f"成功映射参数 {param_name}={param_value} 到 {node_path}")
                except Exception as e:
                    logger.error(f"映射参数 {param_name} 到 {node_path} 失败: {e}")
                    raise ValueError(f"参数映射失败: {param_name} -> {node_path}")
            else:
                logger.warning(f"未找到参数 {param_name} 的映射配置，跳过")
        
        return result
    
    @staticmethod
    def _set_nested_value(data: Dict, path: str, value: Any):
        """
        设置嵌套字典值 - 支持 "24.inputs.clip_l" 这样的路径
        
        Args:
            data: 目标字典
            path: 嵌套路径，用点分隔
            value: 要设置的值
        """
        keys = path.split('.')
        current = data
        
        # 导航到目标位置的父级
        for key in keys[:-1]:
            if key not in current:
                # 如果路径不存在，创建空字典
                current[key] = {}
            elif not isinstance(current[key], dict):
                raise ValueError(f"路径 {path} 中的 {key} 不是字典类型，无法继续导航")
            current = current[key]
        
        # 设置最终值
        final_key = keys[-1]
        current[final_key] = value
    
    @staticmethod
    def _get_nested_value(data: Dict, path: str, default: Any = None) -> Any:
        """
        获取嵌套字典值
        
        Args:
            data: 源字典
            path: 嵌套路径，用点分隔
            default: 默认值
        
        Returns:
            Any: 获取到的值或默认值
        """
        keys = path.split('.')
        current = data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    @staticmethod
    def validate_workflow_template(workflow_json: Dict, parameter_mappings: Dict[str, str]) -> List[str]:
        """
        验证工作流模板中的参数映射路径是否有效
        
        Args:
            workflow_json: 工作流JSON模板
            parameter_mappings: 参数映射配置
        
        Returns:
            List[str]: 无效路径列表
        """
        invalid_paths = []
        
        for param_name, node_path in parameter_mappings.items():
            try:
                # 尝试获取路径，看是否存在
                value = ParameterMapper._get_nested_value(workflow_json, node_path, "__NOT_FOUND__")
                if value == "__NOT_FOUND__":
                    invalid_paths.append(f"{param_name} -> {node_path}")
            except Exception as e:
                invalid_paths.append(f"{param_name} -> {node_path} (错误: {e})")
        
        return invalid_paths
    
    @staticmethod
    def extract_parameter_mappings(workflow_config: Dict) -> Dict[str, str]:
        """
        从工作流配置中提取参数映射字典
        
        Args:
            workflow_config: 工作流配置对象或字典
        
        Returns:
            Dict[str, str]: 参数名到节点路径的映射
        """
        mappings = {}
        
        if hasattr(workflow_config, 'parameters'):
            # 如果是WorkflowConfig对象
            parameters = workflow_config.parameters
        elif isinstance(workflow_config, dict) and 'parameters' in workflow_config:
            # 如果是字典
            parameters = workflow_config['parameters']
        else:
            return mappings
        
        for param_name, param_def in parameters.items():
            if hasattr(param_def, 'node_path'):
                # 如果是WorkflowParameter对象
                if param_def.node_path:
                    mappings[param_name] = param_def.node_path
            elif isinstance(param_def, dict) and 'node_path' in param_def:
                # 如果是字典
                if param_def['node_path']:
                    mappings[param_name] = param_def['node_path']
        
        return mappings
    
    @staticmethod
    def load_workflow_template(template_path: Path) -> Dict:
        """
        加载工作流JSON模板文件
        
        Args:
            template_path: 模板文件路径
        
        Returns:
            Dict: 工作流JSON
        """
        try:
            if not template_path.exists():
                raise FileNotFoundError(f"工作流模板文件不存在: {template_path}")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                workflow_json = json.load(f)
            
            logger.debug(f"成功加载工作流模板: {template_path}")
            return workflow_json
            
        except json.JSONDecodeError as e:
            logger.error(f"工作流模板JSON解析失败: {e}")
            raise ValueError(f"工作流模板JSON格式错误: {e}")
        except Exception as e:
            logger.error(f"加载工作流模板失败: {e}")
            raise RuntimeError(f"加载工作流模板失败: {e}")
    
    @staticmethod
    def create_workflow_with_parameters(template_path: Path, params: Dict[str, Any], 
                                      parameter_mappings: Dict[str, str]) -> Dict:
        """
        便捷方法：加载模板并应用参数
        
        Args:
            template_path: 模板文件路径
            params: 用户参数
            parameter_mappings: 参数映射配置
        
        Returns:
            Dict: 应用参数后的工作流JSON
        """
        workflow_json = ParameterMapper.load_workflow_template(template_path)
        return ParameterMapper.apply_parameters(workflow_json, params, parameter_mappings)
    
    @staticmethod
    def preview_parameter_mapping(workflow_json: Dict, params: Dict[str, Any],
                                 parameter_mappings: Dict[str, str]) -> Dict[str, Dict]:
        """
        预览参数映射结果，用于调试
        
        Returns:
            Dict: 映射预览信息
            {
                "param_name": {
                    "path": "24.inputs.clip_l",
                    "old_value": "原值",
                    "new_value": "新值",
                    "success": True
                }
            }
        """
        preview = {}
        
        for param_name, param_value in params.items():
            if param_name in parameter_mappings:
                node_path = parameter_mappings[param_name]
                old_value = ParameterMapper._get_nested_value(workflow_json, node_path)
                
                preview[param_name] = {
                    "path": node_path,
                    "old_value": old_value,
                    "new_value": param_value,
                    "success": True
                }
            else:
                preview[param_name] = {
                    "path": None,
                    "old_value": None,
                    "new_value": param_value,
                    "success": False,
                    "error": "未找到映射配置"
                }
        
        return preview