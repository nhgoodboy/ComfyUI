"""
任务API端点

提供任务状态查询、结果获取和任务管理功能的REST API
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from typing import List
import logging
from ...models.api_models import (
    TaskStatusData, TaskResultResponse, ApiResponse, TransformRequest
)
from ...models.user_models import APIUser
from .auth import get_current_user
from ...services.user_task_service import UserTaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=TaskStatusData, status_code=202, summary="创建新任务")
async def create_task(
    request: Request,
    task_request: TransformRequest,
    user: APIUser = Depends(get_current_user)
):
    """
    创建一个新的图像处理任务。
    
    - **style_id**: 要应用的风格ID
    - **image_url**: 输入图像的URL
    """
    user_task_service: UserTaskService = request.app.state.user_task_service
    try:
        task_id = await user_task_service.create_task(
            user_id=user.username, 
            style_id=task_request.style_id,
            input_image_path=task_request.image_url
        )
        task = user_task_service.get_user_task(user.username, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务创建后未找到，请稍后重试")
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建任务时发生内部错误")

@router.get("/", response_model=List[TaskStatusData], summary="获取当前用户任务列表")
async def list_tasks(
    request: Request, 
    user: APIUser = Depends(get_current_user), 
    limit: int = Query(100, ge=1, le=1000)
):
    """获取当前认证用户的任务列表"""
    user_task_service: UserTaskService = request.app.state.user_task_service
    tasks = user_task_service.list_user_tasks(user.username, limit)
    return tasks

@router.get("/{task_id}", response_model=TaskStatusData, summary="获取指定任务详情")
async def get_task(
    task_id: str,
    request: Request,
    user: APIUser = Depends(get_current_user)
):
    """获取指定任务的详细信息。"""
    user_task_service: UserTaskService = request.app.state.user_task_service
    task = user_task_service.get_user_task(user.username, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    return task

@router.delete("/{task_id}", response_model=ApiResponse, summary="取消正在进行中的任务")
async def cancel_task(
    task_id: str,
    request: Request,
    user: APIUser = Depends(get_current_user)
):
    """取消一个正在进行中的任务。"""
    # This is a placeholder as UserTaskService does not have a cancel method yet
    # In a real implementation, this would call something like:
    # await user_task_service.cancel_task(user.username, task_id)
    logger.warning(f"Task cancellation requested for {task_id} by {user.username}, but not implemented.")
    return ApiResponse(success=True, data={"message": "任务取消功能待实现"})