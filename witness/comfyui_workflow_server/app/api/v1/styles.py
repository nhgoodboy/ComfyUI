"""
风格API端点

提供风格发现、搜索和转换功能的REST API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Request, Depends
from typing import List, Optional, Dict
import asyncio
import logging
from ...models.api_models import (
    StyleInfo, TransformRequest, TransformResponse, 
    ApiResponse, TaskStatus
)
from ...schemas.request import StyleTransformRequest
from ...middleware.user_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/styles", tags=["styles"])

@router.get("/styles", response_model=List[StyleInfo])
async def get_styles(request: Request):
    """获取所有风格"""
    style_service = request.app.state.style_service
    try:
        styles = await style_service.get_all_styles()
        return styles
    except Exception as e:
        logger.error(f"获取风格列表失败: {e}")
        return []

@router.get("/search", response_model=ApiResponse)
async def search_styles(request: Request, q: str = Query(..., description="搜索关键词")):
    """搜索风格"""
    style_service = request.app.state.style_service
    try:
        styles = await style_service.search_styles(q)
        return ApiResponse(success=True, data=styles)
    except Exception as e:
        logger.error(f"搜索风格失败: {e}")
        return ApiResponse(success=False, error=str(e))

@router.get("/{style_id}", response_model=ApiResponse)
async def get_style(style_id: str, request: Request):
    """获取特定风格"""
    style_service = request.app.state.style_service
    try:
        style = await style_service.get_style(style_id)
        if not style:
            raise HTTPException(status_code=404, detail="风格不存在")
        return ApiResponse(success=True, data=style)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取风格失败: {e}")
        return ApiResponse(success=False, error=str(e))

@router.post("/transform", response_model=TransformResponse)
async def transform_image(request: TransformRequest, req: Request, user_id: str = Depends(get_current_user_id)):
    """执行风格转换"""
    try:
        # 验证风格存在
        style_service = req.app.state.style_service
        style = await style_service.get_style(request.style_id)
        if not style:
            raise HTTPException(status_code=404, detail="风格不存在")
        
        # 创建用户任务
        task_id = await style_service.create_task(
            user_id=user_id,
            style_id=request.style_id,
            input_image_path=request.image_url
        )
        
        logger.info(f"用户风格转换任务创建: {user_id} - {task_id} - {request.style_id}")
        
        return TransformResponse(
            success=True,
            task_id=task_id,
            user_id=user_id,
            estimated_time=style.estimated_time
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交转换任务失败: {user_id} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/count", response_model=ApiResponse)
async def get_style_count(request: Request):
    """获取风格数量"""
    style_service = request.app.state.style_service
    try:
        count = await style_service.get_style_count()
        return ApiResponse(success=True, data={"count": count})
    except Exception as e:
        logger.error(f"获取风格数量失败: {e}")
        return ApiResponse(success=False, error=str(e))

@router.post("/reload", response_model=ApiResponse)
async def reload_styles(request: Request):
    """重新加载风格配置"""
    style_service = request.app.state.style_service
    try:
        await style_service.reload_styles()
        styles = await style_service.get_all_styles()
        return ApiResponse(success=True, data={
            "message": "风格配置重新加载成功",
            "count": len(styles)
        })
    except Exception as e:
        logger.error(f"重新加载风格配置失败: {e}")
        return ApiResponse(success=False, error=str(e))

@router.post("/styles/{style_id}/transform", response_model=Dict[str, str])
async def transform_image_with_style(
    style_id: str,
    request: Request,
    transform_request: StyleTransformRequest = Depends(StyleTransformRequest.as_form)
):
    """使用指定风格转换图像"""
    style_service = request.app.state.style_service
    task_id = await style_service.process_transform_request(
        style_id=style_id,
        user_id="default_user",  # 以后可以从认证信息中获取
        image_data=transform_request.image.file.read(),
        filename=transform_request.image.filename
    )
    return {"task_id": task_id} 