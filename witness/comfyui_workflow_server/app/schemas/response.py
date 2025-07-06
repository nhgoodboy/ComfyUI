from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, TypeVar, Generic

# 基础响应模型
T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    """基础响应模型"""
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")

class SuccessResponse(BaseResponse[T]):
    """成功响应模型"""
    success: bool = Field(True, description="是否成功")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(False, description="是否成功")
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息") 