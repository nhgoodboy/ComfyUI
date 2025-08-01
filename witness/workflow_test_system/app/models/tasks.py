"""
任务状态模型
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskInfo(BaseModel):
    """任务信息"""
    request_id: str
    workflow_id: str
    status: TaskStatus
    progress: float = 0.0
    stage: str = ""
    message: str = ""
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_remaining: Optional[int] = None
    workflow_params: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    output_images: Optional[List[Dict[str, str]]] = None

class WorkflowInfo(BaseModel):
    """工作流信息"""
    workflow_id: str
    name: str
    description: str
    estimated_time: int
    tags: List[str] = []
    version: str = "1.0"
    parameter_count: int = 0

class SystemHealth(BaseModel):
    """系统健康状态"""
    status: str
    timestamp: datetime
    services: Dict[str, str]
    details: Dict[str, Any]

class FileInfo(BaseModel):
    """文件信息"""
    filename: str
    size: int
    created_time: datetime
    modified_time: datetime
    extension: str
    media_type: str
    is_image: bool
    url: str
    static_url: str