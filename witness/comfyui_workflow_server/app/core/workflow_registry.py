"""
通用工作流注册系统

基于YAML配置文件的工作流发现和管理系统，支持任意类型的工作流
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from ..services.comfyui_service import ComfyUIService

logger = logging.getLogger(__name__)


@dataclass
class WorkflowParameter:
    """工作流参数定义"""
    name: str
    type: str
    description: str
    default: Any
    required: bool
    node_path: str
    validation: Optional[Dict] = None


@dataclass 
class WorkflowConfig:
    """工作流配置信息"""
    id: str
    name: str
    description: str
    template_file: str
    estimated_time: int
    tags: List[str]
    parameters: Dict[str, WorkflowParameter]
    version: str = "1.0.0"


class WorkflowRegistry:
    """通用工作流注册系统"""
    
    def __init__(self, config_file: str, comfyui_service: ComfyUIService):
        self.config_file = Path(config_file)
        self.comfyui_service = comfyui_service
        self.workflows: Dict[str, WorkflowConfig] = {}
        self._load_workflows()
    
    def _load_workflows(self):
        """从配置文件加载工作流信息"""
        try:
            if not self.config_file.exists():
                logger.warning(f"配置文件不存在: {self.config_file}")
                return
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config or 'workflows' not in config:
                logger.warning("配置文件中没有找到workflows配置")
                return
            
            for workflow_id, workflow_data in config['workflows'].items():
                try:
                    # 验证必要字段
                    required_fields = ['name', 'description', 'template_file', 'estimated_time', 'tags']
                    for field in required_fields:
                        if field not in workflow_data:
                            logger.error(f"工作流 {workflow_id} 缺少必要字段: {field}")
                            continue
                    
                    # 解析参数定义
                    parameters = {}
                    if 'parameters' in workflow_data:
                        for param_name, param_data in workflow_data['parameters'].items():
                            parameters[param_name] = WorkflowParameter(
                                name=param_name,
                                type=param_data.get('type', 'string'),
                                description=param_data.get('description', ''),
                                default=param_data.get('default'),
                                required=param_data.get('required', False),
                                node_path=param_data.get('node_path', ''),
                                validation=param_data.get('validation')
                            )
                    
                    # 创建工作流配置对象
                    self.workflows[workflow_id] = WorkflowConfig(
                        id=workflow_id,
                        name=workflow_data['name'],
                        description=workflow_data['description'],
                        template_file=workflow_data['template_file'],
                        estimated_time=workflow_data['estimated_time'],
                        tags=workflow_data.get('tags', []),
                        parameters=parameters,
                        version=workflow_data.get('version', '1.0.0')
                    )
                    
                    logger.info(f"成功加载工作流: {workflow_id}")
                    
                except Exception as e:
                    logger.error(f"加载工作流 {workflow_id} 失败: {e}")
                    continue
            
            logger.info(f"总共加载了 {len(self.workflows)} 个工作流")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    
    def get_all_workflows(self) -> List[WorkflowConfig]:
        """获取所有工作流"""
        return list(self.workflows.values())
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowConfig]:
        """获取特定工作流"""
        return self.workflows.get(workflow_id)
    
    def get_workflow_template_path(self, workflow_id: str) -> Optional[Path]:
        """获取工作流模板文件的完整路径"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return None
        
        # 构建模板文件的完整路径
        # config_file 现在在 workflows/ 目录中，模板文件也在同一目录
        template_dir = self.config_file.parent
        return template_dir / workflow.template_file
    
    def get_workflow_parameters(self, workflow_id: str) -> Dict[str, WorkflowParameter]:
        """获取工作流的参数定义"""
        workflow = self.get_workflow(workflow_id)
        return workflow.parameters if workflow else {}
    
    def validate_parameters(self, workflow_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证工作流参数"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        validated_params = {}
        errors = []
        
        # 检查必需参数
        for param_name, param_def in workflow.parameters.items():
            if param_def.required and param_name not in params:
                errors.append(f"缺少必需参数: {param_name}")
                continue
            
            # 获取参数值（用户提供的或默认值）
            param_value = params.get(param_name, param_def.default)
            
            # 类型验证
            if param_value is not None:
                validated_value = self._validate_parameter_type(
                    param_name, param_value, param_def.type, param_def.validation
                )
                validated_params[param_name] = validated_value
        
        if errors:
            raise ValueError(f"参数验证失败: {', '.join(errors)}")
        
        return validated_params
    
    def _validate_parameter_type(self, param_name: str, value: Any, 
                                param_type: str, validation: Optional[Dict]) -> Any:
        """验证参数类型和约束"""
        if param_type == "string":
            if not isinstance(value, str):
                raise ValueError(f"参数 {param_name} 必须是字符串")
            return value
        
        elif param_type == "float":
            try:
                float_value = float(value)
                # 检查范围约束
                if validation and 'range' in validation:
                    min_val, max_val = validation['range']
                    if not (min_val <= float_value <= max_val):
                        raise ValueError(f"参数 {param_name} 必须在 {min_val}-{max_val} 范围内")
                return float_value
            except (ValueError, TypeError):
                raise ValueError(f"参数 {param_name} 必须是数字")
        
        elif param_type == "int":
            try:
                int_value = int(value)
                if validation and 'range' in validation:
                    min_val, max_val = validation['range']
                    if not (min_val <= int_value <= max_val):
                        raise ValueError(f"参数 {param_name} 必须在 {min_val}-{max_val} 范围内")
                return int_value
            except (ValueError, TypeError):
                raise ValueError(f"参数 {param_name} 必须是整数")
        
        elif param_type == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        
        elif param_type == "file":
            # 文件类型参数通常是URL或文件路径
            if not isinstance(value, str):
                raise ValueError(f"参数 {param_name} 必须是文件路径或URL")
            return value
        
        else:
            # 未知类型，直接返回
            return value
    
    def workflow_exists(self, workflow_id: str) -> bool:
        """检查工作流是否存在"""
        return workflow_id in self.workflows
    
    def reload_workflows(self):
        """重新加载配置文件"""
        self.workflows.clear()
        self._load_workflows()
    
    def get_workflow_count(self) -> int:
        """获取工作流数量"""
        return len(self.workflows)
    
    def search_workflows(self, query: str) -> List[WorkflowConfig]:
        """搜索工作流"""
        if not query:
            return self.get_all_workflows()
        
        query_lower = query.lower()
        results = []
        
        for workflow in self.workflows.values():
            # 在名称、描述和标签中搜索
            if (query_lower in workflow.name.lower() or 
                query_lower in workflow.description.lower() or
                any(query_lower in tag.lower() for tag in workflow.tags)):
                results.append(workflow)
        
        return results
    
    def get_workflow_schema(self, workflow_id: str) -> Optional[Dict]:
        """获取工作流的参数模式，用于前端表单生成"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return None
        
        schema = {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "estimated_time": workflow.estimated_time,
            "parameters": {}
        }
        
        for param_name, param_def in workflow.parameters.items():
            schema["parameters"][param_name] = {
                "type": param_def.type,
                "description": param_def.description,
                "default": param_def.default,
                "required": param_def.required
            }
            
            if param_def.validation:
                schema["parameters"][param_name]["validation"] = param_def.validation
        
        return schema