"""
通用工作流API路由

提供工作流的管理、执行和监控功能。
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from ...core.workflow_registry import workflow_registry
from ...core.workflow_manager import get_workflow_manager, TaskStatus
from ...workflows.base import WorkflowType
from ...schemas.response import BaseResponse, SuccessResponse, ErrorResponse
from ...middleware.auth import get_current_user
from ...utils.monitoring import performance_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])

# 请求模型
class ExecuteWorkflowRequest(BaseModel):
    """执行工作流请求"""
    workflow_id: str = Field(..., description="工作流ID")
    parameters: Dict[str, Any] = Field(..., description="工作流参数")
    
class WorkflowSearchRequest(BaseModel):
    """工作流搜索请求"""
    query: str = Field(..., description="搜索关键词")
    workflow_type: Optional[WorkflowType] = Field(None, description="工作流类型过滤")

# 响应模型
class WorkflowMetadataResponse(BaseModel):
    """工作流元数据响应"""
    id: str
    name: str
    description: str
    version: str
    workflow_type: str
    author: str
    tags: List[str]
    input_types: List[str]
    output_types: List[str]
    model_requirements: List[str]
    node_requirements: List[str]
    estimated_time: Optional[int]
    gpu_required: bool
    parameter_schema: Dict[str, Any]

class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    id: str
    workflow_id: str
    status: str
    progress: float
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration: Optional[float]
    estimated_time: Optional[int]
    error_message: Optional[str]

class TaskResultResponse(BaseModel):
    """任务结果响应"""
    id: str
    workflow_id: str
    status: str
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]

class WorkflowStatisticsResponse(BaseModel):
    """工作流统计响应"""
    total_tasks: int
    running_tasks: int
    status_counts: Dict[str, int]
    workflow_counts: Dict[str, int]
    average_duration: float
    max_concurrent_tasks: int

# API端点
@router.get("/", response_model=SuccessResponse[List[str]])
async def list_workflows():
    """列出所有工作流"""
    try:
        workflows = workflow_registry.list_workflows()
        return SuccessResponse(data=workflows)
    except Exception as e:
        logger.error(f"列出工作流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types", response_model=SuccessResponse[List[str]])
async def list_workflow_types():
    """列出所有工作流类型"""
    try:
        types = [wt.value for wt in WorkflowType]
        return SuccessResponse(data=types)
    except Exception as e:
        logger.error(f"列出工作流类型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/type/{workflow_type}", response_model=SuccessResponse[List[str]])
async def list_workflows_by_type(workflow_type: WorkflowType):
    """按类型列出工作流"""
    try:
        workflows = workflow_registry.list_workflows_by_type(workflow_type)
        return SuccessResponse(data=workflows)
    except Exception as e:
        logger.error(f"按类型列出工作流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}", response_model=SuccessResponse[WorkflowMetadataResponse])
async def get_workflow_metadata(workflow_id: str):
    """获取工作流元数据"""
    try:
        metadata = workflow_registry.get_workflow_metadata(workflow_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"工作流不存在: {workflow_id}")
        
        return SuccessResponse(data=WorkflowMetadataResponse(**metadata))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工作流元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/schema", response_model=SuccessResponse[Dict[str, Any]])
async def get_workflow_parameter_schema(workflow_id: str):
    """获取工作流参数Schema"""
    try:
        workflow = workflow_registry.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流不存在: {workflow_id}")
        
        schema = workflow.get_parameter_schema()
        return SuccessResponse(data=schema)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工作流参数Schema失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/requirements", response_model=SuccessResponse[List[str]])
async def validate_workflow_requirements(workflow_id: str):
    """验证工作流运行要求"""
    try:
        missing_requirements = workflow_registry.validate_workflow_requirements(workflow_id)
        return SuccessResponse(data=missing_requirements)
    except Exception as e:
        logger.error(f"验证工作流要求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=SuccessResponse[List[str]])
async def search_workflows(request: WorkflowSearchRequest):
    """搜索工作流"""
    try:
        workflows = workflow_registry.search_workflows(
            query=request.query,
            workflow_type=request.workflow_type
        )
        return SuccessResponse(data=workflows)
    except Exception as e:
        logger.error(f"搜索工作流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/execute", response_model=SuccessResponse[str])
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    background_tasks: BackgroundTasks
):
    """执行工作流"""
    try:
        # 检查工作流是否存在
        workflow = workflow_registry.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"工作流不存在: {workflow_id}")
        
        # 检查参数ID是否匹配
        if request.workflow_id != workflow_id:
            raise HTTPException(status_code=400, detail="URL中的工作流ID与请求体中的ID不匹配")
        
        # 执行工作流
        workflow_manager = get_workflow_manager()
        task_id = await workflow_manager.execute_workflow(workflow_id, request.parameters)
        
        # 记录API调用
        performance_monitor.record_api_call(
            endpoint=f"/workflows/{workflow_id}/execute",
            method="POST",
            success=True
        )
        
        return SuccessResponse(data=task_id)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行工作流失败: {e}")
        performance_monitor.record_api_call(
            endpoint=f"/workflows/{workflow_id}/execute",
            method="POST",
            success=False
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}", response_model=SuccessResponse[TaskStatusResponse])
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        workflow_manager = get_workflow_manager()
        task_status = workflow_manager.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        
        return SuccessResponse(data=TaskStatusResponse(**task_status))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}/result", response_model=SuccessResponse[TaskResultResponse])
async def get_task_result(task_id: str):
    """获取任务结果"""
    try:
        workflow_manager = get_workflow_manager()
        task = workflow_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        
        result_data = TaskResultResponse(
            id=task.id,
            workflow_id=task.workflow_id,
            status=task.status.value,
            result=task.result,
            error_message=task.error_message
        )
        
        return SuccessResponse(data=result_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tasks/{task_id}", response_model=SuccessResponse[bool])
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        workflow_manager = get_workflow_manager()
        success = await workflow_manager.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"任务不存在或无法取消: {task_id}")
        
        return SuccessResponse(data=True)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks", response_model=SuccessResponse[List[TaskStatusResponse]])
async def list_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    workflow_id: Optional[str] = Query(None, description="工作流ID过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制")
):
    """列出任务"""
    try:
        workflow_manager = get_workflow_manager()
        
        # 转换状态过滤
        status_filter = None
        if status:
            try:
                status_filter = TaskStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的任务状态: {status}")
        
        tasks = workflow_manager.list_tasks(
            status=status_filter,
            workflow_id=workflow_id,
            limit=limit
        )
        
        # 转换为响应模型
        task_responses = [TaskStatusResponse(**task) for task in tasks]
        
        return SuccessResponse(data=task_responses)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics", response_model=SuccessResponse[WorkflowStatisticsResponse])
async def get_workflow_statistics():
    """获取工作流统计信息"""
    try:
        workflow_manager = get_workflow_manager()
        stats = workflow_manager.get_statistics()
        
        return SuccessResponse(data=WorkflowStatisticsResponse(**stats))
    
    except Exception as e:
        logger.error(f"获取工作流统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metadata", response_model=SuccessResponse[Dict[str, WorkflowMetadataResponse]])
async def get_all_workflows_metadata():
    """获取所有工作流元数据"""
    try:
        all_metadata = workflow_registry.get_all_workflows_metadata()
        
        # 转换为响应模型
        response_data = {
            workflow_id: WorkflowMetadataResponse(**metadata)
            for workflow_id, metadata in all_metadata.items()
        }
        
        return SuccessResponse(data=response_data)
    
    except Exception as e:
        logger.error(f"获取所有工作流元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 