"""
用户文件API端点

提供基于user_id的文件上传、管理功能
"""

from fastapi import APIRouter, UploadFile, File, Request, HTTPException, Depends, Query, Path
from fastapi.responses import FileResponse
from typing import List
import uuid
import time
import logging
from pathlib import Path as PathLib
from ...models.api_models import UploadFileResponse, ApiResponse, UserFilesResponse, UserFileInfo
from ...models.user_models import UserContext
from ...services.user_file_service import UserFileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["User Files"])

# 配置上传参数
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def get_user_context(user_id: str = Path(..., description="用户ID")) -> UserContext:
    """从路径参数获取用户上下文"""
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="用户ID不能为空")
    return UserContext(user_id=user_id.strip())

@router.post("/{user_id}/files/upload", response_model=UserFileInfo, summary="上传单个文件")
async def upload_file(
    request: Request,
    user_context: UserContext = Depends(get_user_context),
    file: UploadFile = File(...)
):
    """
    为指定用户上传一个文件。
    - **user_id**: 用户ID（路径参数）
    - 文件大小限制: 10MB
    - 支持的格式: .jpg, .jpeg, .png, .gif, .bmp, .webp
    """
    user_file_service: UserFileService = request.app.state.user_file_service
    
    if file.filename is None:
        raise HTTPException(status_code=400, detail="缺少文件名")

    file_extension = PathLib(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_extension}. 支持的类型: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大: {len(file_content) / 1024 / 1024:.2f} MB. 最大允许: {MAX_FILE_SIZE / 1024 / 1024} MB"
        )
        
    try:
        file_id = await user_file_service.save_upload_file(
            user_id=user_context.user_id,
            file_content=file_content,
            filename=file.filename
        )
        # 获取文件信息对象
        file_info = user_file_service.get_user_file(user_context.user_id, file_id)
        if not file_info:
            raise HTTPException(status_code=500, detail="文件保存成功但无法获取文件信息")
        return file_info
    except Exception as e:
        logger.error(f"文件上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="文件上传时发生内部错误")

@router.get("/{user_id}/files", response_model=UserFilesResponse, summary="获取用户的文件列表")
def list_user_files(
    request: Request,
    user_context: UserContext = Depends(get_user_context),
    limit: int = Query(100, ge=1, le=1000)
):
    """获取指定用户的文件列表。"""
    user_file_service: UserFileService = request.app.state.user_file_service
    files = user_file_service.list_user_files(user_context.user_id, limit)
    return UserFilesResponse(
        success=True,
        user_id=user_context.user_id,
        files=files,
        total=len(files)
    )

@router.get("/{user_id}/files/{file_id}", response_model=UserFileInfo, summary="获取指定文件的信息")
def get_user_file_info(
    file_id: str,
    request: Request,
    user_context: UserContext = Depends(get_user_context)
):
    """获取指定用户拥有的某个文件的详细信息。"""
    user_file_service: UserFileService = request.app.state.user_file_service
    file_info = user_file_service.get_user_file(user_context.user_id, file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件未找到或无权访问")
    return file_info

@router.delete("/{user_id}/files/{file_id}", response_model=ApiResponse, summary="删除指定文件")
def delete_user_file(
    file_id: str,
    request: Request,
    user_context: UserContext = Depends(get_user_context)
):
    """删除指定用户拥有的某个文件。"""
    user_file_service: UserFileService = request.app.state.user_file_service
    success = user_file_service.delete_user_file(user_context.user_id, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件删除失败，可能文件不存在或无权访问")
    return ApiResponse(success=True, data={"message": f"文件 {file_id} 已成功删除"}, error=None)

@router.get("/{user_id}/files/stats", response_model=ApiResponse, summary="获取用户的文件统计信息")
def get_user_file_stats(
    request: Request,
    user_context: UserContext = Depends(get_user_context)
):
    """获取指定用户的文件总数和存储使用情况。"""
    user_file_service: UserFileService = request.app.state.user_file_service
    try:
        files = user_file_service.list_user_files(user_context.user_id, limit=10000) # 使用大限制获取所有文件
        storage_used = user_file_service.get_user_storage_usage(user_context.user_id)
        stats = {
            "total_files": len(files),
            "storage_used_bytes": storage_used,
            "storage_used_mb": round(storage_used / (1024 * 1024), 2)
        }
        return ApiResponse(success=True, data=stats, error=None)
    except Exception as e:
        logger.error(f"获取用户 '{user_context.user_id}' 文件统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取统计信息时发生内部错误") 