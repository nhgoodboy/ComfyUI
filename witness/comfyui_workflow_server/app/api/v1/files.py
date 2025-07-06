"""
文件API端点

提供文件上传、管理功能的REST API
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import uuid
import time
import logging
from pathlib import Path
from ...models.api_models import UploadFileResponse, ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# 配置上传参数
UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 确保上传目录存在
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload", response_model=UploadFileResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文件"""
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
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_extension}"
        file_path = UPLOAD_DIR / filename
        
        # 保存文件
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 计算过期时间（24小时后）
        expires_at = time.time() + 24 * 60 * 60
        
        return UploadFileResponse(
            success=True,
            data={
                "file_id": file_id,
                "filename": filename,
                "original_name": file.filename,
                "url": f"/uploads/{filename}",
                "size": len(file_content),
                "expires_at": expires_at
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return UploadFileResponse(success=False, error=str(e))

@router.get("/", response_model=ApiResponse)
async def list_files():
    """列出上传的文件"""
    try:
        files = []
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created_at": stat.st_ctime,
                    "url": f"/uploads/{file_path.name}"
                })
        
        # 按创建时间排序
        files.sort(key=lambda x: x["created_at"], reverse=True)
        
        return ApiResponse(success=True, data=files)
        
    except Exception as e:
        logger.error(f"列出文件失败: {e}")
        return ApiResponse(success=False, error=str(e))

@router.delete("/{filename}", response_model=ApiResponse)
async def delete_file(filename: str):
    """删除文件"""
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="不是有效的文件")
        
        file_path.unlink()
        
        return ApiResponse(success=True, data={"message": f"文件 {filename} 已删除"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        return ApiResponse(success=False, error=str(e))

@router.post("/cleanup", response_model=ApiResponse)
async def cleanup_old_files(max_age_hours: int = 24):
    """清理过期文件"""
    try:
        current_time = time.time()
        max_age_seconds = max_age_hours * 60 * 60
        deleted_count = 0
        
        for file_path in UPLOAD_DIR.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_ctime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
        
        return ApiResponse(
            success=True,
            data={
                "message": f"清理完成，删除了 {deleted_count} 个过期文件",
                "deleted_count": deleted_count
            }
        )
        
    except Exception as e:
        logger.error(f"清理文件失败: {e}")
        return ApiResponse(success=False, error=str(e)) 