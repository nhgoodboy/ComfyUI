"""
自定义异常类

定义API服务的各种异常类型，提供更好的错误处理和用户体验。
"""

from typing import Optional, Dict, Any


class StyleTransformAPIException(Exception):
    """API服务基础异常类"""
    
    def __init__(
        self,
        error_code: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.error_code = error_code
        self.error_message = error_message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(error_message)


class ValidationError(StyleTransformAPIException):
    """输入验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="VALIDATION_ERROR",
            error_message=message,
            details={"field": field, **(details or {})},
            status_code=400
        )


class AuthenticationError(StyleTransformAPIException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="AUTHENTICATION_ERROR",
            error_message=message,
            details=details,
            status_code=401
        )


class AuthorizationError(StyleTransformAPIException):
    """授权错误"""
    
    def __init__(self, message: str = "权限不足", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="AUTHORIZATION_ERROR",
            error_message=message,
            details=details,
            status_code=403
        )


class ResourceNotFoundError(StyleTransformAPIException):
    """资源未找到错误"""
    
    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="RESOURCE_NOT_FOUND",
            error_message=f"{resource_type} 不存在: {resource_id}",
            details={"resource_type": resource_type, "resource_id": resource_id, **(details or {})},
            status_code=404
        )


class RateLimitError(StyleTransformAPIException):
    """限流错误"""
    
    def __init__(self, message: str, limit_type: str, limit_value: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="RATE_LIMIT_EXCEEDED",
            error_message=message,
            details={"limit_type": limit_type, "limit_value": limit_value, **(details or {})},
            status_code=429
        )


class ServiceUnavailableError(StyleTransformAPIException):
    """服务不可用错误"""
    
    def __init__(self, service_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="SERVICE_UNAVAILABLE",
            error_message=f"{service_name} 服务当前不可用",
            details={"service_name": service_name, **(details or {})},
            status_code=503
        )


class ComfyUIError(StyleTransformAPIException):
    """ComfyUI相关错误"""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="COMFYUI_ERROR",
            error_message=f"ComfyUI {operation} 失败: {message}",
            details={"operation": operation, **(details or {})},
            status_code=502
        )


class ImageProcessingError(StyleTransformAPIException):
    """图像处理错误"""
    
    def __init__(self, message: str, stage: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="IMAGE_PROCESSING_ERROR",
            error_message=f"图像处理失败 ({stage}): {message}",
            details={"stage": stage, **(details or {})},
            status_code=422
        )


class NetworkError(StyleTransformAPIException):
    """网络错误"""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="NETWORK_ERROR",
            error_message=f"网络操作失败 ({operation}): {message}",
            details={"operation": operation, **(details or {})},
            status_code=502
        )


class TaskError(StyleTransformAPIException):
    """任务处理错误"""
    
    def __init__(self, message: str, task_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="TASK_ERROR",
            error_message=f"任务处理失败: {message}",
            details={"task_id": task_id, **(details or {})},
            status_code=500
        )


class ConfigurationError(StyleTransformAPIException):
    """配置错误"""
    
    def __init__(self, message: str, config_key: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="CONFIGURATION_ERROR",
            error_message=f"配置错误: {message}",
            details={"config_key": config_key, **(details or {})},
            status_code=500
        )


class TimeoutError(StyleTransformAPIException):
    """超时错误"""
    
    def __init__(self, operation: str, timeout_seconds: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="TIMEOUT_ERROR",
            error_message=f"操作超时 ({operation}): {timeout_seconds}秒",
            details={"operation": operation, "timeout_seconds": timeout_seconds, **(details or {})},
            status_code=504
        )


class QuotaExceededError(StyleTransformAPIException):
    """配额超限错误"""
    
    def __init__(self, quota_type: str, limit: int, current: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="QUOTA_EXCEEDED",
            error_message=f"{quota_type} 配额已用完: {current}/{limit}",
            details={
                "quota_type": quota_type,
                "limit": limit,
                "current": current,
                **(details or {})
            },
            status_code=429
        )


class DatabaseError(StyleTransformAPIException):
    """数据库错误"""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="DATABASE_ERROR",
            error_message=f"数据库操作失败 ({operation}): {message}",
            details={"operation": operation, **(details or {})},
            status_code=500
        )


class FileOperationError(StyleTransformAPIException):
    """文件操作错误"""
    
    def __init__(self, message: str, operation: str, file_path: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="FILE_OPERATION_ERROR",
            error_message=f"文件操作失败 ({operation}): {message}",
            details={"operation": operation, "file_path": file_path, **(details or {})},
            status_code=500
        ) 