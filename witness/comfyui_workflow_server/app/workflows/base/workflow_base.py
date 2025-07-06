"""
工作流基类和类型定义

定义了所有工作流必须实现的接口和数据结构。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class WorkflowType(Enum):
    """工作流类型枚举"""
    IMAGE_TO_IMAGE = "image_to_image"
    TEXT_TO_IMAGE = "text_to_image"  
    IMAGE_UPSCALE = "image_upscale"
    BACKGROUND_REMOVAL = "background_removal"
    VIDEO_GENERATION = "video_generation"
    AUDIO_GENERATION = "audio_generation"
    CUSTOM = "custom"

@dataclass
class WorkflowParameter:
    """工作流参数定义"""
    name: str
    type: str  # "string", "number", "boolean", "file", "enum", "array"
    required: bool = True
    default: Any = None
    description: str = ""
    enum_values: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # 正则表达式模式

@dataclass 
class WorkflowMetadata:
    """工作流元数据"""
    id: str
    name: str
    description: str
    version: str
    workflow_type: WorkflowType
    author: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[WorkflowParameter] = field(default_factory=list)
    input_types: List[str] = field(default_factory=list)  # ["image", "text", "video"]
    output_types: List[str] = field(default_factory=list)  # ["image", "video", "audio"]
    model_requirements: List[str] = field(default_factory=list)  # 需要的模型
    node_requirements: List[str] = field(default_factory=list)  # 需要的节点
    estimated_time: Optional[int] = None  # 预估执行时间（秒）
    gpu_required: bool = True  # 是否需要GPU

class BaseWorkflow(ABC):
    """工作流基类
    
    所有工作流都必须继承这个基类并实现抽象方法。
    """
    
    def __init__(self):
        self.metadata = self.get_metadata()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @abstractmethod
    def get_metadata(self) -> WorkflowMetadata:
        """获取工作流元数据
        
        Returns:
            WorkflowMetadata: 工作流的元数据信息
        """
        pass
    
    @abstractmethod
    async def build_workflow(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """构建 ComfyUI 工作流 JSON
        
        Args:
            parameters: 已验证的工作流参数
            
        Returns:
            Dict[str, Any]: ComfyUI 工作流JSON定义
        """
        pass
    
    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证和处理参数
        
        Args:
            parameters: 原始输入参数
            
        Returns:
            Dict[str, Any]: 验证后的参数
            
        Raises:
            ValueError: 参数验证失败
        """
        pass
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """获取参数 JSON Schema
        
        Returns:
            Dict[str, Any]: JSON Schema定义
        """
        properties = {}
        required = []
        
        for param in self.metadata.parameters:
            properties[param.name] = self._param_to_schema(param)
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False
        }
    
    def _param_to_schema(self, param: WorkflowParameter) -> Dict[str, Any]:
        """转换参数为 JSON Schema
        
        Args:
            param: 工作流参数定义
            
        Returns:
            Dict[str, Any]: JSON Schema属性定义
        """
        schema = {
            "description": param.description
        }
        
        if param.type == "string":
            schema["type"] = "string"
            if param.enum_values:
                schema["enum"] = param.enum_values
            if param.min_length is not None:
                schema["minLength"] = param.min_length
            if param.max_length is not None:
                schema["maxLength"] = param.max_length
            if param.pattern:
                schema["pattern"] = param.pattern
                
        elif param.type == "number":
            schema["type"] = "number"
            if param.min_value is not None:
                schema["minimum"] = param.min_value
            if param.max_value is not None:
                schema["maximum"] = param.max_value
                
        elif param.type == "boolean":
            schema["type"] = "boolean"
            
        elif param.type == "file":
            schema["type"] = "string"
            schema["format"] = "uri"
            
        elif param.type == "array":
            schema["type"] = "array"
            # 可以进一步定义数组项的类型
            
        if param.default is not None:
            schema["default"] = param.default
            
        return schema
    
    async def pre_process(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """预处理步骤（可选重写）
        
        在构建工作流之前执行的预处理，比如下载文件、验证资源等。
        
        Args:
            parameters: 已验证的参数
            
        Returns:
            Dict[str, Any]: 预处理后的参数
        """
        return parameters
    
    async def post_process(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """后处理步骤（可选重写）
        
        在工作流执行完成后的后处理，比如文件转换、结果优化等。
        
        Args:
            workflow_result: 工作流执行结果
            
        Returns:
            Dict[str, Any]: 后处理后的结果
        """
        return workflow_result
    
    def validate_requirements(self) -> List[str]:
        """验证工作流运行环境要求（可选重写）
        
        检查模型、节点等是否可用。
        
        Returns:
            List[str]: 缺失的要求列表，空列表表示满足所有要求
        """
        missing_requirements = []
        
        # 这里可以添加具体的验证逻辑
        # 比如检查模型文件是否存在、ComfyUI节点是否可用等
        
        return missing_requirements
    
    def get_estimated_time(self, parameters: Dict[str, Any]) -> Optional[int]:
        """获取预估执行时间（可选重写）
        
        根据参数估算工作流执行时间。
        
        Args:
            parameters: 工作流参数
            
        Returns:
            Optional[int]: 预估时间（秒），None表示无法估算
        """
        return self.metadata.estimated_time
    
    def get_resource_requirements(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """获取资源需求（可选重写）
        
        根据参数估算所需的计算资源。
        
        Args:
            parameters: 工作流参数
            
        Returns:
            Dict[str, Any]: 资源需求信息
        """
        return {
            "gpu_required": self.metadata.gpu_required,
            "estimated_memory_mb": 2048,  # 默认2GB内存
            "estimated_vram_mb": 4096 if self.metadata.gpu_required else 0,  # 默认4GB显存
            "cpu_cores": 1
        }
    
    def __str__(self) -> str:
        return f"<{self.__class__.__name__}: {self.metadata.id}>"
    
    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(id='{self.metadata.id}', "
                f"name='{self.metadata.name}', version='{self.metadata.version}')") 