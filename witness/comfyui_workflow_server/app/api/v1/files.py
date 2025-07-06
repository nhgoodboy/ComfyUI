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
from .auth import get_current_user

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
    try:
        # 验证文件扩展名
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_extension}. 支持的类型: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # 读取文件内容
        file_content = await file.read()
        
        # 验证文件大小
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件过大: {len(file_content) / 1024 / 1024:.2f} MB. 最大允许: {MAX_FILE_SIZE / 1024 / 1024} MB"
            )
        
        # 使用用户文件服务保存文件
        file_info = await user_file_service.save_upload_file(
            user_id=user.username,
            file_content=file_content,
            filename=file.filename
        )
        
        return file_info
        
    except HTTPException:
        raise
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
    return ApiResponse(message=f"文件 {file_id} 已成功删除")

@router.post("/cleanup", response_model=ApiResponse)
async def cleanup_old_files(max_age_hours: int = 24, user_id: str = Depends(get_current_user_id)):
    """清理用户过期文件"""
    try:
        # 管理员权限检查可以在这里添加
        # 现在只允许用户清理自己的文件
        user_file_service.cleanup_old_files(max_age_hours)
        
        return ApiResponse(
            success=True,
            data={
                "message": f"清理完成，清理了 {max_age_hours} 小时前的过期文件",
                "max_age_hours": max_age_hours
            }
        )
        
    except Exception as e:
        logger.error(f"清理文件失败: {user_id} - {e}")
        return ApiResponse(success=False, error=str(e))

@router.get("/stats", response_model=ApiResponse)
async def get_user_file_stats(user_id: str = Depends(get_current_user_id)):
    """获取用户文件统计"""
    try:
        storage_used = user_file_service.get_user_storage_usage(user_id)
        files = user_file_service.list_user_files(user_id, 1000)
        
        return ApiResponse(
            success=True,
            data={
                "user_id": user_id,
                "total_files": len(files),
                "storage_used": storage_used,
                "storage_used_mb": round(storage_used / 1024 / 1024, 2)
            }
        )
        
    except Exception as e:
        logger.error(f"获取用户文件统计失败: {user_id} - {e}")
        return ApiResponse(success=False, error=str(e))

@router.get("/", response_model=UserFilesResponse)
async def list_user_files(request: Request, user_id: str = Depends(get_current_user_id), limit: int = 100):
    """获取用户文件列表"""
    user_file_service = request.app.state.user_file_service
    # ... (rest of the function)

@router.delete("/{file_id}", response_model=ApiResponse)
async def delete_user_file(request: Request, file_id: str, user_id: str = Depends(get_current_user_id)):
    """删除文件"""
    user_file_service = request.app.state.user_file_service
    # ... (rest of the function) 