"""
Pydantic数据模型

定义API响应的数据结构。
"""

from .response import BaseResponse, SuccessResponse, ErrorResponse

__all__ = [
    "BaseResponse",
    "SuccessResponse", 
    "ErrorResponse"
] 