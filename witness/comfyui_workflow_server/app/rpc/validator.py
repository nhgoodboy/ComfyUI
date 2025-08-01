"""
RPC参数验证器

负责验证RPC方法的输入参数
"""

import logging
from typing import Any, Dict, Optional, Type, get_type_hints
from pydantic import BaseModel, ValidationError
from .exceptions import RPCInvalidParams

logger = logging.getLogger(__name__)


class RPCValidator:
    """RPC参数验证器"""
    
    @staticmethod
    def validate_required_fields(params: Dict[str, Any], required_fields: list[str]):
        """验证必需字段"""
        missing_fields = []
        for field in required_fields:
            if field not in params:
                missing_fields.append(field)
        
        if missing_fields:
            raise RPCInvalidParams(
                message=f"缺少必需参数: {', '.join(missing_fields)}",
                field="required_fields",
                value=missing_fields
            )
    
    @staticmethod
    def validate_workflow_id(workflow_id: Any):
        """验证工作流ID"""
        if not workflow_id or not isinstance(workflow_id, str) or not workflow_id.strip():
            raise RPCInvalidParams(
                message="工作流ID不能为空",
                field="workflow_id", 
                value=workflow_id
            )
    
    @staticmethod
    def validate_request_id(request_id: Any):
        """验证请求ID"""
        if not request_id or not isinstance(request_id, str) or not request_id.strip():
            raise RPCInvalidParams(
                message="请求ID不能为空",
                field="request_id",
                value=request_id
            )
    
    @staticmethod
    def validate_file_url(file_url: Any):
        """验证文件URL"""
        if not file_url or not isinstance(file_url, str):
            raise RPCInvalidParams(
                message="文件URL不能为空",
                field="file_url",
                value=file_url
            )
        
        # 基础URL格式检查
        if not (file_url.startswith('http://') or file_url.startswith('https://')):
            raise RPCInvalidParams(
                message="文件URL格式无效，必须以http://或https://开头",
                field="file_url",
                value=file_url
            )
    
    @staticmethod
    def validate_workflow_filename_format(filename: str, workflow_id: str, request_id: str, file_type: str = "input"):
        """验证工作流文件名格式"""
        expected_pattern = f"{workflow_id}_{request_id}_{file_type}"
        
        if not filename.startswith(expected_pattern):
            raise RPCInvalidParams(
                message="文件名格式不符合规范",
                field="filename",
                value={
                    "actual": filename,
                    "expected_pattern": f"{expected_pattern}.{{ext}}",
                    "workflow_id": workflow_id,
                    "request_id": request_id,
                    "type": file_type
                }
            )
    
    @staticmethod
    def validate_pydantic_model(params: Dict[str, Any], model_class: Type[BaseModel]) -> BaseModel:
        """使用Pydantic模型验证参数"""
        try:
            return model_class(**params)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                errors.append(f"{field}: {error['msg']}")
            
            raise RPCInvalidParams(
                message=f"参数验证失败: {'; '.join(errors)}",
                field="validation",
                value=errors
            )