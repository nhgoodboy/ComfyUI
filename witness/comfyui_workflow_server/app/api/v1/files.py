"""
文件API端点

提供文件上传、管理功能的REST API
"""

from fastapi import APIRouter, UploadFile, File, Request, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from typing import List
import uuid
import time
import logging
from pathlib import Path
from ...models.api_models import UploadFileResponse, ApiResponse, UserFilesResponse, UserFileInfo
from ...models.user_models import APIUser
from ...services.user_file_service import UserFileService
from .auth import get_current_user, get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])

# 配置上传参数
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload", response_model=UserFileInfo, summary="上传单个文件")
async def upload_file(
    request: Request,
    user: APIUser = Depends(get_current_user),
    file: UploadFile = File(...)
):
    """
    为当前认证用户上传一个文件。
    - 文件大小限制: 10MB
    - 支持的格式: .jpg, .jpeg, .png, .gif, .bmp, .webp
    """
    user_file_service: UserFileService = request.app.state.user_file_service
    
    if file.filename is None:
        raise HTTPException(status_code=400, detail="缺少文件名")

    file_extension = Path(file.filename).suffix.lower()
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
            user_id=user.username,
            file_content=file_content,
            filename=file.filename
        )
        # 获取文件信息对象
        file_info = user_file_service.get_user_file(user.username, file_id)
        if not file_info:
            raise HTTPException(status_code=500, detail="文件保存成功但无法获取文件信息")
        return file_info
    except Exception as e:
        logger.error(f"文件上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="文件上传时发生内部错误")

@router.get("/", response_model=UserFilesResponse, summary="获取当前用户的文件列表")
def list_user_files(
    request: Request,
    user: APIUser = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=1000)
):
    """获取当前认证用户的文件列表。"""
    user_file_service: UserFileService = request.app.state.user_file_service
    files = user_file_service.list_user_files(user.username, limit)
    return UserFilesResponse(
        success=True,
        user_id=user.username,
        files=files,
        total=len(files)
    )

@router.get("/{file_id}", response_model=UserFileInfo, summary="获取指定文件的信息")
def get_user_file_info(
    file_id: str,
    request: Request,
    user: APIUser = Depends(get_current_user)
):
    """获取用户拥有的某个文件的详细信息。"""
    user_file_service: UserFileService = request.app.state.user_file_service
    file_info = user_file_service.get_user_file(user.username, file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件未找到或无权访问")
    return file_info

@router.delete("/{file_id}", response_model=ApiResponse, summary="删除指定文件")
def delete_user_file(
    file_id: str,
    request: Request,
    user: APIUser = Depends(get_current_user)
):
    """删除用户拥有的某个文件。"""
    user_file_service: UserFileService = request.app.state.user_file_service
    success = user_file_service.delete_user_file(user.username, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件删除失败，可能文件不存在或无权访问")
    return ApiResponse(success=True, data={"message": f"文件 {file_id} 已成功删除"}, error=None)

@router.post("/cleanup", response_model=ApiResponse, summary="清理所有用户的过期文件 (仅管理员)")
def cleanup_old_files(
    request: Request,
    user: APIUser = Depends(get_admin_user),
    max_age_hours: int = 24
):
    """
    清理系统中所有超过指定小时数的旧文件。
    这是一个管理员权限的操作。
    """
    user_file_service: UserFileService = request.app.state.user_file_service
    try:
        # 注意: service中的cleanup_old_files是全局的
        user_file_service.cleanup_old_files(max_age_hours)
        logger.info(f"管理员 '{user.username}' 触发了文件清理。")
        return ApiResponse(
            success=True,
            data={"message": f"清理任务已成功触发，将清理超过 {max_age_hours} 小时的文件。"},
            error=None
        )
    except Exception as e:
        logger.error(f"管理员 '{user.username}' 清理文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="清理文件时发生内部错误")

@router.get("/stats", response_model=ApiResponse, summary="获取当前用户的文件统计信息")
def get_user_file_stats(
    request: Request,
    user: APIUser = Depends(get_current_user)
):
    """获取当前认证用户的文件总数和存储使用情况。"""
    user_file_service: UserFileService = request.app.state.user_file_service
    try:
        files = user_file_service.list_user_files(user.username, limit=10000) # Use a large limit to get all files
        storage_used = user_file_service.get_user_storage_usage(user.username)
        stats = {
            "total_files": len(files),
            "storage_used_bytes": storage_used,
            "storage_used_mb": round(storage_used / (1024 * 1024), 2)
        }
        return ApiResponse(success=True, data=stats, error=None)
    except Exception as e:
        logger.error(f"获取用户 '{user.username}' 文件统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取统计信息时发生内部错误") 