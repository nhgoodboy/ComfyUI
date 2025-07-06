import asyncio
import logging
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from ..schemas.request import TransformRequest, BatchTransformRequest
from ..schemas.response import (
    TransformResponse, BatchTransformResponse, TaskStatusResponse, 
    ErrorResponse, TaskStatus
)
from ..services.comfyui_service import comfyui_service
from ..utils.task_manager import task_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["图像变换"])

@router.post("/transform", response_model=TransformResponse)
async def transform_image(
    request: TransformRequest,
    background_tasks: BackgroundTasks
):
    """
    单张图像风格变换
    
    - **user_id**: 用户ID
    - **image_url**: 输入图像URL
    - **style_type**: 风格类型
    - **custom_prompt**: 自定义提示词（可选）
    - **strength**: 变换强度（0.1-1.0）
    """
    try:
        # 创建任务
        task_id = await task_manager.create_task(request.user_id)
        
        # 后台处理
        background_tasks.add_task(
            _process_single_image,
            task_id,
            request.image_url,
            request.style_type.value,
            request.custom_prompt,
            request.strength
        )
        
        return TransformResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="任务已创建，正在处理中"
        )
        
    except Exception as e:
        logger.error(f"创建变换任务失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="TASK_CREATION_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.post("/transform/batch", response_model=BatchTransformResponse)
async def transform_images_batch(
    request: BatchTransformRequest,
    background_tasks: BackgroundTasks
):
    """
    批量图像风格变换
    
    - **user_id**: 用户ID
    - **image_urls**: 输入图像URL列表（最多10张）
    - **style_type**: 风格类型
    - **custom_prompt**: 自定义提示词（可选）
    - **strength**: 变换强度（0.1-1.0）
    """
    try:
        # 创建批量任务
        task_ids = []
        for image_url in request.image_urls:
            task_id = await task_manager.create_task(request.user_id)
            task_ids.append(task_id)
            
            # 后台处理每张图像
            background_tasks.add_task(
                _process_single_image,
                task_id,
                image_url,
                request.style_type.value,
                request.custom_prompt,
                request.strength
            )
        
        # 创建批次响应
        batch_id = f"batch_{request.user_id}_{len(task_ids)}"
        results = [
            TransformResponse(
                success=True,
                task_id=task_id,
                status=TaskStatus.PENDING,
                message="任务已创建"
            )
            for task_id in task_ids
        ]
        
        return BatchTransformResponse(
            success=True,
            batch_id=batch_id,
            total_count=len(task_ids),
            completed_count=0,
            failed_count=0,
            results=results
        )
        
    except Exception as e:
        logger.error(f"创建批量变换任务失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="BATCH_TASK_CREATION_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    - **task_id**: 任务ID
    """
    try:
        task = await task_manager.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="TASK_NOT_FOUND",
                    error_message=f"任务 {task_id} 不存在"
                ).dict()
            )
        
        return TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            output_image_url=task.output_image_url,
            error_message=task.error_message,
            created_at=task.created_at,
            completed_at=task.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="TASK_QUERY_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.get("/user/{user_id}/tasks")
async def get_user_tasks(user_id: str, limit: int = 50):
    """
    获取用户的任务列表
    
    - **user_id**: 用户ID
    - **limit**: 返回数量限制（默认50）
    """
    try:
        tasks = await task_manager.get_user_tasks(user_id, limit)
        
        task_responses = [
            TaskStatusResponse(
                task_id=task.task_id,
                status=task.status,
                progress=task.progress,
                output_image_url=task.output_image_url,
                error_message=task.error_message,
                created_at=task.created_at,
                completed_at=task.completed_at
            )
            for task in tasks
        ]
        
        return {
            "success": True,
            "user_id": user_id,
            "total_count": len(task_responses),
            "tasks": task_responses
        }
        
    except Exception as e:
        logger.error(f"获取用户任务列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="USER_TASKS_QUERY_FAILED",
                error_message=str(e)
            ).dict()
        )

@router.get("/stats")
async def get_system_stats():
    """
    获取系统统计信息
    """
    try:
        stats = await task_manager.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="STATS_QUERY_FAILED",
                error_message=str(e)
            ).dict()
        )

async def _process_single_image(
    task_id: str,
    image_url: str,
    style_type: str,
    custom_prompt: str = None,
    strength: float = 0.6
):
    """后台处理单张图像"""
    try:
        logger.info(f"开始处理任务 {task_id}")
        
        # 调用ComfyUI服务处理图像
        await comfyui_service.process_image(
            task_id=task_id,
            image_url=image_url,
            style_type=style_type,
            custom_prompt=custom_prompt,
            strength=strength
        )
        
    except Exception as e:
        logger.error(f"处理任务 {task_id} 失败: {e}")
        await task_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error_message=str(e)
        ) 