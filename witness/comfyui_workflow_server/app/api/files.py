"""
文件访问API

提供输出图片的访问接口
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["文件访问"])

@router.get("/output/{filename}")
async def get_output_image(filename: str):
    """获取输出图片"""
    try:
        output_dir = Path("outputs")
        file_path = output_dir / filename
        
        if not file_path.exists():
            logger.warning(f"请求的文件不存在: {filename}")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_path.is_file():
            logger.warning(f"请求的路径不是文件: {filename}")
            raise HTTPException(status_code=404, detail="不是有效文件")
        
        # 检查文件扩展名
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
        if file_path.suffix.lower() not in allowed_extensions:
            logger.warning(f"不支持的文件类型: {filename}")
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        # 确定MIME类型
        mime_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }
        
        media_type = mime_type_map.get(file_path.suffix.lower(), 'image/png')
        
        logger.info(f"提供文件访问: {filename}")
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件失败: {filename}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")

@router.get("/output/{filename}/info")
async def get_output_image_info(filename: str):
    """获取输出图片信息"""
    try:
        output_dir = Path("outputs")
        file_path = output_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="不是有效文件")
        
        # 获取文件信息
        stat = file_path.stat()
        
        return {
            "filename": filename,
            "size": stat.st_size,
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
            "extension": file_path.suffix.lower(),
            "url": f"/api/files/output/{filename}",
            "static_url": f"/outputs/{filename}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件信息失败: {filename}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")