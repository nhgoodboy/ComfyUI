"""
风格API端点

提供风格发现、搜索功能的REST API（全局共享）
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional, Dict
import logging
from ...models.api_models import StyleInfo
from ...services.style_service import StyleService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/styles", tags=["Styles"])

@router.get("/", response_model=List[StyleInfo], summary="获取所有可用风格")
async def get_styles(request: Request):
    """获取所有公开可用的风格列表。"""
    style_service: StyleService = request.app.state.style_service
    try:
        styles = await style_service.get_all_styles()
        return styles
    except Exception as e:
        logger.error(f"获取风格列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取风格列表时发生内部错误")

@router.get("/search", response_model=List[StyleInfo], summary="搜索风格")
async def search_styles(request: Request, q: str = Query(..., description="搜索关键词")):
    """根据关键词搜索风格。"""
    style_service: StyleService = request.app.state.style_service
    try:
        styles = await style_service.search_styles(q)
        return styles
    except Exception as e:
        logger.error(f"搜索风格失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="搜索风格时发生内部错误")

@router.get("/{style_id}", response_model=StyleInfo, summary="获取特定风格详情")
async def get_style(style_id: str, request: Request):
    """获取特定风格的详细信息。"""
    style_service: StyleService = request.app.state.style_service
    style = await style_service.get_style(style_id)
    if not style:
        raise HTTPException(status_code=404, detail="风格不存在")
    return style