"""
用户任务API端点

提供基于user_id的任务状态查询、结果获取和任务管理功能
"""

from fastapi import APIRouter, HTTPException, Query, Request, Path, Depends
from typing import List
import logging
from ...models.api_models import (
    TaskStatusData, TaskResultResponse, ApiResponse, TransformRequest, TaskResult, OutputImage
)
from ...models.user_models import UserContext
from ...services.user_task_service import UserTaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Tasks"])

async def get_user_context(user_id: str = Path(..., description="用户ID")) -> UserContext:
    """从路径参数获取用户上下文"""
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="用户ID不能为空")
    return UserContext(user_id=user_id.strip())

@router.post("/{user_id}/tasks", response_model=TaskStatusData, status_code=202, summary="创建新任务")
async def create_task(
    request: Request,
    task_request: TransformRequest,
    user_context: UserContext = Depends(get_user_context)
):
    """
    为指定用户创建一个新的图像处理任务。
    
    - **user_id**: 用户ID（路径参数）
    - **style_id**: 要应用的风格ID
    - **image_url**: 输入图像的URL
    """
    user_task_service: UserTaskService = request.app.state.user_task_service
    try:
        task_id = await user_task_service.create_task(
            user_id=user_context.user_id, 
            style_id=task_request.style_id,
            input_image_path=task_request.image_url
        )
        task = user_task_service.get_user_task(user_context.user_id, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务创建后未找到，请稍后重试")
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建任务时发生内部错误")

@router.get("/{user_id}/tasks", response_model=List[TaskStatusData], summary="获取用户任务列表")
async def list_tasks(
    request: Request, 
    user_context: UserContext = Depends(get_user_context),
    limit: int = Query(100, ge=1, le=1000)
):
    """获取指定用户的任务列表"""
    user_task_service: UserTaskService = request.app.state.user_task_service
    tasks = user_task_service.list_user_tasks(user_context.user_id, limit)
    return tasks

@router.get("/{user_id}/tasks/{task_id}", response_model=TaskStatusData, summary="获取指定任务详情")
async def get_task(
    task_id: str,
    request: Request,
    user_context: UserContext = Depends(get_user_context)
):
    """获取指定用户的指定任务详细信息。"""
    user_task_service: UserTaskService = request.app.state.user_task_service
    task = user_task_service.get_user_task(user_context.user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    return task

@router.get("/{user_id}/tasks/{task_id}/result", response_model=TaskResultResponse, summary="获取任务结果")
async def get_task_result(
    task_id: str,
    request: Request,
    user_context: UserContext = Depends(get_user_context)
):
    """获取指定用户的指定任务结果。仅当任务成功完成后才可用。"""
    user_task_service: UserTaskService = request.app.state.user_task_service
    task = user_task_service.get_user_task(user_context.user_id, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    
    if task.status != "completed" or not task.result:
        raise HTTPException(status_code=404, detail="任务结果尚不可用或任务未成功")
        
    # 安全地构建TaskResult对象
    try:
        raw_outputs = task.result.get('output', {})
        output_images = []

        for node_id, node_output in raw_outputs.items():
            if 'images' in node_output:
                for img_data in node_output['images']:
                    # 构建图像访问URL
                    full_url = f"/view?filename={img_data.get('filename')}&subfolder={img_data.get('subfolder')}&type={img_data.get('type')}"
                    output_images.append(OutputImage(
                        filename=img_data.get("filename", "unknown"),
                        url=full_url,
                        size=0 # 暂时无法获取
                    ))

        duration = task.completed_at - task.started_at if task.completed_at and task.started_at else 0

        task_result_data = TaskResult(
            output_images=output_images,
            duration=duration,
            style_applied=task.style_id
        )
    except Exception as e:
        logger.error(f"构建任务结果失败: {task_id} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="无法解析任务结果")

    return TaskResultResponse(
        success=True,
        data=task_result_data
    )

@router.delete("/{user_id}/tasks/{task_id}", response_model=ApiResponse, summary="取消正在进行中的任务")
async def cancel_task(
    task_id: str,
    request: Request,
    user_context: UserContext = Depends(get_user_context)
):
    """取消指定用户的一个正在进行中的任务。"""
    # 这是一个占位符，因为UserTaskService尚未有取消方法
    # 在实际实现中，这将调用类似于：
    # await user_task_service.cancel_task(user_context.user_id, task_id)
    logger.warning(f"用户 {user_context.user_id} 请求取消任务 {task_id}，但取消功能待实现。")
    return ApiResponse(success=True, data={"message": "任务取消功能待实现"})