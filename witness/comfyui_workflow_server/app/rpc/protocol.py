"""
RPC协议规范

定义RPC请求和响应的数据模型
"""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field


class RPCRequest(BaseModel):
    """RPC请求模型"""
    method: str = Field(..., description="RPC方法名")
    params: Dict[str, Any] = Field(default_factory=dict, description="方法参数")
    id: str = Field(..., description="请求ID")
    
    class Config:
        json_encoders = {
            # 确保字典类型正确序列化
        }


class RPCResponse(BaseModel):
    """RPC响应模型"""
    result: Optional[Dict[str, Any]] = Field(None, description="成功结果")
    error: Optional[Dict[str, Any]] = Field(None, description="错误信息")
    id: str = Field(..., description="请求ID")
    
    @classmethod
    def success(cls, result: Dict[str, Any], request_id: str) -> "RPCResponse":
        """创建成功响应"""
        return cls(result=result, id=request_id)
    
    @classmethod
    def error(cls, error: Dict[str, Any], request_id: str) -> "RPCResponse":
        """创建错误响应"""
        return cls(error=error, id=request_id)


class BatchRPCRequest(BaseModel):
    """批量RPC请求模型"""
    requests: list[RPCRequest] = Field(..., description="批量请求列表")


class BatchRPCResponse(BaseModel):
    """批量RPC响应模型"""
    responses: list[RPCResponse] = Field(..., description="批量响应列表")


# 业务相关的数据模型

class FileInfo(BaseModel):
    """文件信息模型"""
    filename: str
    path: str
    size: int
    format: str
    created_at: float


class TaskFileInfo(BaseModel):
    """任务文件信息模型"""
    input_filename: str
    expected_output_filename: str
    input_path: Optional[str] = None
    output_path: Optional[str] = None


class WorkflowTaskStatus(BaseModel):
    """工作流任务状态模型"""
    request_id: str
    workflow_id: str
    status: str  # pending, processing, completed, failed, cancelled
    progress: float = 0.0
    stage: str = "pending"  # workflow_execution, post_processing
    message: str = ""
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    estimated_remaining: Optional[int] = None
    workflow_params: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class WorkflowResult(BaseModel):
    """工作流结果模型"""
    request_id: str
    workflow_id: str
    status: str
    workflow_params: Dict[str, Any]
    output_files: list[FileInfo]
    duration: float
    completed_at: float


class WorkflowInfo(BaseModel):
    """工作流信息模型"""
    id: str
    name: str
    description: str
    estimated_time: int
    tags: list[str]
    version: str = "1.0"
    parameters: Optional[Dict[str, Any]] = None