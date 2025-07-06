"""
风格API端点

提供风格发现、搜索和转换功能的REST API
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends, Body, File, UploadFile, Form
from typing import List, Optional, Dict
import logging
from ...models.api_models import StyleInfo, TransformRequest, ApiResponse, TaskStatusData
from ...models.user_models import APIUser
from ...services.style_service import StyleService
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/styles", tags=["Styles"])

@router.get("/", response_model=List[StyleInfo], summary="获取所有可用风格")
async def get_styles(request: Request):
    """获取所有公开可用的风格列表。"""
    style_service: StyleService = request.app.state.style_service
    try:
        styles = style_service.get_all_styles()
        return styles
    except Exception as e:
        logger.error(f"获取风格列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取风格列表时发生内部错误")

@router.get("/search", response_model=List[StyleInfo], summary="搜索风格")
async def search_styles(request: Request, q: str = Query(..., description="搜索关键词")):
    """根据关键词搜索风格。"""
    style_service: StyleService = request.app.state.style_service
    try:
        styles = style_service.search_styles(q)
        return styles
    except Exception as e:
        logger.error(f"搜索风格失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="搜索风格时发生内部错误")

@router.get("/{style_id}", response_model=StyleInfo, summary="获取特定风格详情")
async def get_style(style_id: str, request: Request):
    """获取特定风格的详细信息。"""
    style_service: StyleService = request.app.state.style_service
    style = style_service.get_style(style_id)
    if not style:
        raise HTTPException(status_code=404, detail="风格不存在")
    return style

@router.post("/transform", response_model=TaskStatusData, summary="提交风格转换任务")
async def transform_image(
    req: Request,
    request: TransformRequest, 
    user: APIUser = Depends(get_current_user)
):
    """
    为当前认证用户提交一个风格转换任务。
    这是一个长轮询任务，会返回一个任务ID供后续状态查询。
    """
    style_service: StyleService = req.app.state.style_service
    user_task_service = req.app.state.user_task_service
    
    # 验证风格存在
    style = style_service.get_style(request.style_id)
    if not style:
        raise HTTPException(status_code=404, detail="风格不存在")
    
    try:
        # 创建用户任务
        task_id = await user_task_service.create_task(
            user_id=user.username,
            style_id=request.style_id,
            input_image_path=request.image_url
        )
        
        task_data = user_task_service.get_user_task(user.username, task_id)
        if not task_data:
             raise HTTPException(status_code=404, detail="任务创建后未找到")

        return task_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"提交转换任务失败: {user.username} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="提交转换任务时发生内部错误")

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

@router.post("/styles/transform", response_model=ApiResponse)
async def transform_image_by_style(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    image: UploadFile = File(...),
    strength: Optional[float] = Form(None)
):
    """使用指定风格转换图片 (multipart/form-data)"""
    # ... logic using image and strength ...
    style_service = request.app.state.style_service
    task_service = request.app.state.user_task_service
    file_service = request.app.state.user_file_service

    # ... (rest of the function remains the same)
    # ... (it will now use the service instances from request.app.state)
    # ... 