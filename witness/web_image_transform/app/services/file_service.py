import os
import uuid
import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any
import aiofiles
from PIL import Image
import hashlib

from ..config import settings
from ..utils.logger import get_logger, log_file_upload

logger = get_logger("file_service")

class FileService:
    """文件处理服务"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.output_dir = Path(settings.OUTPUT_DIR)
        self.allowed_extensions = set(settings.ALLOWED_EXTENSIONS)
        self.max_file_size = settings.MAX_FILE_SIZE
    
    def _is_allowed_file(self, filename: str) -> bool:
        """检查文件扩展名是否允许"""
        if '.' not in filename:
            return False
        
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in self.allowed_extensions
    
    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    async def validate_image(self, file_path: Path) -> Dict[str, Any]:
        """验证图像文件"""
        try:
            # 检查文件大小
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                raise ValueError(f"文件大小超过限制: {file_size} > {self.max_file_size}")
            
            # 使用PIL验证图像
            with Image.open(file_path) as img:
                # 获取图像信息
                image_info = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.size[0],
                    "height": img.size[1],
                    "file_size": file_size
                }
                
                # 检查图像尺寸
                if img.size[0] < 64 or img.size[1] < 64:
                    raise ValueError("图像尺寸太小，最小64x64像素")
                
                if img.size[0] > 4096 or img.size[1] > 4096:
                    raise ValueError("图像尺寸太大，最大4096x4096像素")
                
                logger.info(f"图像验证成功: {image_info}")
                return image_info
                
        except Exception as e:
            logger.error(f"图像验证失败: {e}")
            raise
    
    async def save_uploaded_file(self, file_content: bytes, 
                               original_filename: str) -> Dict[str, Any]:
        """保存上传的文件"""
        try:
            # 验证文件名
            if not self._is_allowed_file(original_filename):
                raise ValueError(f"不支持的文件类型: {original_filename}")
            
            # 生成唯一文件名
            file_extension = Path(original_filename).suffix.lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = self.upload_dir / unique_filename
            
            # 保存文件
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # 验证图像
            image_info = await self.validate_image(file_path)
            
            # 计算文件哈希
            file_hash = self._get_file_hash(file_path)
            
            # 记录日志
            log_file_upload(original_filename, len(file_content), settings.DEFAULT_USER_ID)
            
            result = {
                "success": True,
                "filename": unique_filename,
                "original_filename": original_filename,
                "file_path": str(file_path),
                "file_size": len(file_content),
                "file_hash": file_hash,
                "image_info": image_info,
                "url": f"/uploads/{unique_filename}"
            }
            
            logger.info(f"文件保存成功: {result}")
            return result
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            # 清理可能创建的文件
            if 'file_path' in locals() and file_path.exists():
                file_path.unlink()
            raise
    
    async def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        try:
            file_path = self.upload_dir / filename
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            
            # 获取MIME类型
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            info = {
                "filename": filename,
                "file_path": str(file_path),
                "file_size": stat.st_size,
                "created_time": stat.st_ctime,
                "modified_time": stat.st_mtime,
                "mime_type": mime_type,
                "url": f"/uploads/{filename}"
            }
            
            # 如果是图像文件，获取图像信息
            if mime_type and mime_type.startswith('image/'):
                try:
                    image_info = await self.validate_image(file_path)
                    info["image_info"] = image_info
                except Exception as e:
                    logger.warning(f"获取图像信息失败: {e}")
            
            return info
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None
    
    async def delete_file(self, filename: str) -> bool:
        """删除文件"""
        try:
            file_path = self.upload_dir / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"文件已删除: {filename}")
                return True
            else:
                logger.warning(f"文件不存在: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False
    
    async def list_files(self, directory: str = "uploads", 
                        limit: int = 100) -> List[Dict[str, Any]]:
        """列出文件"""
        try:
            if directory == "uploads":
                target_dir = self.upload_dir
            elif directory == "outputs":
                target_dir = self.output_dir
            else:
                raise ValueError(f"不支持的目录: {directory}")
            
            files = []
            for file_path in target_dir.iterdir():
                if file_path.is_file() and len(files) < limit:
                    file_info = await self.get_file_info(file_path.name)
                    if file_info:
                        files.append(file_info)
            
            # 按修改时间排序（最新的在前）
            files.sort(key=lambda x: x.get("modified_time", 0), reverse=True)
            
            return files
            
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return []
    
    async def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """清理旧文件"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)
            
            deleted_count = 0
            
            # 清理上传目录
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"已删除旧文件: {file_path.name}")
                    except Exception as e:
                        logger.warning(f"删除文件失败: {file_path.name} - {e}")
            
            # 清理输出目录
            for file_path in self.output_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"已删除旧输出文件: {file_path.name}")
                    except Exception as e:
                        logger.warning(f"删除输出文件失败: {file_path.name} - {e}")
            
            if deleted_count > 0:
                logger.info(f"清理完成，删除了 {deleted_count} 个旧文件")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")
            return 0
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            upload_files = list(self.upload_dir.iterdir())
            output_files = list(self.output_dir.iterdir())
            
            upload_size = sum(f.stat().st_size for f in upload_files if f.is_file())
            output_size = sum(f.stat().st_size for f in output_files if f.is_file())
            
            stats = {
                "upload_dir": {
                    "path": str(self.upload_dir),
                    "file_count": len([f for f in upload_files if f.is_file()]),
                    "total_size": upload_size,
                    "total_size_mb": round(upload_size / 1024 / 1024, 2)
                },
                "output_dir": {
                    "path": str(self.output_dir),
                    "file_count": len([f for f in output_files if f.is_file()]),
                    "total_size": output_size,
                    "total_size_mb": round(output_size / 1024 / 1024, 2)
                },
                "total": {
                    "file_count": len([f for f in upload_files if f.is_file()]) + len([f for f in output_files if f.is_file()]),
                    "total_size": upload_size + output_size,
                    "total_size_mb": round((upload_size + output_size) / 1024 / 1024, 2)
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            return {}

# 全局文件服务实例
file_service = FileService() 