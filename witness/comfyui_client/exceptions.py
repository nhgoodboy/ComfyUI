"""
ComfyUI客户端自定义异常类

提供详细的错误分类和上下文信息，便于调试和错误处理。
"""

class ComfyUIClientError(Exception):
    """ComfyUI客户端基础异常类"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        
    def __str__(self):
        if self.details:
            return f"{self.message} - 详情: {self.details}"
        return self.message


class ComfyUIConnectionError(ComfyUIClientError):
    """连接相关错误"""
    def __init__(self, message: str, server_url: str = None, status_code: int = None):
        details = {}
        if server_url:
            details["server_url"] = server_url
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details)


class ComfyUIAPIError(ComfyUIClientError):
    """API请求相关错误"""
    def __init__(self, message: str, endpoint: str = None, method: str = None, 
                 status_code: int = None, response_data: dict = None):
        details = {}
        if endpoint:
            details["endpoint"] = endpoint
        if method:
            details["method"] = method
        if status_code:
            details["status_code"] = status_code
        if response_data:
            details["response_data"] = response_data
        super().__init__(message, details)


class ComfyUIValidationError(ComfyUIClientError):
    """参数验证错误"""
    def __init__(self, message: str, parameter: str = None, expected_type: str = None):
        details = {}
        if parameter:
            details["parameter"] = parameter
        if expected_type:
            details["expected_type"] = expected_type
        super().__init__(message, details)


class ComfyUITimeoutError(ComfyUIClientError):
    """请求超时错误"""
    def __init__(self, message: str, timeout_seconds: float = None, operation: str = None):
        details = {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        if operation:
            details["operation"] = operation
        super().__init__(message, details)


class ComfyUIWebSocketError(ComfyUIClientError):
    """WebSocket相关错误"""
    def __init__(self, message: str, websocket_url: str = None, error_code: int = None):
        details = {}
        if websocket_url:
            details["websocket_url"] = websocket_url
        if error_code:
            details["error_code"] = error_code
        super().__init__(message, details)


class ComfyUIFileError(ComfyUIClientError):
    """文件操作相关错误"""
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        details = {}
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation
        super().__init__(message, details) 