"""
RPC异常定义

定义RPC处理过程中的异常类型
"""

from typing import Any, Dict
from .error_codes import ErrorCodes


class RPCError(Exception):
    """RPC基础异常"""
    
    def __init__(self, code: int, message: str = None, data: Any = None):
        self.code = code
        self.message = message or ErrorCodes.get_message(code)
        self.data = data
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            result["data"] = self.data
        return result


class RPCMethodNotFound(RPCError):
    """RPC方法不存在异常"""
    
    def __init__(self, method: str):
        super().__init__(
            code=ErrorCodes.METHOD_NOT_FOUND,
            message=f"方法 '{method}' 不存在",
            data={"method": method}
        )


class RPCInvalidParams(RPCError):
    """RPC参数无效异常"""
    
    def __init__(self, message: str = None, field: str = None, value: Any = None):
        data = {}
        if field:
            data["field"] = field
        if value is not None:
            data["value"] = value
            
        super().__init__(
            code=ErrorCodes.INVALID_PARAMS,
            message=message or "参数无效",
            data=data if data else None
        )


class RPCInternalError(RPCError):
    """RPC内部错误异常"""
    
    def __init__(self, message: str = None, original_error: Exception = None):
        data = {}
        if original_error:
            data["original_error"] = str(original_error)
            
        super().__init__(
            code=ErrorCodes.INTERNAL_ERROR,
            message=message or "内部服务器错误",
            data=data if data else None
        )


class RPCDownloadError(RPCError):
    """下载相关错误"""
    
    def __init__(self, code: int, message: str = None, url: str = None, details: str = None):
        data = {}
        if url:
            data["url"] = url
        if details:
            data["details"] = details
            
        super().__init__(
            code=code,
            message=message,
            data=data if data else None
        )


class RPCTransformError(RPCError):
    """转换相关错误"""
    
    def __init__(self, code: int, message: str = None, task_id: str = None, details: str = None):
        data = {}
        if task_id:
            data["task_id"] = task_id
        if details:
            data["details"] = details
            
        super().__init__(
            code=code,
            message=message,
            data=data if data else None
        )