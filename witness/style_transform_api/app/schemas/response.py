from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TransformResponse(BaseModel):
    """图像变换响应模型"""
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    message: str = Field(..., description="响应消息")
    output_image_url: Optional[str] = Field(None, description="输出图像URL")
    processing_time: Optional[float] = Field(None, description="处理时间（秒）")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "task_id": "task_abc123",
                "status": "completed",
                "message": "图像变换完成",
                "output_image_url": "https://example.com/output.jpg",
                "processing_time": 15.5
            }
        }

class BatchTransformResponse(BaseModel):
    """批量变换响应模型"""
    success: bool = Field(..., description="是否成功")
    batch_id: str = Field(..., description="批次ID")
    total_count: int = Field(..., description="总数量")
    completed_count: int = Field(..., description="完成数量")
    failed_count: int = Field(..., description="失败数量")
    results: List[TransformResponse] = Field(..., description="各个任务的结果")

class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: float = Field(..., ge=0, le=100, description="进度百分比")
    output_image_url: Optional[str] = Field(None, description="输出图像URL")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(False, description="是否成功")
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误信息")
    details: Optional[dict] = Field(None, description="详细信息") 