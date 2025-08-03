"""
RPC协议规范

定义RPC请求和响应的数据模型，基于最新的代码结构设计
"""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


# ==== 核心RPC协议模型 ====

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
    requests: List[RPCRequest] = Field(..., description="批量请求列表")


class BatchRPCResponse(BaseModel):
    """批量RPC响应模型"""
    responses: List[RPCResponse] = Field(..., description="批量响应列表")


# ==== 文件相关模型 ====

class FileInfo(BaseModel):
    """文件信息模型 - 标准化输出文件信息"""
    filename: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小(字节)")
    media_type: str = Field(..., description="MIME类型")
    extension: str = Field(..., description="文件扩展名")
    url: str = Field(..., description="访问URL")
    static_url: str = Field(..., description="静态资源URL")
    created_time: Optional[int] = Field(None, description="创建时间戳")
    modified_time: Optional[int] = Field(None, description="修改时间戳")
    is_image: Optional[bool] = Field(None, description="是否为图片文件")


class OutputImageInfo(BaseModel):
    """输出图片信息模型 - 用于返回带base64数据的图片"""
    filename: str = Field(..., description="文件名")
    media_type: str = Field(..., description="MIME类型")
    size: int = Field(..., description="文件大小(字节)")
    data: str = Field(..., description="base64编码的文件数据")
    url: str = Field(..., description="访问URL")
    static_url: str = Field(..., description="静态资源URL")


class FileListResult(BaseModel):
    """文件列表结果模型"""
    files: List[FileInfo] = Field(..., description="文件列表")
    total: int = Field(..., description="总文件数")
    limit: int = Field(..., description="返回限制")
    offset: int = Field(..., description="偏移量")
    pattern: str = Field(..., description="过滤模式")
    has_more: bool = Field(..., description="是否有更多文件")


# ==== 工作流相关模型 ====

class WorkflowParameter(BaseModel):
    """工作流参数模型"""
    name: str = Field(..., description="参数名")
    type: str = Field(..., description="参数类型")
    description: str = Field(..., description="参数描述")
    required: bool = Field(..., description="是否必需")
    default: Any = Field(None, description="默认值")
    validation: Optional[Dict[str, Any]] = Field(None, description="验证规则")


class WorkflowInfo(BaseModel):
    """工作流信息模型"""
    workflow_id: str = Field(..., description="工作流ID")
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述")
    estimated_time: int = Field(..., description="预估执行时间(秒)")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    version: str = Field(default="1.0.0", description="版本号")
    parameter_count: Optional[int] = Field(None, description="参数数量")


class WorkflowListResult(BaseModel):
    """工作流列表结果模型"""
    workflows: List[WorkflowInfo] = Field(..., description="工作流列表")
    total_count: int = Field(..., description="总工作流数")
    query: Optional[str] = Field(None, description="搜索查询")


class WorkflowSchema(BaseModel):
    """工作流模式模型 - 用于前端表单生成"""
    workflow_id: str = Field(..., description="工作流ID")
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述")
    parameters: Dict[str, WorkflowParameter] = Field(..., description="参数定义")


# ==== 任务相关模型 ====

class WorkflowTaskStatus(BaseModel):
    """工作流任务状态模型"""
    request_id: str = Field(..., description="请求ID")
    workflow_id: str = Field(..., description="工作流ID")
    status: str = Field(..., description="任务状态")
    progress: float = Field(default=0.0, description="进度(0-100)")
    stage: str = Field(default="pending", description="任务阶段")
    message: str = Field(default="", description="状态消息")
    created_at: Optional[int] = Field(None, description="创建时间戳")
    started_at: Optional[int] = Field(None, description="开始时间戳")
    completed_at: Optional[int] = Field(None, description="完成时间戳")
    estimated_remaining: Optional[int] = Field(None, description="预估剩余时间(秒)")
    workflow_params: Optional[Dict[str, Any]] = Field(None, description="工作流参数")
    error_message: Optional[str] = Field(None, description="错误信息")
    workflow_info: Optional[WorkflowInfo] = Field(None, description="工作流信息")


class WorkflowResult(BaseModel):
    """工作流结果模型"""
    request_id: str = Field(..., description="请求ID")
    workflow_id: str = Field(..., description="工作流ID")
    status: str = Field(..., description="任务状态")
    duration: float = Field(..., description="处理时长(秒)")
    completed_at: Optional[int] = Field(None, description="完成时间戳")
    workflow_params: Optional[Dict[str, Any]] = Field(None, description="工作流参数")
    output_images: List[FileInfo] = Field(default_factory=list, description="输出图片列表")


class TaskCancelResult(BaseModel):
    """任务取消结果模型"""
    success: bool = Field(..., description="是否成功")
    request_id: str = Field(..., description="请求ID")
    message: str = Field(..., description="结果消息")


# ==== 系统相关模型 ====

class ServiceStatus(BaseModel):
    """服务状态模型"""
    comfyui: str = Field(..., description="ComfyUI服务状态")
    storage: str = Field(..., description="存储服务状态")
    workflows: str = Field(..., description="工作流服务状态")


class SystemHealthDetails(BaseModel):
    """系统健康检查详情模型"""
    comfyui_connected: bool = Field(..., description="ComfyUI是否连接")
    storage_healthy: bool = Field(..., description="存储是否健康")
    workflows_count: int = Field(..., description="可用工作流数量")
    environment: str = Field(..., description="运行环境")
    version: str = Field(..., description="系统版本")


class SystemHealth(BaseModel):
    """系统健康检查模型"""
    status: str = Field(..., description="总体状态")
    timestamp: float = Field(..., description="检查时间戳")
    services: ServiceStatus = Field(..., description="服务状态")
    details: SystemHealthDetails = Field(..., description="详细信息")


class TaskStats(BaseModel):
    """任务统计模型"""
    total: int = Field(..., description="总任务数")
    by_status: Dict[str, int] = Field(default_factory=dict, description="按状态统计")
    by_user: Dict[str, int] = Field(default_factory=dict, description="按用户统计")


class FileStats(BaseModel):
    """文件统计模型"""
    inputs: int = Field(..., description="输入文件数")
    outputs: int = Field(..., description="输出文件数")
    temp: int = Field(..., description="临时文件数")


class WorkflowStats(BaseModel):
    """工作流统计模型"""
    total: int = Field(..., description="总工作流数")
    available: List[str] = Field(default_factory=list, description="可用工作流ID列表")


class SystemStats(BaseModel):
    """系统统计信息模型"""
    timestamp: float = Field(..., description="统计时间戳")
    uptime: float = Field(..., description="系统运行时间(秒)")
    tasks: TaskStats = Field(..., description="任务统计")
    files: FileStats = Field(..., description="文件统计")
    workflows: WorkflowStats = Field(..., description="工作流统计")