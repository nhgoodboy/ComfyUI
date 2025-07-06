"""
工作流注册中心

负责管理所有工作流的注册、查找和元数据管理。
"""

from typing import Dict, List, Optional, Type, Any
from ..workflows.base import BaseWorkflow, WorkflowType
import logging
import os
import importlib
import importlib.util
import inspect

logger = logging.getLogger(__name__)

class WorkflowRegistry:
    """工作流注册中心
    
    管理所有工作流的注册、查找和元数据。
    """
    
    def __init__(self):
        self._workflows: Dict[str, Type[BaseWorkflow]] = {}
        self._workflow_instances: Dict[str, BaseWorkflow] = {}
        self._is_initialized = False
    
    def register_workflow(self, workflow_class: Type[BaseWorkflow]) -> None:
        """注册工作流
        
        Args:
            workflow_class: 工作流类
            
        Raises:
            ValueError: 工作流ID重复或无效
        """
        if not issubclass(workflow_class, BaseWorkflow):
            raise ValueError(f"工作流类必须继承自 BaseWorkflow: {workflow_class}")
        
        # 创建实例获取元数据
        try:
            instance = workflow_class()
            workflow_id = instance.metadata.id
        except Exception as e:
            raise ValueError(f"创建工作流实例失败: {workflow_class}, 错误: {e}")
        
        if workflow_id in self._workflows:
            raise ValueError(f"工作流ID已存在: {workflow_id}")
        
        self._workflows[workflow_id] = workflow_class
        self._workflow_instances[workflow_id] = instance
        
        logger.info(f"注册工作流: {workflow_id} ({workflow_class.__name__})")
    
    def get_workflow(self, workflow_id: str) -> Optional[BaseWorkflow]:
        """获取工作流实例
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            Optional[BaseWorkflow]: 工作流实例，如果不存在则返回None
        """
        return self._workflow_instances.get(workflow_id)
    
    def get_workflow_class(self, workflow_id: str) -> Optional[Type[BaseWorkflow]]:
        """获取工作流类
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            Optional[Type[BaseWorkflow]]: 工作流类，如果不存在则返回None
        """
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[str]:
        """列出所有工作流ID
        
        Returns:
            List[str]: 工作流ID列表
        """
        return list(self._workflows.keys())
    
    def list_workflows_by_type(self, workflow_type: WorkflowType) -> List[str]:
        """按类型列出工作流
        
        Args:
            workflow_type: 工作流类型
            
        Returns:
            List[str]: 符合类型的工作流ID列表
        """
        return [
            workflow_id for workflow_id, instance in self._workflow_instances.items()
            if instance.metadata.workflow_type == workflow_type
        ]
    
    def get_workflow_metadata(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流元数据
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            Optional[Dict[str, Any]]: 工作流元数据字典，如果不存在则返回None
        """
        instance = self._workflow_instances.get(workflow_id)
        if not instance:
            return None
        
        metadata = instance.metadata
        return {
            "id": metadata.id,
            "name": metadata.name,
            "description": metadata.description,
            "version": metadata.version,
            "workflow_type": metadata.workflow_type.value,
            "author": metadata.author,
            "tags": metadata.tags,
            "input_types": metadata.input_types,
            "output_types": metadata.output_types,
            "model_requirements": metadata.model_requirements,
            "node_requirements": metadata.node_requirements,
            "estimated_time": metadata.estimated_time,
            "gpu_required": metadata.gpu_required,
            "parameter_schema": instance.get_parameter_schema()
        }
    
    def get_all_workflows_metadata(self) -> Dict[str, Dict[str, Any]]:
        """获取所有工作流元数据
        
        Returns:
            Dict[str, Dict[str, Any]]: 工作流ID到元数据的映射
        """
        return {
            workflow_id: self.get_workflow_metadata(workflow_id)
            for workflow_id in self._workflows.keys()
        }
    
    def search_workflows(self, query: str, workflow_type: Optional[WorkflowType] = None) -> List[str]:
        """搜索工作流
        
        Args:
            query: 搜索关键词
            workflow_type: 可选的工作流类型过滤
            
        Returns:
            List[str]: 匹配的工作流ID列表
        """
        matching_workflows = []
        query_lower = query.lower()
        
        for workflow_id, instance in self._workflow_instances.items():
            metadata = instance.metadata
            
            # 类型过滤
            if workflow_type and metadata.workflow_type != workflow_type:
                continue
            
            # 关键词匹配
            search_text = f"{metadata.name} {metadata.description} {' '.join(metadata.tags)}"
            if query_lower in search_text.lower():
                matching_workflows.append(workflow_id)
        
        return matching_workflows
    
    def validate_workflow_requirements(self, workflow_id: str) -> List[str]:
        """验证工作流运行要求
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            List[str]: 缺失的要求列表
        """
        instance = self._workflow_instances.get(workflow_id)
        if not instance:
            return [f"工作流不存在: {workflow_id}"]
        
        return instance.validate_requirements()
    
    def auto_discover_workflows(self, base_paths: List[str]) -> int:
        """自动发现并注册工作流
        
        Args:
            base_paths: 搜索路径列表
            
        Returns:
            int: 成功注册的工作流数量
        """
        registered_count = 0
        
        for base_path in base_paths:
            try:
                registered_count += self._discover_workflows_in_path(base_path)
            except Exception as e:
                logger.error(f"发现工作流失败: {base_path}, 错误: {e}")
        
        return registered_count
    
    def _discover_workflows_in_path(self, base_path: str) -> int:
        """在指定路径中发现工作流
        
        Args:
            base_path: 搜索路径
            
        Returns:
            int: 发现的工作流数量
        """
        registered_count = 0
        
        if not os.path.exists(base_path):
            logger.warning(f"路径不存在: {base_path}")
            return 0
        
        # 遍历Python文件
        for root, dirs, files in os.walk(base_path):
            # 跳过__pycache__目录
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    try:
                        registered_count += self._load_workflows_from_file(file_path)
                    except Exception as e:
                        logger.error(f"加载工作流文件失败: {file_path}, 错误: {e}")
        
        return registered_count
    
    def _load_workflows_from_file(self, file_path: str) -> int:
        """从文件加载工作流
        
        Args:
            file_path: 文件路径
            
        Returns:
            int: 加载的工作流数量
        """
        # 将文件路径转换为模块名
        module_name = self._file_path_to_module_name(file_path)
        
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找工作流类
            registered_count = 0
            for name in dir(module):
                obj = getattr(module, name)
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseWorkflow) and 
                    obj is not BaseWorkflow):
                    
                    try:
                        self.register_workflow(obj)
                        registered_count += 1
                    except Exception as e:
                        logger.error(f"注册工作流失败: {obj}, 错误: {e}")
            
            return registered_count
            
        except Exception as e:
            logger.error(f"导入模块失败: {file_path}, 错误: {e}")
            return 0
    
    def _file_path_to_module_name(self, file_path: str) -> str:
        """将文件路径转换为模块名
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 模块名
        """
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 确保模块名是有效的Python标识符
        if not base_name.isidentifier():
            # 替换非字母数字字符为下划线
            import re
            base_name = re.sub(r'[^a-zA-Z0-9_]', '_', base_name)
            
            # 确保以字母或下划线开头
            if base_name and not base_name[0].isalpha() and base_name[0] != '_':
                base_name = f"workflow_{base_name}"
            
            # 如果仍然无效，使用哈希值
            if not base_name or not base_name.isidentifier():
                base_name = f"workflow_{hash(file_path) % 1000000}"
        
        return base_name
    
    def initialize(self) -> None:
        """初始化工作流注册中心
        
        自动发现并注册内置工作流。
        """
        if self._is_initialized:
            return
        
        try:
            # 获取当前文件的目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 内置工作流路径（使用更健壮的路径解析）
            built_in_path = os.path.normpath(os.path.join(current_dir, "..", "workflows", "built_in"))
            custom_path = os.path.normpath(os.path.join(current_dir, "..", "workflows", "custom"))
            
            # 确保路径存在
            search_paths = []
            for path in [built_in_path, custom_path]:
                if os.path.exists(path):
                    search_paths.append(path)
                    logger.debug(f"工作流搜索路径: {path}")
                else:
                    logger.warning(f"工作流路径不存在: {path}")
            
            if not search_paths:
                logger.warning("没有找到可用的工作流搜索路径")
                self._is_initialized = True
                return
            
            # 自动发现工作流
            discovered_count = self.auto_discover_workflows(search_paths)
            
            if discovered_count > 0:
                logger.info(f"工作流注册中心初始化完成，发现 {discovered_count} 个工作流: {list(self._workflows.keys())}")
            else:
                logger.warning("工作流注册中心初始化完成，但未发现任何工作流")
                
            self._is_initialized = True
            
        except Exception as e:
            logger.error(f"工作流注册中心初始化失败: {e}")
            self._is_initialized = True  # 即使失败也标记为已初始化，避免重复尝试
    
    def is_initialized(self) -> bool:
        """检查是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return self._is_initialized

# 全局工作流注册中心实例
workflow_registry = WorkflowRegistry() 