"""
File API endpoints
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from ..models.requests import FileGetRequest, FileListRequest
from ..services.rpc_client import rpc_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])

# 配置上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    param_name: str = Form(...)
):
    """Upload file for workflow parameter"""
    try:
        # 验证文件类型
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        
        # 保存文件
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # 构建访问URL (相对于测试系统的静态文件服务)
        file_url = f"http://localhost:8001/uploads/{unique_filename}"
        
        logger.info(f"File uploaded: {file.filename} -> {unique_filename}")
        
        return {
            "success": True,
            "data": {
                "filename": unique_filename,
                "original_name": file.filename,
                "url": file_url,
                "size": len(content),
                "param_name": param_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/image/{filename}")
async def get_output_image(filename: str):
    """Get output image"""
    try:
        logger.debug(f"Getting output image: {filename}")
        
        async with rpc_client:
            result = await rpc_client.get_output_image(filename)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to get output image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/image/info/{filename}")
async def get_output_image_info(filename: str):
    """Get output image information"""
    try:
        logger.debug(f"Getting output image info: {filename}")
        
        async with rpc_client:
            result = await rpc_client.get_output_image_info(filename)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to get output image info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/output")
async def list_output_images(
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    pattern: Optional[str] = "*"
):
    """List output images"""
    try:
        logger.debug(f"Listing output images: limit={limit}, offset={offset}, pattern={pattern}")
        
        async with rpc_client:
            result = await rpc_client.list_output_images(limit, offset, pattern)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to list output images: {e}")
        raise HTTPException(status_code=500, detail=str(e))