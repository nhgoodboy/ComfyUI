"""
工作流管理器

负责工作流的执行、任务管理和结果处理。
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
import asyncio
import uuid
import logging
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from .workflow_registry import workflow_registry
from ..services.comfyui_service import ComfyUIService
from ..utils.monitoring import performance_monitor

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    VALIDATING = "validating"
    PREPROCESSING = "preprocessing"
    RUNNING = "running"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WorkflowTask:
    """工作流任务"""
    id: str
    workflow_id: str
    parameters: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    comfyui_prompt_id: Optional[str] = None
    progress: float = 0.0
    estimated_time: Optional[int] = None
    
    @property
    def duration(self) -> Optional[float]:
        """任务执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_finished(self) -> bool:
        """任务是否已完成"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]

class WorkflowManager:
    """工作流管理器
    
    负责工作流的执行、任务管理和结果处理。
    """
    
    def __init__(self, comfyui_service: ComfyUIService):
        self.comfyui_service = comfyui_service
        self.tasks: Dict[str, WorkflowTask] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._max_concurrent_tasks = 5  # 最大并发任务数
    
    async def execute_workflow(self, workflow_id: str, parameters: Dict[str, Any]) -> str:
        """执行工作流
        
        Args:
            workflow_id: 工作流ID
            parameters: 工作流参数
            
        Returns:
            str: 任务ID
            
        Raises:
            ValueError: 工作流不存在或参数无效
        """
        # 检查工作流是否存在
        workflow = workflow_registry.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        # 创建任务
        task_id = str(uuid.uuid4())
        task = WorkflowTask(
            id=task_id,
            workflow_id=workflow_id,
            parameters=parameters,
            estimated_time=workflow.get_estimated_time(parameters)
        )
        
        self.tasks[task_id] = task
        
        # 异步执行任务
        asyncio_task = asyncio.create_task(self._execute_task(task))
        self._running_tasks[task_id] = asyncio_task
        
        logger.info(f"创建工作流任务: {task_id} (工作流: {workflow_id})")
        return task_id
    
    async def _execute_task(self, task: WorkflowTask) -> None:
        """执行任务
        
        Args:
            task: 工作流任务
        """
        try:
            # 更新任务状态
            task.status = TaskStatus.VALIDATING
            task.started_at = datetime.now()
            
            # 获取工作流实例
            workflow = workflow_registry.get_workflow(task.workflow_id)
            if not workflow:
                raise ValueError(f"工作流不存在: {task.workflow_id}")
            
            # 记录性能开始
            performance_monitor.start_request(task.id)
            
            # 1. 验证参数
            logger.info(f"验证参数: {task.id}")
            validated_params = workflow.validate_parameters(task.parameters)
            task.parameters = validated_params
            task.progress = 0.1
            
            # 2. 预处理
            task.status = TaskStatus.PREPROCESSING
            logger.info(f"预处理: {task.id}")
            preprocessed_params = await workflow.pre_process(validated_params)
            task.progress = 0.2
            
            # 3. 构建工作流
            logger.info(f"构建工作流: {task.id}")
            workflow_json = await workflow.build_workflow(preprocessed_params)
            task.progress = 0.3
            
            # 4. 执行工作流
            task.status = TaskStatus.RUNNING
            logger.info(f"执行工作流: {task.id}")
            
            # 提交到ComfyUI
            prompt_id = await self.comfyui_service.queue_prompt(workflow_json)
            task.comfyui_prompt_id = prompt_id
            
            # 等待执行完成
            async for progress in self._monitor_comfyui_progress(prompt_id):
                task.progress = 0.3 + (progress * 0.6)  # 30%-90%
            
            # 获取结果
            result = await self.comfyui_service.get_result(prompt_id)
            task.progress = 0.9
            
            # 5. 后处理
            task.status = TaskStatus.POSTPROCESSING
            logger.info(f"后处理: {task.id}")
            final_result = await workflow.post_process(result)
            task.progress = 1.0
            
            # 6. 完成任务
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = final_result
            
            # 记录性能结束
            performance_monitor.end_request(task.id, success=True)
            
            logger.info(f"任务完成: {task.id} (耗时: {task.duration:.2f}s)")
            
        except Exception as e:
            # 处理错误
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error_message = str(e)
            
            # 记录性能结束
            performance_monitor.end_request(task.id, success=False)
            
            logger.error(f"任务失败: {task.id}, 错误: {e}")
            
        finally:
            # 清理运行中的任务
            if task.id in self._running_tasks:
                del self._running_tasks[task.id]
    
    async def _monitor_comfyui_progress(self, prompt_id: str) -> AsyncGenerator[float, None]:
        """监控ComfyUI执行进度
        
        Args:
            prompt_id: ComfyUI提示ID
            
        Yields:
            float: 进度值(0-1)
        """
        try:
            while True:
                # 检查任务状态
                status = await self.comfyui_service.get_prompt_status(prompt_id)
                
                if status == "completed":
                    yield 1.0
                    break
                elif status == "failed":
                    raise Exception(f"ComfyUI任务失败: {prompt_id}")
                elif status == "running":
                    # 这里可以根据ComfyUI的进度API获取更详细的进度
                    # 目前简单返回0.5表示正在执行
                    yield 0.5
                
                await asyncio.sleep(1)  # 每秒检查一次
                
        except Exception as e:
            logger.error(f"监控ComfyUI进度失败: {prompt_id}, 错误: {e}")
            raise
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.is_finished:
            return False
        
        # 取消asyncio任务
        if task_id in self._running_tasks:
            asyncio_task = self._running_tasks[task_id]
            asyncio_task.cancel()
        
        # 如果有ComfyUI任务，也要取消
        if task.comfyui_prompt_id:
            await self.comfyui_service.cancel_prompt(task.comfyui_prompt_id)
        
        # 更新任务状态
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        logger.info(f"任务已取消: {task_id}")
        return True
    
    def get_task(self, task_id: str) -> Optional[WorkflowTask]:
        """获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[WorkflowTask]: 任务信息
        """
        return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务状态信息
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "workflow_id": task.workflow_id,
            "status": task.status.value,
            "progress": task.progress,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration": task.duration,
            "estimated_time": task.estimated_time,
            "error_message": task.error_message
        }
    
    def list_tasks(self, status: Optional[TaskStatus] = None, 
                   workflow_id: Optional[str] = None, 
                   limit: int = 100) -> List[Dict[str, Any]]:
        """列出任务
        
        Args:
            status: 可选的状态过滤
            workflow_id: 可选的工作流ID过滤
            limit: 返回数量限制
            
        Returns:
            List[Dict[str, Any]]: 任务列表
        """
        tasks = list(self.tasks.values())
        
        # 过滤
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if workflow_id:
            tasks = [t for t in tasks if t.workflow_id == workflow_id]
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        # 限制数量
        tasks = tasks[:limit]
        
        # 转换为字典
        return [self.get_task_status(t.id) for t in tasks]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        tasks = list(self.tasks.values())
        
        # 按状态统计
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(1 for t in tasks if t.status == status)
        
        # 按工作流统计
        workflow_counts = {}
        for task in tasks:
            workflow_id = task.workflow_id
            if workflow_id not in workflow_counts:
                workflow_counts[workflow_id] = 0
            workflow_counts[workflow_id] += 1
        
        # 计算平均执行时间
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED and t.duration]
        avg_duration = sum(t.duration for t in completed_tasks) / len(completed_tasks) if completed_tasks else 0
        
        return {
            "total_tasks": len(tasks),
            "running_tasks": len(self._running_tasks),
            "status_counts": status_counts,
            "workflow_counts": workflow_counts,
            "average_duration": avg_duration,
            "max_concurrent_tasks": self._max_concurrent_tasks
        }
    
    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """清理旧任务
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            int: 清理的任务数量
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if task.created_at < cutoff_time and task.is_finished:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        
        logger.info(f"清理了 {len(tasks_to_remove)} 个旧任务")
        return len(tasks_to_remove)

# 全局工作流管理器实例（需要在应用启动时初始化）
_workflow_manager: Optional[WorkflowManager] = None

def set_workflow_manager(manager: WorkflowManager) -> None:
    """设置工作流管理器实例
    
    Args:
        manager: 工作流管理器实例
    """
    global _workflow_manager
    _workflow_manager = manager

def get_workflow_manager() -> WorkflowManager:
    """获取工作流管理器实例
    
    Returns:
        WorkflowManager: 工作流管理器实例
        
    Raises:
        RuntimeError: 如果工作流管理器未初始化
    """
    if _workflow_manager is None:
        raise RuntimeError("工作流管理器未初始化")
    return _workflow_manager 