"""
工作流任务服务

通用工作流任务调度和管理服务，支持：
- 任意类型工作流的执行和调度
- 文件下载和预处理
- 任务状态管理和进度跟踪
- WebSocket 实时状态推送
- 多种工作流执行模式（单图、双图、通用工作流）
"""

import uuid
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from pathlib import Path

from ..models.workflow_models import WorkflowTaskData
from ..core.workflow_registry import WorkflowRegistry
from ..services.download_service import DownloadService
from ..utils.file_naming import FileNamingUtils
from ..rpc.exceptions import RPCError, RPCWorkflowError, RPCFileError
from ..rpc.error_codes import ErrorCodes

if TYPE_CHECKING:
    from ..services.comfyui_service import ComfyUIService

logger = logging.getLogger(__name__)

# 导入推送管理器
try:
    from ..utils.websocket_push import push_manager
except ImportError:
    push_manager = None
    logger.warning("WebSocket 推送管理器不可用")


class WorkflowTaskService:
    """工作流任务服务
    
    负责工作流任务的完整生命周期管理：
    - 任务创建和验证
    - 文件下载和预处理
    - 工作流执行调度
    - 进度跟踪和状态更新
    - 结果后处理和存储
    """
    
    def __init__(self, comfyui_service: 'ComfyUIService', workflow_registry: WorkflowRegistry):
        self.comfyui_service = comfyui_service
        self.workflow_registry = workflow_registry
        self.download_service = DownloadService()
        self.file_naming = FileNamingUtils()
        
        # 任务存储：简化为按request_id存储
        self.tasks: Dict[str, WorkflowTaskData] = {}  # {request_id: task_data}
        self.prompt_to_request: Dict[str, str] = {}  # {prompt_id: request_id}
        
        # 任务状态枚举
        self.TASK_STATUSES = {
            "pending": "等待处理",
            "downloading": "下载中",
            "downloaded": "下载完成", 
            "processing": "执行中",
            "completed": "已完成",
            "download_failed": "下载失败",
            "processing_failed": "执行失败",
            "cancelled": "已取消"
        }
    
    async def create_workflow_task(
        self, 
        request_id: str,
        workflow_id: str, 
        params: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        创建通用工作流任务
        
        Args:
            request_id: 请求ID，必须唯一
            workflow_id: 工作流ID
            params: 工作流参数
            progress_callback: 进度回调函数
        
        Returns:
            str: 请求ID (request_id)
        """
        # 验证参数
        request_id = self.file_naming.validate_request_id(request_id)
        
        # 检查request_id是否已存在
        if request_id in self.tasks:
            raise RPCWorkflowError(
                code=ErrorCodes.INVALID_PARAMS,
                message=f"任务ID已存在: {request_id}",
                details="请使用不同的request_id"
            )
        
        # 验证工作流存在
        if not self.workflow_registry.workflow_exists(workflow_id):
            available_workflows = [wf.id for wf in self.workflow_registry.get_all_workflows()]
            raise RPCWorkflowError(
                code=ErrorCodes.WORKFLOW_NOT_FOUND,
                message=f"工作流不存在: {workflow_id}",
                details=f"可用工作流: {available_workflows}"
            )
        
        current_time = time.time()
        
        # 创建任务数据
        task_data = WorkflowTaskData(
            request_id=request_id,
            workflow_id=workflow_id,
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
        task_data.workflow_params = params
        
        # 存储任务
        self.tasks[request_id] = task_data
        
        logger.info(f"创建工作流任务: {request_id}, 工作流: {workflow_id}")
        
        # 推送任务创建消息
        await self._push_task_update(task_data)
        
        # 异步执行任务
        asyncio.create_task(self._execute_workflow_task(request_id, progress_callback))
        
        return request_id

    async def _execute_workflow_task(self, request_id: str, progress_callback: Optional[Callable] = None):
        """执行工作流任务的完整流程"""
        task_data = self.tasks.get(request_id)
        if not task_data:
            logger.error(f"请求 {request_id} 数据不存在")
            return

        # 推送任务开始状态
        task_data.status = "processing"
        task_data.started_at = time.time()
        await self._push_task_update(task_data)

        try:
            # 获取工作流配置
            workflow_config = self.workflow_registry.get_workflow_config(task_data.workflow_id)
            if not workflow_config:
                raise ValueError(f"工作流配置不存在: {task_data.workflow_id}")
            
            from ..workflows.universal_workflow import UniversalWorkflowExecutor
            workflow_executor = UniversalWorkflowExecutor(workflow_config, self.comfyui_service)
            
            # 验证参数
            validated_params = workflow_executor.validate_parameters(task_data.workflow_params)
            
            # 预处理（处理文件下载等）
            processed_params = await workflow_executor.pre_process(validated_params)
            
            # 更新任务数据
            task_data.stage = "workflow_execution"
            task_data.message = "正在执行工作流..."
            task_data.progress = 25.0
            await self._push_task_update(task_data)
            
            # 构建工作流JSON
            workflow_json = await workflow_executor.build_workflow(processed_params)
            
            # 提交到ComfyUI
            prompt_id = await self.comfyui_service.queue_prompt(workflow_json)
            task_data.prompt_id = prompt_id
            
            # 建立映射关系
            self.prompt_to_request[prompt_id] = task_data.request_id
            
            logger.info(f"工作流任务 {request_id} 已提交到ComfyUI: {prompt_id}")
            
            # 更新状态
            task_data.stage = "waiting_completion"
            task_data.message = "工作流执行中..."
            task_data.progress = 50.0
            await self._push_task_update(task_data)
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            await self._fail_task(task_data, str(e))

    def get_task(self, request_id: str) -> Optional[WorkflowTaskData]:
        """获取任务数据"""
        return self.tasks.get(request_id)

    async def cancel_task(self, request_id: str) -> bool:
        """取消任务"""
        task_data = self.tasks.get(request_id)
        if not task_data:
            return False
        
        if task_data.status in ["completed", "processing_failed", "cancelled"]:
            return False
        
        try:
            # 如果有prompt_id，尝试取消ComfyUI任务
            if task_data.prompt_id:
                # ComfyUI没有直接取消API，我们只能标记为取消
                pass
            
            task_data.status = "cancelled"
            task_data.completed_at = time.time()
            task_data.message = "任务已取消"
            
            await self._push_task_update(task_data)
            
            logger.info(f"任务 {request_id} 已取消")
            return True
            
        except Exception as e:
            logger.error(f"取消任务失败: {request_id}, {e}")
            return False

    def on_comfyui_result(self, prompt_id: str, result: Dict[str, Any]):
        """处理ComfyUI结果回调"""
        request_id = self.prompt_to_request.get(prompt_id)
        if not request_id:
            logger.warning(f"未找到prompt_id {prompt_id} 对应的请求")
            return
        
        # 异步处理结果
        asyncio.create_task(self._process_completion_result(request_id, prompt_id, result))

    async def _process_completion_result(self, request_id: str, prompt_id: str, result: Dict[str, Any]):
        """处理完成结果"""
        task_data = self.tasks.get(request_id)
        if not task_data:
            logger.error(f"任务数据不存在: {request_id}")
            return

        try:
            # 获取历史记录信息
            logger.info(f"任务 {task_data.request_id} 获取历史记录信息...")
            history = await self.comfyui_service.get_result(prompt_id)
            logger.info(f"任务 {task_data.request_id} 获取到历史记录: {history}")
            
            # 获取工作流配置进行后处理
            workflow_config = self.workflow_registry.get_workflow_config(task_data.workflow_id)
            if not workflow_config:
                logger.error(f"工作流配置不存在: {task_data.workflow_id}")
                return
                
            # 导入通用工作流执行器
            from ..workflows.universal_workflow import UniversalWorkflowExecutor
            workflow = UniversalWorkflowExecutor(workflow_config, self.comfyui_service)
            
            # 构造工作流结果数据
            workflow_result = {
                'status': 'completed',
                'prompt_id': prompt_id,
                'history': history
            }
            
            # 后处理
            processed_result = await workflow.post_process(workflow_result)
            
            # 完成任务
            await self._complete_task(task_data, processed_result)
            
        except Exception as e:
            logger.error(f"处理完成结果失败: {e}")
            await self._fail_task(task_data, str(e))

    async def _complete_task(self, task_data: WorkflowTaskData, result: Dict[str, Any] = None):
        """完成任务"""
        task_data.status = "completed"
        task_data.completed_at = time.time()
        task_data.progress = 100.0
        task_data.message = "任务完成"
        task_data.result = result
        
        await self._push_task_update(task_data)
        
        logger.info(f"任务 {task_data.request_id} 完成")

    async def _fail_task(self, task_data: WorkflowTaskData, error_message: str):
        """任务失败"""
        task_data.status = "processing_failed"
        task_data.completed_at = time.time()
        task_data.error_message = error_message
        task_data.message = f"任务失败: {error_message}"
        
        await self._push_task_update(task_data)
        
        logger.error(f"任务 {task_data.request_id} 失败: {error_message}")

    async def _push_task_update(self, task_data: WorkflowTaskData):
        """推送任务状态更新"""
        if not push_manager:
            return
        
        try:
            update_data = {
                "request_id": task_data.request_id,
                "workflow_id": task_data.workflow_id,
                "status": task_data.status,
                "stage": getattr(task_data, 'stage', 'unknown'),
                "progress": task_data.progress,
                "message": getattr(task_data, 'message', ''),
                "timestamp": time.time()
            }
            
            # 推送到特定请求ID的连接
            await push_manager.push_to_client(task_data.request_id, {
                "type": "task_update",
                "data": update_data
            })
            
            # 推送到全局服务连接
            await push_manager.push_to_client("web_image_transform_service", {
                "type": "task_update", 
                "data": update_data
            })
            
        except Exception as e:
            logger.warning(f"推送任务更新失败: {e}")

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        to_remove = []
        for request_id, task_data in self.tasks.items():
            if task_data.created_at < cutoff_time:
                if task_data.status in ["completed", "processing_failed", "cancelled"]:
                    to_remove.append(request_id)
        
        for request_id in to_remove:
            task_data = self.tasks.pop(request_id, None)
            if task_data and task_data.prompt_id:
                self.prompt_to_request.pop(task_data.prompt_id, None)
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个旧任务")

    def handle_progress_update(self, prompt_id: str, progress_data: Dict[str, Any]):
        """处理进度更新"""
        request_id = self.prompt_to_request.get(prompt_id)
        if not request_id:
            return
        
        task_data = self.tasks.get(request_id)
        if not task_data:
            return
        
        try:
            # 解析进度数据
            if 'value' in progress_data and 'max' in progress_data:
                progress_percent = (progress_data['value'] / progress_data['max']) * 100
                # 工作流执行阶段占50-90%的进度
                task_data.progress = 50.0 + (progress_percent * 0.4)
                task_data.message = f"工作流执行中... {progress_percent:.1f}%"
                
                # 异步推送更新
                asyncio.create_task(self._push_task_update(task_data))
        except Exception as e:
            logger.warning(f"处理进度更新失败: {e}")

    async def handle_completion_update(self, prompt_id: str, result_data: Dict[str, Any]):
        """处理完成更新"""
        self.on_comfyui_result(prompt_id, result_data)