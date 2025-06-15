import asyncio
import time
import uuid
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
from ..schemas.response import TaskStatus
import logging

logger = logging.getLogger(__name__)

@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    user_id: str
    status: TaskStatus
    created_at: datetime
    comfyui_prompt_id: Optional[str] = None
    sampler_node_ids: Optional[list[str]] = None
    output_image_url: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0

class TaskManager:
    """内存任务管理器"""
    
    def __init__(self):
        self._tasks: Dict[str, TaskInfo] = {}
        self._user_tasks: Dict[str, set] = {}  # user_id -> set of task_ids
        self._lock = asyncio.Lock()
        
    async def create_task(self, user_id: str) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        
        async with self._lock:
            task_info = TaskInfo(
                task_id=task_id,
                user_id=user_id,
                status=TaskStatus.PENDING,
                created_at=datetime.now()
            )
            
            self._tasks[task_id] = task_info
            
            if user_id not in self._user_tasks:
                self._user_tasks[user_id] = set()
            self._user_tasks[user_id].add(task_id)
            
        logger.info(f"创建任务 {task_id} for 用户 {user_id}")
        return task_id
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                               comfyui_prompt_id: Optional[str] = None,
                               sampler_node_ids: Optional[list[str]] = None,
                               output_image_url: Optional[str] = None,
                               error_message: Optional[str] = None,
                               progress: Optional[float] = None):
        """更新任务状态"""
        async with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务 {task_id} 不存在")
                return
            
            task = self._tasks[task_id]
            task.status = status
            
            if comfyui_prompt_id:
                task.comfyui_prompt_id = comfyui_prompt_id
            if sampler_node_ids is not None:
                task.sampler_node_ids = sampler_node_ids
            if output_image_url:
                task.output_image_url = output_image_url
            if error_message:
                task.error_message = error_message
            if progress is not None:
                task.progress = progress
                
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.now()
                
        logger.info(f"更新任务 {task_id} 状态为 {status}")
    
    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        async with self._lock:
            return self._tasks.get(task_id)
    
    async def get_user_tasks(self, user_id: str, limit: int = 50) -> list[TaskInfo]:
        """获取用户的任务列表"""
        async with self._lock:
            if user_id not in self._user_tasks:
                return []
            
            task_ids = list(self._user_tasks[user_id])
            tasks = [self._tasks[tid] for tid in task_ids if tid in self._tasks]
            
            # 按创建时间倒序排列
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            return tasks[:limit]
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        current_time = datetime.now()
        cutoff_time = current_time.timestamp() - (max_age_hours * 3600)
        
        async with self._lock:
            tasks_to_remove = []
            
            for task_id, task in self._tasks.items():
                if task.created_at.timestamp() < cutoff_time:
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                task = self._tasks[task_id]
                user_id = task.user_id
                
                # 从任务字典中删除
                del self._tasks[task_id]
                
                # 从用户任务集合中删除
                if user_id in self._user_tasks:
                    self._user_tasks[user_id].discard(task_id)
                    if not self._user_tasks[user_id]:
                        del self._user_tasks[user_id]
            
            if tasks_to_remove:
                logger.info(f"清理了 {len(tasks_to_remove)} 个旧任务")
    
    async def get_stats(self) -> dict:
        """获取统计信息"""
        async with self._lock:
            total_tasks = len(self._tasks)
            status_counts = {}
            
            for task in self._tasks.values():
                status = task.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_tasks": total_tasks,
                "total_users": len(self._user_tasks),
                "status_counts": status_counts
            }

# 全局任务管理器实例
task_manager = TaskManager()

async def start_cleanup_task():
    """启动定期清理任务"""
    while True:
        try:
            await task_manager.cleanup_old_tasks()
            await asyncio.sleep(3600)  # 每小时清理一次
        except Exception as e:
            logger.error(f"清理任务失败: {e}")
            await asyncio.sleep(300)  # 出错后5分钟重试 