"""
多用户文件服务

实现用户文件隔离和管理
"""

import os
import uuid
import time
import shutil
from typing import Dict, List, Optional
from pathlib import Path
from ..models.user_models import UserFileInfo
import logging

logger = logging.getLogger(__name__)

class UserFileService:
    """多用户文件服务"""
    
    def __init__(self, base_upload_dir: str = "uploads", base_output_dir: str = "outputs"):
        self.base_upload_dir = Path(base_upload_dir)
        self.base_output_dir = Path(base_output_dir)
        self.user_files: Dict[str, Dict[str, UserFileInfo]] = {}  # {user_id: {file_id: file_info}}
        
        # 确保基础目录存在
        self.base_upload_dir.mkdir(exist_ok=True)
        self.base_output_dir.mkdir(exist_ok=True)
    
    def _get_user_upload_dir(self, user_id: str) -> Path:
        """获取用户上传目录"""
        user_dir = self.base_upload_dir / user_id
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    def _get_user_output_dir(self, user_id: str) -> Path:
        """获取用户输出目录"""
        user_dir = self.base_output_dir / user_id
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    async def save_upload_file(self, user_id: str, file_content: bytes, filename: str) -> str:
        """保存用户上传文件"""
        try:
            # 生成文件ID
            file_id = str(uuid.uuid4())
            
            # 获取文件扩展名
            file_extension = Path(filename).suffix
            stored_filename = f"{file_id}{file_extension}"
            
            # 获取用户目录
            user_dir = self._get_user_upload_dir(user_id)
            file_path = user_dir / stored_filename
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # 创建文件信息
            file_info = UserFileInfo(
                file_id=file_id,
                user_id=user_id,
                filename=stored_filename,
                original_name=filename,
                url=f"/files/{user_id}/{stored_filename}",
                size=len(file_content),
                created_at=time.time()
            )
            
            # 存储文件信息
            if user_id not in self.user_files:
                self.user_files[user_id] = {}
            self.user_files[user_id][file_id] = file_info
            
            logger.info(f"用户文件保存成功: {user_id} - {file_id} - {filename}")
            return file_id
            
        except Exception as e:
            logger.error(f"保存用户文件失败: {user_id} - {filename} - {e}")
            raise
    
    async def save_output_file(self, user_id: str, task_id: str, source_path: str, filename: str) -> str:
        """保存用户输出文件"""
        try:
            # 生成文件ID
            file_id = str(uuid.uuid4())
            
            # 获取文件扩展名
            file_extension = Path(filename).suffix
            stored_filename = f"{task_id}_{file_id}{file_extension}"
            
            # 获取用户输出目录
            user_dir = self._get_user_output_dir(user_id)
            dest_path = user_dir / stored_filename
            
            # 复制文件
            shutil.copy2(source_path, dest_path)
            
            # 获取文件大小
            file_size = dest_path.stat().st_size
            
            # 创建文件信息
            file_info = UserFileInfo(
                file_id=file_id,
                user_id=user_id,
                filename=stored_filename,
                original_name=filename,
                url=f"/outputs/{user_id}/{stored_filename}",
                size=file_size,
                created_at=time.time()
            )
            
            # 存储文件信息
            if user_id not in self.user_files:
                self.user_files[user_id] = {}
            self.user_files[user_id][file_id] = file_info
            
            logger.info(f"用户输出文件保存成功: {user_id} - {file_id} - {filename}")
            return file_id
            
        except Exception as e:
            logger.error(f"保存用户输出文件失败: {user_id} - {filename} - {e}")
            raise
    
    def get_user_file(self, user_id: str, file_id: str) -> Optional[UserFileInfo]:
        """获取用户文件信息"""
        if user_id not in self.user_files:
            return None
        return self.user_files[user_id].get(file_id)
    
    def get_user_file_path(self, user_id: str, file_id: str) -> Optional[Path]:
        """获取用户文件路径"""
        file_info = self.get_user_file(user_id, file_id)
        if not file_info:
            return None
        
        # 判断是上传文件还是输出文件
        if file_info.url.startswith("/files/"):
            return self._get_user_upload_dir(user_id) / file_info.filename
        elif file_info.url.startswith("/outputs/"):
            return self._get_user_output_dir(user_id) / file_info.filename
        else:
            return None
    
    def list_user_files(self, user_id: str, limit: int = 100) -> List[UserFileInfo]:
        """列出用户文件"""
        if user_id not in self.user_files:
            return []
        
        files = list(self.user_files[user_id].values())
        # 按创建时间倒序排序
        files.sort(key=lambda x: x.created_at, reverse=True)
        return files[:limit]
    
    def delete_user_file(self, user_id: str, file_id: str) -> bool:
        """删除用户文件"""
        try:
            file_info = self.get_user_file(user_id, file_id)
            if not file_info:
                return False
            
            # 删除物理文件
            file_path = self.get_user_file_path(user_id, file_id)
            if file_path and file_path.exists():
                file_path.unlink()
            
            # 删除文件信息
            del self.user_files[user_id][file_id]
            
            logger.info(f"用户文件删除成功: {user_id} - {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除用户文件失败: {user_id} - {file_id} - {e}")
            return False
    
    def get_user_storage_usage(self, user_id: str) -> int:
        """获取用户存储使用量"""
        if user_id not in self.user_files:
            return 0
        
        total_size = 0
        for file_info in self.user_files[user_id].values():
            total_size += file_info.size
        
        return total_size
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """清理过期文件"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for user_id in list(self.user_files.keys()):
                files_to_remove = []
                for file_id, file_info in self.user_files[user_id].items():
                    if current_time - file_info.created_at > max_age_seconds:
                        files_to_remove.append(file_id)
                
                for file_id in files_to_remove:
                    self.delete_user_file(user_id, file_id)
                
                # 如果用户没有文件了，清理用户记录
                if not self.user_files[user_id]:
                    del self.user_files[user_id]
            
            logger.info(f"清理过期文件完成，清理时间: {max_age_hours}小时")
            
        except Exception as e:
            logger.error(f"清理过期文件失败: {e}")
    
    def cleanup_user_directories(self):
        """清理空的用户目录"""
        try:
            # 清理上传目录
            for user_dir in self.base_upload_dir.iterdir():
                if user_dir.is_dir() and not any(user_dir.iterdir()):
                    user_dir.rmdir()
            
            # 清理输出目录
            for user_dir in self.base_output_dir.iterdir():
                if user_dir.is_dir() and not any(user_dir.iterdir()):
                    user_dir.rmdir()
            
            logger.info("清理空用户目录完成")
            
        except Exception as e:
            logger.error(f"清理空用户目录失败: {e}") 