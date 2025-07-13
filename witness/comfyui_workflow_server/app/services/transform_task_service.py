"""
转换任务服务

集成文件下载和图像风格转换的完整流程
"""

import uuid
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from pathlib import Path

from ..models.user_models import UserTaskData
from ..core.style_registry import StyleRegistry
from ..services.download_service import DownloadService
from ..utils.file_naming import FileNamingUtils
from ..rpc.exceptions import RPCError, RPCTransformError, RPCDownloadError
from ..rpc.error_codes import ErrorCodes

if TYPE_CHECKING:
    from ..services.comfyui_service import ComfyUIService

logger = logging.getLogger(__name__)

# 导入推送管理器
try:
    from ..api.v1.websocket_push import push_manager
except ImportError:
    push_manager = None
    logger.warning("WebSocket 推送管理器不可用")


class TransformTaskService:
    """转换任务服务"""
    
    def __init__(self, comfyui_service: 'ComfyUIService', style_registry: StyleRegistry):
        self.comfyui_service = comfyui_service
        self.style_registry = style_registry
        self.download_service = DownloadService()
        self.file_naming = FileNamingUtils()
        
        # 任务存储：按用户隔离
        self.user_tasks: Dict[str, Dict[str, UserTaskData]] = {}  # {user_id: {task_id: task_data}}
        self.task_to_user: Dict[str, str] = {}  # {task_id: user_id}
        self.prompt_to_task: Dict[str, str] = {}  # {prompt_id: task_id}
        
        # 任务状态枚举
        self.TASK_STATUSES = {
            "pending": "等待处理",
            "downloading": "下载中",
            "downloaded": "下载完成", 
            "processing": "转换中",
            "completed": "已完成",
            "download_failed": "下载失败",
            "processing_failed": "转换失败",
            "cancelled": "已取消"
        }
    
    async def create_transform_task(
        self, 
        user_id: str, 
        style_id: str, 
        image_url: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        创建转换任务（下载 + 转换）
        
        Args:
            user_id: 用户ID
            style_id: 风格ID
            image_url: 图片URL
            progress_callback: 进度回调函数
        
        Returns:
            str: 任务ID
        """
        # 验证参数
        user_id = self.file_naming.validate_user_id(user_id)
        style_id = self.file_naming.validate_style_id(style_id)
        
        # 验证风格存在
        if style_id not in self.style_registry.styles:
            raise RPCTransformError(
                code=ErrorCodes.STYLE_NOT_FOUND,
                message=f"风格不存在: {style_id}",
                details=f"可用风格: {list(self.style_registry.styles.keys())}"
            )
        
        # 验证工作流存在
        if style_id not in self.style_registry.workflows:
            raise RPCTransformError(
                code=ErrorCodes.STYLE_NOT_FOUND,
                message=f"风格工作流不存在: {style_id}",
                details=f"可用工作流: {list(self.style_registry.workflows.keys())}"
            )
        
        # 验证URL中的文件名
        try:
            # 获取已知的风格ID列表
            known_style_ids = list(self.style_registry.styles.keys())
            expected_filename = self.file_naming.validate_url_filename(
                image_url, style_id, user_id, "input", known_style_ids
            )
        except Exception as e:
            raise RPCDownloadError(
                code=ErrorCodes.INVALID_FILENAME_FORMAT,
                message=str(e),
                url=image_url
            )
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        current_time = time.time()
        
        # 创建任务数据
        task_data = UserTaskData(
            task_id=task_id,
            user_id=user_id,
            style_id=style_id,
            status="pending",
            progress=0.0,
            created_at=current_time,
            started_at=None,
            completed_at=None,
            estimated_remaining=None,
            result=None,
            error_message=None
        )
        
        # 添加扩展属性
        task_data.stage = "pending"
        task_data.message = "任务已创建，等待开始"
        task_data.image_url = image_url
        task_data.expected_filename = expected_filename
        task_data.output_filename = self.file_naming.get_output_filename(expected_filename)
        task_data.download_progress = 0.0
        task_data.transform_progress = 0.0
        
        # 存储任务
        if user_id not in self.user_tasks:
            self.user_tasks[user_id] = {}
        
        self.user_tasks[user_id][task_id] = task_data
        self.task_to_user[task_id] = user_id
        
        logger.info(f"创建转换任务: {task_id}, 用户: {user_id}, 风格: {style_id}")
        
        # 推送任务创建消息
        await self._push_task_update(task_data)
        
        # 异步执行任务
        asyncio.create_task(self._execute_transform_task(task_id, progress_callback))
        
        return task_id
    
    async def _execute_transform_task(self, task_id: str, progress_callback: Optional[Callable] = None):
        """执行转换任务的完整流程"""
        user_id = self.task_to_user.get(task_id)
        if not user_id:
            logger.error(f"任务 {task_id} 找不到对应的用户")
            return
        
        task_data = self.user_tasks[user_id].get(task_id)
        if not task_data:
            logger.error(f"任务 {task_id} 数据不存在")
            return
        
        try:
            # 阶段1: 下载图片
            await self._download_phase(task_data, progress_callback)
            
            # 阶段2: 图像转换
            await self._transform_phase(task_data, progress_callback)
            
            # 任务完成
            await self._complete_task(task_data)
            
        except Exception as e:
            await self._fail_task(task_data, str(e))
    
    async def _download_phase(self, task_data: UserTaskData, progress_callback: Optional[Callable] = None):
        """下载阶段"""
        task_data.status = "downloading"
        task_data.stage = "download"
        task_data.message = "正在下载图片..."
        task_data.started_at = time.time()
        
        await self._push_task_update(task_data)
        
        def download_progress_callback(progress: float):
            task_data.download_progress = progress
            task_data.progress = progress * 0.3  # 下载占总进度的30%
            task_data.message = f"正在下载图片... {progress:.1f}%"
            
            # 异步推送进度
            asyncio.create_task(self._push_task_update(task_data))
        
        try:
            async with self.download_service:
                file_path, file_info = await self.download_service.download_image(
                    task_data.image_url,
                    task_data.expected_filename,
                    download_progress_callback
                )
            
            # 下载完成
            task_data.status = "downloaded"
            task_data.stage = "downloaded"
            task_data.message = "图片下载完成"
            task_data.progress = 30.0
            task_data.download_progress = 100.0
            task_data.input_file_path = file_path
            task_data.input_file_info = file_info
            
            await self._push_task_update(task_data)
            
            logger.info(f"任务 {task_data.task_id} 下载完成: {file_path}")
            
        except Exception as e:
            task_data.status = "download_failed"
            task_data.error_message = str(e)
            await self._push_task_update(task_data)
            raise
    
    async def _transform_phase(self, task_data: UserTaskData, progress_callback: Optional[Callable] = None):
        """转换阶段"""
        task_data.status = "processing"
        task_data.stage = "transform"
        task_data.message = "正在进行风格转换..."
        task_data.progress = 30.0
        
        await self._push_task_update(task_data)
        
        try:
            # 获取风格工作流
            workflow = self.style_registry.workflows[task_data.style_id]
            
            # 设置输入参数
            input_params = {
                "input_image_path": task_data.input_file_path,
                "output_filename": task_data.output_filename
            }
            
            # 执行工作流
            prompt_id = await workflow.execute_async(
                self.comfyui_service,
                input_params,
                lambda progress, message: self._on_transform_progress(task_data, progress, message)
            )
            
            # 记录prompt_id映射
            self.prompt_to_task[prompt_id] = task_data.task_id
            
            # 等待转换完成
            await self._wait_for_transform_completion(task_data, prompt_id)
            
        except Exception as e:
            task_data.status = "processing_failed"
            task_data.error_message = str(e)
            await self._push_task_update(task_data)
            raise
    
    def _on_transform_progress(self, task_data: UserTaskData, progress: float, message: str):
        """转换进度回调"""
        task_data.transform_progress = progress
        task_data.progress = 30.0 + (progress * 0.7)  # 转换占总进度的70%
        task_data.message = message
        
        # 异步推送进度
        asyncio.create_task(self._push_task_update(task_data))
    
    async def _wait_for_transform_completion(self, task_data: UserTaskData, prompt_id: str):
        """等待转换完成"""
        timeout = 300  # 5分钟超时
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 检查任务状态
            if hasattr(task_data, 'result') and task_data.result:
                break
            
            # 检查是否被取消
            if task_data.status == "cancelled":
                raise RPCTransformError(
                    code=ErrorCodes.TASK_CANCELLED,
                    message="任务已被取消",
                    task_id=task_data.task_id
                )
            
            await asyncio.sleep(1)
        
        # 超时检查
        if not hasattr(task_data, 'result') or not task_data.result:
            raise RPCTransformError(
                code=ErrorCodes.TRANSFORM_FAILED,
                message="转换超时",
                task_id=task_data.task_id
            )
    
    async def _complete_task(self, task_data: UserTaskData):
        """完成任务"""
        task_data.status = "completed"
        task_data.stage = "completed"
        task_data.message = "转换完成"
        task_data.progress = 100.0
        task_data.completed_at = time.time()
        
        await self._push_task_update(task_data)
        
        logger.info(f"任务 {task_data.task_id} 完成")
    
    async def _fail_task(self, task_data: UserTaskData, error_message: str):
        """任务失败"""
        if task_data.stage == "download":
            task_data.status = "download_failed"
        else:
            task_data.status = "processing_failed"
        
        task_data.error_message = error_message
        task_data.message = f"任务失败: {error_message}"
        
        await self._push_task_update(task_data)
        
        logger.error(f"任务 {task_data.task_id} 失败: {error_message}")
    
    async def _push_task_update(self, task_data: UserTaskData):
        """推送任务状态更新"""
        if not push_manager:
            return
        
        try:
            update_data = {
                "task_id": task_data.task_id,
                "user_id": task_data.user_id,
                "style_id": task_data.style_id,
                "status": task_data.status,
                "stage": getattr(task_data, 'stage', 'unknown'),
                "progress": task_data.progress,
                "message": getattr(task_data, 'message', ''),
                "timestamp": time.time()
            }
            
            # 添加文件信息
            if hasattr(task_data, 'expected_filename'):
                update_data["files"] = {
                    "input": getattr(task_data, 'expected_filename', ''),
                    "output": getattr(task_data, 'output_filename', '')
                }
            
            # 添加结果信息（如果完成）
            if task_data.status == "completed" and task_data.result:
                update_data["result"] = task_data.result
            
            await push_manager.push_task_update(task_data.task_id, update_data)
            
        except Exception as e:
            logger.warning(f"推送任务更新失败: {e}")
    
    def get_user_task(self, user_id: str, task_id: str) -> Optional[UserTaskData]:
        """获取用户任务"""
        user_tasks = self.user_tasks.get(user_id, {})
        return user_tasks.get(task_id)
    
    def list_user_tasks(self, user_id: str, limit: int = 100) -> List[UserTaskData]:
        """获取用户任务列表"""
        user_tasks = self.user_tasks.get(user_id, {})
        tasks = list(user_tasks.values())
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        
        return tasks[:limit]
    
    async def cancel_task(self, user_id: str, task_id: str) -> bool:
        """取消任务"""
        task_data = self.get_user_task(user_id, task_id)
        if not task_data:
            return False
        
        # 只能取消未完成的任务
        if task_data.status in ["completed", "download_failed", "processing_failed", "cancelled"]:
            return False
        
        task_data.status = "cancelled"
        task_data.message = "任务已取消"
        
        await self._push_task_update(task_data)
        
        logger.info(f"任务 {task_id} 已被用户 {user_id} 取消")
        return True
    
    def on_comfyui_result(self, prompt_id: str, result: Dict[str, Any]):
        """ComfyUI结果回调"""
        task_id = self.prompt_to_task.get(prompt_id)
        if not task_id:
            logger.warning(f"收到未知prompt_id的结果: {prompt_id}")
            return
        
        user_id = self.task_to_user.get(task_id)
        if not user_id:
            logger.warning(f"任务 {task_id} 找不到用户")
            return
        
        task_data = self.get_user_task(user_id, task_id)
        if not task_data:
            logger.warning(f"任务数据不存在: {task_id}")
            return
        
        # 更新任务结果
        task_data.result = result
        
        logger.info(f"任务 {task_id} 收到ComfyUI结果")
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        current_time = time.time()
        cleanup_count = 0
        
        for user_id, user_tasks in self.user_tasks.items():
            tasks_to_remove = []
            
            for task_id, task_data in user_tasks.items():
                task_age = current_time - task_data.created_at
                if task_age > max_age_hours * 3600:
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del user_tasks[task_id]
                if task_id in self.task_to_user:
                    del self.task_to_user[task_id]
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"清理了 {cleanup_count} 个旧任务")