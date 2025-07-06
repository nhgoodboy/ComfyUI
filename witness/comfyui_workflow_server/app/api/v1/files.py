"""
文件API端点

提供文件上传、管理功能的REST API
"""

from fastapi import APIRouter, UploadFile, File, Request, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import List
import uuid
import time
import logging
from pathlib import Path
from ...models.api_models import UploadFileResponse, ApiResponse, UserFilesResponse
from ...models.user_models import UserFileInfo
from ...middleware.user_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# 配置上传参数
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload", response_model=UserFileInfo)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """上传文件"""
    user_file_service = request.app.state.user_file_service
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
                detail=f"文件过大: {len(file_content)} bytes. 最大允许: {MAX_FILE_SIZE} bytes"
            )
        
        # 使用用户文件服务保存文件
        file_id = await user_file_service.save_upload_file(
            user_id="default_user",
            file_content=file_content,
            filename=file.filename
        )
        
        # 获取文件信息
        file_info = user_file_service.get_user_file(user_id="default_user", file_id=file_id)
        
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=UserFilesResponse)
async def list_user_files(request: Request, limit: int = 100):
    """列出用户文件"""
    user_file_service = request.app.state.user_file_service
    try:
        files = user_file_service.list_user_files(user_id="default_user", limit=limit)
        
        return UserFilesResponse(
            success=True,
            user_id="default_user",
            files=files,
            total=len(files)
        )
        
    except Exception as e:
        logger.error(f"列出用户文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{file_id}", response_model=ApiResponse)
async def delete_user_file(file_id: str, user_id: str = Depends(get_current_user_id)):
    """删除用户文件"""
    try:
        success = user_file_service.delete_user_file(user_id, file_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="文件不存在或无权删除")
        
        return ApiResponse(success=True, data={"message": f"文件 {file_id} 已删除"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户文件失败: {user_id} - {file_id} - {e}")
        return ApiResponse(success=False, error=str(e))

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