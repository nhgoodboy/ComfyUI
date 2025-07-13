"""
RPC错误码定义

定义所有RPC方法可能返回的错误码
"""

class ErrorCodes:
    """RPC错误码常量"""
    
    # 通用错误 1001-1099
    INVALID_PARAMS = 1001
    INVALID_USER_ID = 1002
    METHOD_NOT_FOUND = 1003
    INTERNAL_ERROR = 1004
    
    # 下载相关错误 2001-2099  
    INVALID_IMAGE_URL = 2001
    DOWNLOAD_FAILED = 2002
    INVALID_FILE_FORMAT = 2003
    FILE_TOO_LARGE = 2004
    DOWNLOAD_TIMEOUT = 2005
    INVALID_FILENAME_FORMAT = 2006
    STYLE_MISMATCH = 2007
    USER_MISMATCH = 2008
    NETWORK_ERROR = 2009
    
    # 转换相关错误 3001-3099
    STYLE_NOT_FOUND = 3001
    COMFYUI_UNAVAILABLE = 3002
    TRANSFORM_FAILED = 3003
    TASK_NOT_FOUND = 3004
    TASK_CANCELLED = 3005
    WORKFLOW_ERROR = 3006
    
    # 系统错误 9001-9099
    STORAGE_ERROR = 9001
    SERVICE_UNAVAILABLE = 9002
    RATE_LIMIT_EXCEEDED = 9003

    @classmethod
    def get_message(cls, code: int) -> str:
        """获取错误码对应的默认消息"""
        messages = {
            cls.INVALID_PARAMS: "参数错误",
            cls.INVALID_USER_ID: "用户ID无效",
            cls.METHOD_NOT_FOUND: "方法不存在",
            cls.INTERNAL_ERROR: "内部服务器错误",
            
            cls.INVALID_IMAGE_URL: "图片URL无效",
            cls.DOWNLOAD_FAILED: "图片下载失败",
            cls.INVALID_FILE_FORMAT: "文件格式不支持",
            cls.FILE_TOO_LARGE: "文件过大",
            cls.DOWNLOAD_TIMEOUT: "下载超时",
            cls.INVALID_FILENAME_FORMAT: "文件名格式不符合规范",
            cls.STYLE_MISMATCH: "风格参数不匹配",
            cls.USER_MISMATCH: "用户ID不匹配",
            cls.NETWORK_ERROR: "网络连接错误",
            
            cls.STYLE_NOT_FOUND: "风格不存在",
            cls.COMFYUI_UNAVAILABLE: "ComfyUI服务不可用",
            cls.TRANSFORM_FAILED: "转换处理失败",
            cls.TASK_NOT_FOUND: "任务不存在",
            cls.TASK_CANCELLED: "任务已取消",
            cls.WORKFLOW_ERROR: "工作流执行错误",
            
            cls.STORAGE_ERROR: "存储空间错误",
            cls.SERVICE_UNAVAILABLE: "服务暂时不可用",
            cls.RATE_LIMIT_EXCEEDED: "请求频率限制"
        }
        return messages.get(code, "未知错误")