"""
任务服务

管理异步任务的创建、状态追踪和结果获取
"""

from typing import Dict, Any, Optional
import asyncio
import time
import uuid
import logging
from ..models.api_models import TaskStatus, TaskResult, TaskStatusData, OutputImage
from .style_service import style_service

logger = logging.getLogger(__name__)

class TaskService:
    """任务服务"""
    
    def __init__(self):
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.completed_tasks: Dict[str, Dict[str, Any]] = {}
        self.max_completed_tasks = 1000  # 最大保留的已完成任务数
    
    async def create_task(self, style_id: str, parameters: Dict[str, Any]) -> str:
        """创建新任务"""
        try:
            task_id = str(uuid.uuid4())
            current_time = time.time()
            
            # 获取风格信息
            style_info = await style_service.get_style(style_id)
            estimated_time = style_info.estimated_time if style_info else 60
            
            # 创建任务记录
            task_data = {
                "task_id": task_id,
                "style_id": style_id,
                "status": TaskStatus.PENDING,
                "progress": 0.0,
                "created_at": current_time,
                "started_at": None,
                "completed_at": None,
                "estimated_remaining": estimated_time,
                "parameters": parameters,
                "result": None,
                "error_message": None
            }
            
            self.active_tasks[task_id] = task_data
            
            logger.info(f"创建任务: {task_id}, 风格: {style_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatusData]:
        """获取任务状态"""
        try:
            # 先在活动任务中查找
            task_data = self.active_tasks.get(task_id)
            if not task_data:
                # 在已完成任务中查找
                task_data = self.completed_tasks.get(task_id)
            
            if not task_data:
                return None
            
            return TaskStatusData(
                task_id=task_data["task_id"],
                style_id=task_data["style_id"],
                status=task_data["status"],
                progress=task_data["progress"],
                created_at=task_data["created_at"],
                started_at=task_data.get("started_at"),
                completed_at=task_data.get("completed_at"),
                estimated_remaining=task_data.get("estimated_remaining"),
                error_message=task_data.get("error_message")
            )
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None
    
    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        try:
            # 先在活动任务中查找
            task_data = self.active_tasks.get(task_id)
            if not task_data:
                # 在已完成任务中查找
                task_data = self.completed_tasks.get(task_id)
            
            if not task_data or task_data["status"] != TaskStatus.COMPLETED:
                return None
            
            result_data = task_data.get("result", {})
            if not result_data:
                return None
            
            # 构造输出图片列表
            output_images = []
            for img_data in result_data.get("output_images", []):
                output_images.append(OutputImage(
                    filename=img_data.get("filename", ""),
                    url=img_data.get("url", ""),
                    size=img_data.get("size", 0)
                ))
            
            return TaskResult(
                output_images=output_images,
                duration=task_data.get("duration", 0.0),
                style_applied=task_data["style_id"]
            )
            
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return None
    
    async def update_task_progress(self, task_id: str, progress: float, status: TaskStatus = None):
        """更新任务进度"""
        try:
            if task_id not in self.active_tasks:
                logger.warning(f"任务不存在: {task_id}")
                return
            
            task_data = self.active_tasks[task_id]
            task_data["progress"] = progress
            
            if status:
                task_data["status"] = status
                
                # 更新时间戳
                current_time = time.time()
                if status == TaskStatus.PROCESSING and not task_data.get("started_at"):
                    task_data["started_at"] = current_time
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    task_data["completed_at"] = current_time
                    if task_data.get("started_at"):
                        task_data["duration"] = current_time - task_data["started_at"]
                
                # 计算剩余时间
                if status == TaskStatus.PROCESSING and progress > 0:
                    elapsed = current_time - task_data.get("started_at", current_time)
                    if elapsed > 0:
                        total_estimated = elapsed / (progress / 100)
                        task_data["estimated_remaining"] = max(0, total_estimated - elapsed)
            
            logger.debug(f"更新任务 {task_id} 进度: {progress}%, 状态: {status}")
            
        except Exception as e:
            logger.error(f"更新任务进度失败: {e}")
    
    async def complete_task(self, task_id: str, result: Dict[str, Any]):
        """完成任务"""
        try:
            if task_id not in self.active_tasks:
                logger.warning(f"任务不存在: {task_id}")
                return
            
            task_data = self.active_tasks[task_id]
            task_data["result"] = result
            task_data["status"] = TaskStatus.COMPLETED
            task_data["progress"] = 100.0
            task_data["completed_at"] = time.time()
            
            if task_data.get("started_at"):
                task_data["duration"] = task_data["completed_at"] - task_data["started_at"]
            
            # 移动到已完成任务
            self.completed_tasks[task_id] = task_data
            del self.active_tasks[task_id]
            
            # 清理过多的已完成任务
            await self._cleanup_completed_tasks()
            
            logger.info(f"任务完成: {task_id}")
            
        except Exception as e:
            logger.error(f"完成任务失败: {e}")
    
    async def fail_task(self, task_id: str, error_message: str):
        """标记任务失败"""
        try:
            if task_id not in self.active_tasks:
                logger.warning(f"任务不存在: {task_id}")
                return
            
            task_data = self.active_tasks[task_id]
            task_data["status"] = TaskStatus.FAILED
            task_data["error_message"] = error_message
            task_data["completed_at"] = time.time()
            
            if task_data.get("started_at"):
                task_data["duration"] = task_data["completed_at"] - task_data["started_at"]
            
            # 移动到已完成任务
            self.completed_tasks[task_id] = task_data
            del self.active_tasks[task_id]
            
            logger.error(f"任务失败: {task_id}, 错误: {error_message}")
            
        except Exception as e:
            logger.error(f"标记任务失败时出错: {e}")
    
    async def _cleanup_completed_tasks(self):
        """清理过多的已完成任务"""
        try:
            if len(self.completed_tasks) > self.max_completed_tasks:
                # 按完成时间排序，删除最旧的任务
                sorted_tasks = sorted(
                    self.completed_tasks.items(),
                    key=lambda x: x[1].get("completed_at", 0)
                )
                
                # 删除超出限制的任务
                excess_count = len(self.completed_tasks) - self.max_completed_tasks
                for task_id, _ in sorted_tasks[:excess_count]:
                    del self.completed_tasks[task_id]
                
                logger.info(f"清理了 {excess_count} 个已完成任务")
                
        except Exception as e:
            logger.error(f"清理已完成任务失败: {e}")
    
    async def get_task_count(self) -> Dict[str, int]:
        """获取任务统计"""
        try:
            return {
                "active": len(self.active_tasks),
                "completed": len(self.completed_tasks),
                "total": len(self.active_tasks) + len(self.completed_tasks)
            }
        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {"active": 0, "completed": 0, "total": 0}
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            if task_id not in self.active_tasks:
                return False
            
            task_data = self.active_tasks[task_id]
            if task_data["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return False
            
            task_data["status"] = TaskStatus.FAILED
            task_data["error_message"] = "任务被取消"
            task_data["completed_at"] = time.time()
            
            # 移动到已完成任务
            self.completed_tasks[task_id] = task_data
            del self.active_tasks[task_id]
            
            logger.info(f"任务已取消: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False

# 创建全局任务服务实例
task_service = TaskService() 