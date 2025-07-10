"""
多用户任务服务

实现用户任务隔离和管理
"""

import uuid
import time
import asyncio
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from ..models.user_models import UserTaskData, UserStatsResponse
# from ..services.comfyui_service import ComfyUIService
from ..core.style_registry import StyleRegistry
from ..workflows.built_in.universal_style_transform import UniversalStyleTransformWorkflow
import logging

if TYPE_CHECKING:
    from ..services.comfyui_service import ComfyUIService

logger = logging.getLogger(__name__)

# 导入推送管理器
try:
    from ..api.v1.websocket_push import push_manager
except ImportError:
    push_manager = None
    logger.warning("WebSocket 推送管理器不可用")

class UserTaskService:
    """多用户任务服务"""
    
    def __init__(self, comfyui_service: 'ComfyUIService', style_registry: StyleRegistry):
        self.comfyui_service = comfyui_service
        self.style_registry = style_registry
        self.user_tasks: Dict[str, Dict[str, UserTaskData]] = {}  # {user_id: {task_id: task_data}}
        self.task_to_user: Dict[str, str] = {}  # {task_id: user_id}
        self.prompt_to_task: Dict[str, str] = {} # {prompt_id: task_id}
    
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
            task_data.prompt_id = prompt_id
            self.prompt_to_task[prompt_id] = task_id
            
            logger.info(f"用户任务处理已提交: {user_id} - {task_id} - prompt_id: {prompt_id}")

            # 移除旧的轮询逻辑 - 现在由ComfyUIService的事件回调驱动
            
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
    
    def handle_progress_update(self, prompt_id: str, progress_data: Dict):
        """处理来自ComfyUIService的进度更新事件"""
        logger.info(f"收到进度更新: prompt_id={prompt_id}, data={progress_data}")
        
        task_id = self.prompt_to_task.get(prompt_id)
        if not task_id:
            logger.warning(f"未找到对应任务: prompt_id={prompt_id}")
            return

        user_id = self.task_to_user.get(task_id)
        if not user_id or user_id not in self.user_tasks or task_id not in self.user_tasks[user_id]:
            logger.warning(f"任务数据异常: task_id={task_id}, user_id={user_id}")
            return
            
        task_data = self.user_tasks[user_id][task_id]
        
        # 检查是否是状态更新而非进度更新
        status = progress_data.get("status")
        if status == "started":
            # 工作流开始执行
            logger.info(f"任务开始执行: task_id={task_id}")
            if push_manager:
                asyncio.create_task(push_manager.push_task_update(task_id, {
                    "status": "running",
                    "progress": 0,
                    "message": "工作流开始执行",
                    "current_step": 0,
                    "total_steps": None
                }))
            return
        elif status in ["executing_node"]:
            # 节点开始执行（仅调试模式下发送）
            node_id = progress_data.get("node")
            if node_id:
                logger.debug(f"节点开始执行: task_id={task_id}, node_id={node_id}")
            return
        
        # 处理真实的进度数据
        value = progress_data.get("value")
        if value is not None:
            # 检查是否包含详细的步骤信息
            current_step = progress_data.get("current_step")
            total_steps = progress_data.get("total_steps")
            node_id = progress_data.get("node")
            
            progress = value  # 已经是百分比
            task_data.progress = progress
            
            logger.info(f"任务进度更新: task_id={task_id}, progress={progress:.1f}%")
            
            if current_step is not None and total_steps is not None:
                logger.info(f"详细进度: {current_step}/{total_steps} (节点: {node_id})")

            # 更新预估剩余时间
            if task_data.started_at and progress > 0:
                elapsed = time.time() - task_data.started_at
                if progress < 100:
                    remaining = (elapsed / progress) * (100 - progress)
                    task_data.estimated_remaining = int(remaining)
                else:
                    task_data.estimated_remaining = 0

            # 构建推送消息
            push_data = {
                "status": "running",
                "progress": progress,
                "estimated_remaining": task_data.estimated_remaining
            }
            
            # 添加详细进度信息（如果可用）
            if current_step is not None and total_steps is not None:
                push_data.update({
                    "current_step": current_step,
                    "total_steps": total_steps,
                    "message": f"处理中... 步骤 {current_step}/{total_steps} ({progress:.1f}%)"
                })
                if node_id:
                    push_data["current_node"] = node_id
            else:
                push_data["message"] = f"处理中... ({progress:.1f}%)"

            # 推送进度更新到外部客户端
            if push_manager:
                logger.info(f"推送进度更新到WebSocket: task_id={task_id}")
                asyncio.create_task(push_manager.push_task_update(task_id, push_data))
            else:
                logger.warning("WebSocket推送管理器不可用")

    async def handle_completion_update(self, prompt_id: str, result_data: Dict):
        """处理来自ComfyUIService的完成/失败事件"""
        task_id = self.prompt_to_task.get(prompt_id)
        if not task_id:
            logger.warning(f"完成事件: 未找到对应任务: prompt_id={prompt_id}")
            return

        user_id = self.task_to_user.get(task_id)
        if not user_id or user_id not in self.user_tasks or task_id not in self.user_tasks[user_id]:
            logger.warning(f"完成事件: 任务数据异常: task_id={task_id}, user_id={user_id}")
            return
            
        task_data = self.user_tasks[user_id][task_id]
        status = result_data.get("status", "completed")

        if status == "completed":
            # 任务完成，需要获取实际结果
            logger.info(f"任务完成，开始获取结果: task_id={task_id}, prompt_id={prompt_id}")
            
            try:
                # 从ComfyUI历史记录中获取结果
                comfyui_result = await self.comfyui_service.get_result(prompt_id)
                logger.info(f"从ComfyUI获取结果: {list(comfyui_result.keys()) if comfyui_result else 'empty'}")
                
                # 处理输出文件
                output_files = []
                if comfyui_result and "outputs" in comfyui_result:
                    for node_id, node_output in comfyui_result["outputs"].items():
                        if "images" in node_output:
                            for img_info in node_output["images"]:
                                filename = img_info.get("filename", "")
                                img_type = img_info.get("type", "output")  # 获取图像类型
                                subfolder = img_info.get("subfolder", "")
                                
                                if filename:
                                    # 构建完整的图像URL，使用正确的type参数
                                    image_url = f"http://127.0.0.1:8188/view?filename={filename}&type={img_type}"
                                    if subfolder:
                                        image_url += f"&subfolder={subfolder}"
                                    
                                    # 优先选择最终输出图像（type=output），而不是临时预览图像
                                    priority = 1 if img_type == "output" else 0
                                    
                                    output_files.append({
                                        "filename": filename,
                                        "url": image_url,
                                        "type": "image",
                                        "img_type": img_type,
                                        "priority": priority,
                                        "node_id": node_id
                                    })
                                    logger.info(f"添加输出文件: {filename} (类型: {img_type}, 节点: {node_id})")
                
                    # 按优先级排序，最终输出图像排在前面
                    output_files.sort(key=lambda x: x["priority"], reverse=True)
                
                # 设置任务结果
                task_result = {
                    "output_files": output_files,
                    "comfyui_result": comfyui_result  # 保留在服务器端用于调试和历史记录
                }
                
                task_data.status = "completed"
                task_data.progress = 100.0
                task_data.result = task_result
                logger.info(f"任务完成: {task_id}, 输出文件数量: {len(output_files)}")
                
                # 推送完成状态到外部客户端 - 只推送必要的数据
                if push_manager:
                    # 构建精简的推送数据，只包含前端需要的信息
                    push_result = {
                        "output_files": output_files,
                        # 可以添加其他前端需要的元数据，但不包含完整的工作流
                        "task_id": task_id,
                        "completed_at": task_data.completed_at if hasattr(task_data, 'completed_at') else time.time()
                    }
                    
                    asyncio.create_task(push_manager.push_task_update(task_id, {
                        "status": "completed",
                        "progress": 100.0,
                        "result": push_result
                    }))
                    
            except Exception as e:
                logger.error(f"获取任务结果失败: {task_id} - {e}", exc_info=True)
                # 将任务标记为失败
                task_data.status = "failed"
                task_data.error_message = f"获取结果失败: {str(e)}"
                
                if push_manager:
                    asyncio.create_task(push_manager.push_task_update(task_id, {
                        "status": "failed",
                        "error_message": task_data.error_message
                    }))
        else: # failed
            task_data.status = "failed"
            task_data.error_message = str(result_data.get("error", "未知错误"))
            logger.error(f"任务失败: {task_id} - {task_data.error_message}")
            
            # 推送失败状态到外部客户端
            if push_manager:
                asyncio.create_task(push_manager.push_task_update(task_id, {
                    "status": "failed",
                    "error_message": task_data.error_message
                }))
        
        task_data.completed_at = time.time()
        
        # 清理映射
        if prompt_id in self.prompt_to_task:
            del self.prompt_to_task[prompt_id]

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