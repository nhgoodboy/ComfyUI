"""
任务API端点

提供任务状态查询、结果获取和任务管理功能的REST API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging
from ...models.api_models import (
    TaskStatusResponse, TaskResultResponse, ApiResponse
)
from ...services.task_service import task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        task_status = await task_service.get_task_status(task_id)
        if not task_status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return TaskStatusResponse(success=True, data=task_status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """获取任务结果"""
    try:
        # 首先检查任务是否存在
        task_status = await task_service.get_task_status(task_id)
        if not task_status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 检查任务是否已完成
        if task_status.status.value != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"任务尚未完成，当前状态: {task_status.status.value}"
            )
        
        # 获取任务结果
        result = await task_service.get_task_result(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="任务结果不存在")
        
        return TaskResultResponse(success=True, data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}", response_model=ApiResponse)
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        success = await task_service.cancel_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或无法取消")
        
        return ApiResponse(success=True, data={"message": "任务已取消"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=ApiResponse)
async def get_task_statistics():
    """获取任务统计"""
    try:
        stats = await task_service.get_task_count()
        return ApiResponse(success=True, data=stats)
    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        return ApiResponse(success=False, error=str(e)) 