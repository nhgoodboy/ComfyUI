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
    def validate_user_id(user_id: Any):
        """验证用户ID"""
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            raise RPCInvalidParams(
                message="用户ID不能为空",
                field="user_id",
                value=user_id
            )
    
    @staticmethod
    def validate_style_id(style_id: Any):
        """验证风格ID"""
        if not style_id or not isinstance(style_id, str) or not style_id.strip():
            raise RPCInvalidParams(
                message="风格ID不能为空",
                field="style_id", 
                value=style_id
            )
    
    @staticmethod
    def validate_task_id(task_id: Any):
        """验证任务ID"""
        if not task_id or not isinstance(task_id, str) or not task_id.strip():
            raise RPCInvalidParams(
                message="任务ID不能为空",
                field="task_id",
                value=task_id
            )
    
    @staticmethod
    def validate_image_url(image_url: Any):
        """验证图片URL"""
        if not image_url or not isinstance(image_url, str):
            raise RPCInvalidParams(
                message="图片URL不能为空",
                field="image_url",
                value=image_url
            )
        
        # 基础URL格式检查
        if not (image_url.startswith('http://') or image_url.startswith('https://')):
            raise RPCInvalidParams(
                message="图片URL格式无效，必须以http://或https://开头",
                field="image_url",
                value=image_url
            )
    
    @staticmethod
    def validate_filename_format(filename: str, style_id: str, user_id: str, file_type: str = "input"):
        """验证文件名格式"""
        expected_pattern = f"{style_id}_{user_id}_{file_type}"
        
        if not filename.startswith(expected_pattern):
            raise RPCInvalidParams(
                message="文件名格式不符合规范",
                field="filename",
                value={
                    "actual": filename,
                    "expected_pattern": f"{expected_pattern}.{{ext}}",
                    "style_id": style_id,
                    "user_id": user_id,
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