"""
工作流任务数据模型

定义工作流任务和文件相关的数据结构
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class WorkflowTaskData(BaseModel):
    """工作流任务数据"""
    # 核心标识
    request_id: str = Field(..., description="请求ID，作为主标识符")
    prompt_id: Optional[str] = Field(None, description="ComfyUI的prompt_id")
    workflow_id: str = Field(..., description="工作流ID")
    
    # 任务状态
    status: str = Field(..., description="任务状态")
    progress: float = Field(..., description="进度(0-100)")
    stage: Optional[str] = Field(None, description="任务阶段")
    message: Optional[str] = Field(None, description="状态消息")
    
    # 时间信息
    created_at: float = Field(..., description="创建时间戳")
    started_at: Optional[float] = Field(None, description="开始时间戳")
    completed_at: Optional[float] = Field(None, description="完成时间戳")
    estimated_remaining: Optional[int] = Field(None, description="预估剩余时间(秒)")
    
    # 结果和错误
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 工作流执行参数和状态（动态字段）
    workflow_params: Optional[Dict[str, Any]] = Field(None, description="工作流参数")
    
    # 文件管理（新增）
    task_file_id: Optional[str] = Field(None, description="任务文件ID，用于文件命名")
    input_files: Optional[Dict[str, str]] = Field(default_factory=dict, description="输入文件映射 {参数名: 文件路径}")
    output_file: Optional[str] = Field(None, description="输出文件路径")
    
    class Config:
        # 允许动态添加字段以支持不同工作流的特定需求
        extra = "allow"

class FileInfo(BaseModel):
    """文件信息"""
    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    original_name: str = Field(..., description="原始文件名")
    url: str = Field(..., description="访问URL")
    size: int = Field(..., description="文件大小(字节)")
    created_at: float = Field(..., description="创建时间戳")

class SystemStats(BaseModel):
    """系统统计数据"""
    task_counts: Dict[str, int] = Field(..., description="任务状态统计")
    file_counts: Dict[str, int] = Field(..., description="文件类型统计")
    storage_used: int = Field(..., description="存储使用量(字节)")
    workflow_counts: Dict[str, int] = Field(default_factory=dict, description="工作流使用统计")

class WorkflowTaskListResponse(BaseModel):
    """工作流任务列表响应"""
    success: bool = Field(..., description="是否成功")
    data: List[WorkflowTaskData] = Field(..., description="任务列表")
    total: int = Field(..., description="总数量")

class FileListResponse(BaseModel):
    """文件列表响应"""
    success: bool = Field(..., description="是否成功")
    data: List[FileInfo] = Field(..., description="文件列表")
    total: int = Field(..., description="总数量") 