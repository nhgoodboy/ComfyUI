"""
API数据模型定义

定义所有API请求和响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class StyleInfo(BaseModel):
    """风格信息模型"""
    id: str = Field(..., description="风格ID")
    name: str = Field(..., description="风格名称")
    description: str = Field(..., description="风格描述")
    estimated_time: int = Field(..., description="预估处理时间(秒)")
    tags: List[str] = Field(default=[], description="风格标签")

class TransformRequest(BaseModel):
    """风格转换请求模型"""
    style_id: str = Field(..., description="风格ID")
    image_url: str = Field(..., description="图片URL")

class TransformResponse(BaseModel):
    """风格转换响应模型"""
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    user_id: str = Field(..., description="用户ID")
    estimated_time: int = Field(..., description="预估处理时间(秒)")

class TaskStatusData(BaseModel):
    """任务状态数据模型"""
    task_id: str = Field(..., description="任务ID")
    user_id: str = Field(..., description="用户ID")
    style_id: str = Field(..., description="风格ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: float = Field(..., description="进度(0-100)")
    created_at: float = Field(..., description="创建时间戳")
    started_at: Optional[float] = Field(None, description="开始时间戳")
    completed_at: Optional[float] = Field(None, description="完成时间戳")
    estimated_remaining: Optional[int] = Field(None, description="预估剩余时间(秒)")
    error_message: Optional[str] = Field(None, description="错误信息")

class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    success: bool = Field(..., description="是否成功")
    data: TaskStatusData = Field(..., description="任务状态数据")

class OutputImage(BaseModel):
    """输出图片模型"""
    filename: str = Field(..., description="文件名")
    url: str = Field(..., description="访问URL")
    size: int = Field(..., description="文件大小(字节)")

class TaskResult(BaseModel):
    """任务结果模型"""
    output_images: List[OutputImage] = Field(..., description="输出图片列表")
    duration: float = Field(..., description="处理耗时(秒)")
    style_applied: str = Field(..., description="应用的风格")

class TaskResultResponse(BaseModel):
    """任务结果响应模型"""
    success: bool = Field(..., description="是否成功")
    data: TaskResult = Field(..., description="任务结果数据")

class ApiResponse(BaseModel):
    """通用API响应模型"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Any] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")

class UploadFileResponse(BaseModel):
    """文件上传响应模型"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="上传结果")
    error: Optional[str] = Field(None, description="错误信息")

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    message: str = Field(..., description="状态消息")
    timestamp: float = Field(..., description="检查时间戳")
    version: str = Field(..., description="API版本")

class UserTasksResponse(BaseModel):
    """用户任务列表响应模型"""
    success: bool = Field(..., description="是否成功")
    user_id: str = Field(..., description="用户ID")
    tasks: List[TaskStatusData] = Field(..., description="任务列表")
    total: int = Field(..., description="总任务数")

class UserFileInfo(BaseModel):
    """用户文件信息模型"""
    file_id: str = Field(..., description="文件ID")
    user_id: str = Field(..., description="用户ID")
    filename: str = Field(..., description="文件名")
    original_name: str = Field(..., description="原始文件名")
    url: str = Field(..., description="访问URL")
    size: int = Field(..., description="文件大小(字节)")
    created_at: float = Field(..., description="创建时间戳")

class UserFilesResponse(BaseModel):
    """用户文件列表响应模型"""
    success: bool = Field(..., description="是否成功")
    user_id: str = Field(..., description="用户ID")
    files: List[UserFileInfo] = Field(..., description="文件列表")
    total: int = Field(..., description="总文件数")

class UserStatsData(BaseModel):
    """用户统计数据模型"""
    user_id: str = Field(..., description="用户ID")
    task_counts: Dict[str, int] = Field(..., description="任务状态统计")
    file_counts: Dict[str, int] = Field(..., description="文件类型统计")
    storage_used: int = Field(..., description="存储使用量(字节)")

class UserStatsResponse(BaseModel):
    """用户统计响应模型"""
    success: bool = Field(..., description="是否成功")
    data: UserStatsData = Field(..., description="用户统计数据")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(False, description="是否成功")
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")

class Token(BaseModel):
    """JWT令牌模型"""
    access_token: str
    token_type: str

class UserFileSchema(BaseModel):
    id: str
    user_id: str
    filename: str
    filepath: str
    file_size: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    file_id: str


class GenericResponseModel(BaseModel):
    message: str | None = None
    data: dict | list | None = None 