"""
任务API端点

提供任务状态查询、结果获取和任务管理功能的REST API
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from typing import Optional, List
import logging
from ...models.api_models import (
    TaskStatusResponse, TaskResultResponse, ApiResponse, UserTasksResponse
)
from ...services import user_task_service
from ...middleware.user_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, user_id: str = Depends(get_current_user_id)):
    """获取任务状态"""
    try:
        task_data = user_task_service.get_user_task(user_id, task_id)
        if not task_data:
            raise HTTPException(status_code=404, detail="任务不存在或无权访问")
        
        return TaskStatusResponse(success=True, data=task_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {user_id} - {task_id} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str, user_id: str = Depends(get_current_user_id)):
    """获取任务结果"""
    try:
        # 首先检查任务是否存在
        task_data = user_task_service.get_user_task(user_id, task_id)
        if not task_data:
            raise HTTPException(status_code=404, detail="任务不存在或无权访问")
        
        # 检查任务是否已完成
        if task_data.status != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"任务尚未完成，当前状态: {task_data.status}"
            )
        
        # 构造任务结果响应
        # 这里需要根据实际的文件服务来获取结果URL
        result_data = {
            "output_images": [],  # 这里应该从文件服务获取
            "duration": task_data.completed_at - task_data.started_at if task_data.started_at and task_data.completed_at else 0,
            "style_applied": task_data.style_id
        }
        
        return TaskResultResponse(success=True, data=result_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {user_id} - {task_id} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}", response_model=ApiResponse)
async def cancel_task(task_id: str, user_id: str = Depends(get_current_user_id)):
    """取消任务"""
    try:
        task_data = user_task_service.get_user_task(user_id, task_id)
        if not task_data:
            raise HTTPException(status_code=404, detail="任务不存在或无权访问")
        
        if task_data.status in ["completed", "failed"]:
            raise HTTPException(status_code=400, detail="任务已结束，无法取消")
        
        # 简单地将任务状态设为失败
        task_data.status = "failed"
        task_data.error_message = "用户取消"
        
        return ApiResponse(success=True, data={"message": "任务已取消"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {user_id} - {task_id} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=UserTasksResponse)
async def get_user_tasks(user_id: str = Depends(get_current_user_id), limit: int = Query(100, ge=1, le=1000)):
    """获取用户任务列表"""
    try:
        tasks = user_task_service.list_user_tasks(user_id, limit)
        return UserTasksResponse(
            success=True,
            user_id=user_id,
            tasks=tasks,
            total=len(tasks)
        )
    except Exception as e:
        logger.error(f"获取用户任务列表失败: {user_id} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=ApiResponse)
async def get_user_task_stats(user_id: str = Depends(get_current_user_id)):
    """获取用户任务统计"""
    try:
        stats = user_task_service.get_user_stats(user_id)
        return ApiResponse(success=True, data=stats)
    except Exception as e:
        logger.error(f"获取用户任务统计失败: {user_id} - {e}")
        return ApiResponse(success=False, error=str(e)) 