"""
用户相关数据模型

定义基于user_id的资源隔离数据结构
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class UserContext(BaseModel):
    """用户上下文 - 用于标识用户身份"""
    user_id: str = Field(..., description="用户ID")

class UserTaskData(BaseModel):
    """用户任务数据"""
    request_id: str = Field(..., description="请求ID，作为主标识符")
    prompt_id: Optional[str] = None  # ComfyUI的prompt_id
    user_id: str = Field(..., description="用户ID")
    style_id: str = Field(..., description="风格ID")
    status: str = Field(..., description="任务状态")
    progress: float = Field(..., description="进度(0-100)")
    created_at: float = Field(..., description="创建时间戳")
    started_at: Optional[float] = Field(None, description="开始时间戳")
    completed_at: Optional[float] = Field(None, description="完成时间戳")
    estimated_remaining: Optional[int] = Field(None, description="预估剩余时间(秒)")
    error_message: Optional[str] = Field(None, description="错误信息")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    

    # 扩展字段 - 用于任务执行过程中的状态管理
    stage: Optional[str] = Field(None, description="任务阶段")
    message: Optional[str] = Field(None, description="状态消息")
    image_url: Optional[str] = Field(None, description="输入图片URL")
    expected_filename: Optional[str] = Field(None, description="期望的文件名")
    output_filename: Optional[str] = Field(None, description="输出文件名")
    download_progress: Optional[float] = Field(None, description="下载进度")
    transform_progress: Optional[float] = Field(None, description="转换进度")
    input_file_path: Optional[str] = Field(None, description="输入文件路径")
    input_file_info: Optional[Dict[str, Any]] = Field(None, description="输入文件信息")
    
    class Config:
        # 允许动态添加字段
        extra = "allow"

class UserFileInfo(BaseModel):
    """用户文件信息"""
    file_id: str = Field(..., description="文件ID")
    user_id: str = Field(..., description="用户ID")
    filename: str = Field(..., description="文件名")
    original_name: str = Field(..., description="原始文件名")
    url: str = Field(..., description="访问URL")
    size: int = Field(..., description="文件大小(字节)")
    created_at: float = Field(..., description="创建时间戳")

class UserStatsResponse(BaseModel):
    """用户统计响应"""
    user_id: str = Field(..., description="用户ID")
    task_counts: Dict[str, int] = Field(..., description="任务统计")
    file_counts: Dict[str, int] = Field(..., description="文件统计")
    storage_used: int = Field(..., description="存储使用量(字节)")

class UserTaskListResponse(BaseModel):
    """用户任务列表响应"""
    success: bool = Field(..., description="是否成功")
    data: List[UserTaskData] = Field(..., description="任务列表")
    total: int = Field(..., description="总数量")

class UserFileListResponse(BaseModel):
    """用户文件列表响应"""
    success: bool = Field(..., description="是否成功")
    data: List[UserFileInfo] = Field(..., description="文件列表")
    total: int = Field(..., description="总数量") 