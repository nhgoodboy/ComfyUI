"""
风格API端点

提供风格发现、搜索和转换功能的REST API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Request, Depends
from typing import List, Optional
import asyncio
import logging
from ...models.api_models import (
    StyleInfo, TransformRequest, TransformResponse, 
    ApiResponse, TaskStatus
)
from ...services.style_service import style_service
from ...services import user_task_service
from ...middleware.user_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/styles", tags=["styles"])

@router.get("/", response_model=ApiResponse)
async def get_styles():
    """获取所有风格"""
    try:
        styles = await style_service.get_all_styles()
        return ApiResponse(success=True, data=styles)
    except Exception as e:
        logger.error(f"获取风格列表失败: {e}")
        return ApiResponse(success=False, error=str(e))

@router.get("/search", response_model=ApiResponse)
async def search_styles(q: str = Query(..., description="搜索关键词")):
    """搜索风格"""
    try:
        styles = await style_service.search_styles(q)
        return ApiResponse(success=True, data=styles)
    except Exception as e:
        logger.error(f"搜索风格失败: {e}")
        return ApiResponse(success=False, error=str(e))

@router.get("/{style_id}", response_model=ApiResponse)
async def get_style(style_id: str):
    """获取特定风格"""
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
        style = await style_service.get_style(request.style_id)
        if not style:
            raise HTTPException(status_code=404, detail="风格不存在")
        
        # 创建用户任务
        task_id = await user_task_service.create_task(
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
async def get_style_count():
    """获取风格数量"""
    try:
        count = await style_service.get_style_count()
        return ApiResponse(success=True, data={"count": count})
    except Exception as e:
        logger.error(f"获取风格数量失败: {e}")
        return ApiResponse(success=False, error=str(e))

@router.post("/reload", response_model=ApiResponse)
async def reload_styles():
    """重新加载风格配置"""
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