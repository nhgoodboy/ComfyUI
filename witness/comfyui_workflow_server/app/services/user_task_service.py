"""
多用户任务服务

实现用户任务隔离和管理
"""

import uuid
import time
import asyncio
from typing import Dict, List, Optional, Any
from ..models.user_models import UserTaskData, UserStatsResponse
from ..services.comfyui_service import ComfyUIService
from ..core.style_registry import StyleRegistry
from ..workflows.built_in.universal_style_transform import UniversalStyleTransformWorkflow
import logging

logger = logging.getLogger(__name__)

class UserTaskService:
    """多用户任务服务"""
    
    def __init__(self, comfyui_service: ComfyUIService, style_registry: StyleRegistry):
        self.comfyui_service = comfyui_service
        self.style_registry = style_registry
        self.user_tasks: Dict[str, Dict[str, UserTaskData]] = {}  # {user_id: {task_id: task_data}}
        self.task_to_user: Dict[str, str] = {}  # {task_id: user_id}
    
    async def create_task(self, user_id: str, style_id: str, input_image_path: str) -> str:
        """创建用户任务"""
        try:
            # 验证风格ID
            if style_id not in self.style_registry.styles:
                raise ValueError(f"未知的风格ID: {style_id}")
            
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 创建任务数据
            task_data = UserTaskData(
                task_id=task_id,
                user_id=user_id,
                style_id=style_id,
                status="pending",
                progress=0.0,
                created_at=time.time()
            )
            
            # 存储任务
            if user_id not in self.user_tasks:
                self.user_tasks[user_id] = {}
            self.user_tasks[user_id][task_id] = task_data
            self.task_to_user[task_id] = user_id
            
            # 启动任务处理
            asyncio.create_task(self._process_task(task_id, style_id, input_image_path))
            
            logger.info(f"用户任务创建成功: {user_id} - {task_id} - {style_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"创建用户任务失败: {user_id} - {style_id} - {e}")
            raise
    
    async def _process_task(self, task_id: str, style_id: str, input_image_path: str):
        """处理任务"""
        try:
            user_id = self.task_to_user[task_id]
            task_data = self.user_tasks[user_id][task_id]
            
            # 更新任务状态
            task_data.status = "running"
            task_data.started_at = time.time()
            
            # 从注册表获取已创建的工作流处理器实例
            workflow_processor = self.style_registry.get_workflow(style_id)
            if not workflow_processor:
                raise ValueError(f"无法为风格 {style_id} 获取工作流处理器")
            
            # 更新预估时间
            task_data.estimated_remaining = workflow_processor.get_estimated_time({"input_image_path": input_image_path})
            
            # 准备参数
            parameters = {"image_url": input_image_path}
            
            # 验证参数
            validated_params = workflow_processor.validate_parameters(parameters)
            
            # 预处理（下载图片等）
            processed_params = await workflow_processor.pre_process(validated_params)
            
            # 构建工作流
            workflow = await workflow_processor.build_workflow(processed_params)
            
            # 提交工作流到ComfyUI
            prompt_id = await self.comfyui_service.submit_workflow(task_id, workflow)
            
            logger.info(f"用户任务处理已提交: {user_id} - {task_id} - prompt_id: {prompt_id}")

            # 开始轮询任务状态
            while True:
                await asyncio.sleep(1) # 每秒轮询一次
                status_data = self.comfyui_service.get_prompt_status(prompt_id)
                status = status_data.get("status")

                if status == "running":
                    progress_info = status_data.get("progress", {})
                    value = progress_info.get("value", 0)
                    max_value = progress_info.get("max", 1)
                    if max_value > 0:
                        # 计算实际进度百分比
                        progress = (value / max_value) * 100
                        self._update_task_progress(task_id, progress)

                elif status == "completed":
                    result = status_data.get("result", {})
                    task_data.status = "completed"
                    task_data.progress = 100.0
                    task_data.completed_at = time.time()
                    task_data.result = result
                    logger.info(f"任务完成: {task_id}")
                    break
                
                elif status == "failed":
                    error_info = status_data.get("error", "未知错误")
                    task_data.status = "failed"
                    task_data.error_message = str(error_info)
                    task_data.completed_at = time.time()
                    logger.error(f"任务失败: {task_id} - {error_info}")
                    break

                # 超时检查
                if task_data.started_at and time.time() - task_data.started_at > 3600: # 1小时超时
                    task_data.status = "failed"
                    task_data.error_message = "任务超时"
                    logger.error(f"任务超时: {task_id}")
                    break
            
        except Exception as e:
            logger.error(f"处理用户任务失败: {task_id} - {e}", exc_info=True)
            # 更新任务错误状态
            if task_id in self.task_to_user:
                user_id = self.task_to_user[task_id]
                if user_id in self.user_tasks and task_id in self.user_tasks[user_id]:
                    task_data = self.user_tasks[user_id][task_id]
                    task_data.status = "failed"
                    task_data.error_message = str(e)
                    task_data.completed_at = time.time()
    
    def _update_task_progress(self, task_id: str, progress: float):
        """更新任务进度"""
        try:
            if task_id in self.task_to_user:
                user_id = self.task_to_user[task_id]
                if user_id in self.user_tasks and task_id in self.user_tasks[user_id]:
                    task_data = self.user_tasks[user_id][task_id]
                    task_data.progress = progress
                    
                    # 更新预估剩余时间
                    if task_data.started_at and progress > 0:
                        elapsed = time.time() - task_data.started_at
                        if progress < 100:
                            remaining = (elapsed / progress) * (100 - progress)
                            task_data.estimated_remaining = int(remaining)
                        else:
                            task_data.estimated_remaining = 0
        except Exception as e:
            logger.error(f"更新任务进度失败: {task_id} - {e}")
    
    def get_user_task(self, user_id: str, task_id: str) -> Optional[UserTaskData]:
        """获取用户任务"""
        if user_id not in self.user_tasks:
            return None
        return self.user_tasks[user_id].get(task_id)
    
    def list_user_tasks(self, user_id: str, limit: int = 100) -> List[UserTaskData]:
        """列出用户任务"""
        if user_id not in self.user_tasks:
            return []
        
        tasks = list(self.user_tasks[user_id].values())
        # 按创建时间倒序排序
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        return tasks[:limit]
    
    def get_user_stats(self, user_id: str) -> UserStatsResponse:
        """获取用户统计信息"""
        if user_id not in self.user_tasks:
            return UserStatsResponse(
                user_id=user_id,
                task_counts={},
                file_counts={},
                storage_used=0
            )
        
        tasks = self.user_tasks[user_id].values()
        task_counts = {}
        for task in tasks:
            status = task.status
            task_counts[status] = task_counts.get(status, 0) + 1
        
        return UserStatsResponse(
            user_id=user_id,
            task_counts=task_counts,
            file_counts={"total": len(tasks)},
            storage_used=0  # 这里可以添加存储计算逻辑
        )
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理过期任务"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for user_id in list(self.user_tasks.keys()):
                tasks_to_remove = []
                for task_id, task_data in self.user_tasks[user_id].items():
                    if current_time - task_data.created_at > max_age_seconds:
                        tasks_to_remove.append(task_id)
                
                for task_id in tasks_to_remove:
                    del self.user_tasks[user_id][task_id]
                    if task_id in self.task_to_user:
                        del self.task_to_user[task_id]
                
                # 如果用户没有任务了，清理用户记录
                if not self.user_tasks[user_id]:
                    del self.user_tasks[user_id]
            
            logger.info(f"清理过期任务完成，清理时间: {max_age_hours}小时")
            
        except Exception as e:
            logger.error(f"清理过期任务失败: {e}") 