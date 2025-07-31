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
    from ..utils.websocket_push import push_manager
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
        
        # 任务存储：简化为按request_id存储
        self.tasks: Dict[str, UserTaskData] = {}  # {request_id: task_data}
        self.prompt_to_request: Dict[str, str] = {}  # {prompt_id: request_id}
        
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
        request_id: str,
        style_id: str, 
        image_url: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        创建转换任务（下载 + 转换）
        
        Args:
            request_id: 请求ID，必须唯一
            style_id: 风格ID
            image_url: 图片URL
            progress_callback: 进度回调函数
        
        Returns:
            str: 请求ID (request_id)
        """
        # 验证参数
        request_id = self.file_naming.validate_request_id(request_id)
        style_id = self.file_naming.validate_style_id(style_id)
        
        # 检查request_id是否已存在
        if request_id in self.tasks:
            raise RPCTransformError(
                code=ErrorCodes.INVALID_PARAMS,
                message=f"任务ID已存在: {request_id}",
                details="请使用不同的request_id"
            )
        
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
        
        current_time = time.time()
        
        # 创建任务数据
        task_data = UserTaskData(
            request_id=request_id,
            user_id="",  # 不再使用用户ID
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
        task_data.download_progress = 0.0
        task_data.transform_progress = 0.0
        
        # 存储任务
        self.tasks[request_id] = task_data
        
        logger.info(f"创建转换任务: {request_id}, 风格: {style_id}")
        
        # 推送任务创建消息
        await self._push_task_update(task_data)
        
        # 异步执行任务
        asyncio.create_task(self._execute_transform_task(request_id, progress_callback))
        
        return request_id
    
    async def _execute_transform_task(self, request_id: str, progress_callback: Optional[Callable] = None):
        """执行转换任务的完整流程"""
        task_data = self.tasks.get(request_id)
        if not task_data:
            logger.error(f"请求 {request_id} 数据不存在")
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
            
            logger.info(f"请求 {task_data.request_id} 下载完成: {file_path}")
            
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
        # 重置进度为0，只显示转换的实际进度
        task_data.progress = 0.0
        
        # 推送转换开始状态（进度为0）
        await self._push_task_update(task_data)
        
        try:
            # 获取风格工作流
            workflow = self.style_registry.workflows[task_data.style_id]
            
            # 设置输入参数
            input_params = {
                "input_image_path": task_data.input_file_path,
                "output_filename": task_data.output_filename
            }
            
            # 设置期望的输出文件名到工作流实例
            workflow.expected_output_filename = task_data.output_filename
            
            # 执行工作流
            prompt_id = await workflow.execute_async(
                self.comfyui_service,
                input_params,
                lambda progress, message: self._on_transform_progress(task_data, progress, message)
            )
            
            # 记录prompt_id映射
            self.prompt_to_request[prompt_id] = task_data.request_id
            
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
        # 直接使用ComfyUI的实际进度，不再添加30%的基础偏移
        task_data.progress = progress
        task_data.message = message
        
        # 异步推送进度
        asyncio.create_task(self._push_task_update(task_data))
    
    async def _wait_for_transform_completion(self, task_data: UserTaskData, prompt_id: str):
        """等待转换完成"""
        timeout = 300  # 5分钟超时
        start_time = time.time()
        last_progress_update = start_time
        

        
        while time.time() - start_time < timeout:
            # 检查任务状态
            if hasattr(task_data, 'result') and task_data.result:
                break
            
            # 检查是否被取消
            if task_data.status == "cancelled":
                raise RPCTransformError(
                    code=ErrorCodes.TASK_CANCELLED,
                    message="任务已被取消",
                    request_id=task_data.request_id
                )
            
            # 检查是否收到ComfyUI的进度更新
            current_time = time.time()
            if current_time - last_progress_update > 10:
                # 超过10秒没有进度更新，记录调试信息但不强制模拟进度
                logger.debug(f"请求 {task_data.request_id} 超过10秒没有收到进度更新")
                last_progress_update = current_time
            
            await asyncio.sleep(1)
        
        # 超时检查
        if not hasattr(task_data, 'result') or not task_data.result:
            raise RPCTransformError(
                code=ErrorCodes.TRANSFORM_FAILED,
                message="转换超时",
                request_id=task_data.request_id
            )
    
    async def _complete_task(self, task_data: UserTaskData):
        """完成任务"""
        task_data.status = "completed"
        task_data.stage = "completed"
        task_data.message = "转换完成"
        task_data.progress = 100.0
        task_data.completed_at = time.time()
        
        await self._push_task_update(task_data)
        
        logger.info(f"请求 {task_data.request_id} 完成")
    
    async def _fail_task(self, task_data: UserTaskData, error_message: str):
        """任务失败"""
        if task_data.stage == "download":
            task_data.status = "download_failed"
        else:
            task_data.status = "processing_failed"
        
        task_data.error_message = error_message
        task_data.message = f"任务失败: {error_message}"
        
        await self._push_task_update(task_data)
        
        logger.error(f"请求 {task_data.request_id} 失败: {error_message}")
    
    async def _push_task_update(self, task_data: UserTaskData):
        """推送任务状态更新"""
        if not push_manager:
            return
        
        try:
            update_data = {
                "request_id": task_data.request_id,
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
            
            await push_manager.push_task_update(task_data.request_id, update_data)
            
        except Exception as e:
            logger.warning(f"推送任务更新失败: {e}")
    
    def get_task(self, request_id: str) -> Optional[UserTaskData]:
        """获取任务"""
        return self.tasks.get(request_id)
    
    async def cancel_task(self, request_id: str) -> bool:
        """取消任务"""
        task_data = self.get_task(request_id)
        if not task_data:
            return False
        
        # 只能取消未完成的任务
        if task_data.status in ["completed", "download_failed", "processing_failed", "cancelled"]:
            return False
        
        task_data.status = "cancelled"
        task_data.message = "任务已取消"
        
        await self._push_task_update(task_data)
        
        logger.info(f"请求 {request_id} 已取消")
        return True
    
    def on_comfyui_result(self, prompt_id: str, result: Dict[str, Any]):
        """ComfyUI结果回调"""
        request_id = self.prompt_to_request.get(prompt_id)
        if not request_id:
            logger.warning(f"收到未知prompt_id的结果: {prompt_id}")
            return
        
        task_data = self.get_task(request_id)
        if not task_data:
            logger.warning(f"任务数据不存在: {request_id}")
            return
        
        # 更新任务结果 - 先记录原始结果用于调试
        logger.info(f"任务 {request_id} 收到ComfyUI原始结果: {result}")
        
        # 异步获取完整的历史记录信息
        asyncio.create_task(self._process_completion_result(task_data, prompt_id, result))
    
    async def _process_completion_result(self, task_data: 'UserTaskData', prompt_id: str, result: Dict[str, Any]):
        """处理完成结果，获取完整的历史记录信息"""
        try:
            # 获取完整的历史记录
            logger.info(f"任务 {task_data.request_id} 获取历史记录信息...")
            history = await self.comfyui_service.get_result(prompt_id)
            logger.info(f"任务 {task_data.request_id} 获取到历史记录: {history}")
            
            # 获取工作流实例进行后处理
            workflow = self.style_registry.workflows[task_data.style_id]
            
            # 构造工作流结果数据
            workflow_result = {
                'status': 'completed',
                'prompt_id': prompt_id,
                'timestamp': result.get('timestamp'),
                'history': history
            }
            
            # 调用工作流的后处理方法（下载图片并保存到本地）
            logger.info(f"任务 {task_data.request_id} 开始后处理...")
            processed_result = await workflow.post_process(workflow_result)
            logger.info(f"任务 {task_data.request_id} 后处理完成: {processed_result}")
            
            # 更新任务状态
            task_data.status = "completed"
            task_data.stage = "completed" 
            task_data.progress = 100.0
            task_data.message = "转换完成"
            
            # 使用后处理的结果
            task_data.result = processed_result
            
            # 统计输出文件数量
            output_count = 0
            if processed_result and 'output_images' in processed_result:
                output_count = len(processed_result['output_images'])
            
            logger.info(f"任务 {task_data.request_id} 完成，生成了 {output_count} 个文件")
            
            # 推送任务完成更新
            await self._push_task_update(task_data)
            
        except Exception as e:
            logger.error(f"处理任务 {task_data.request_id} 完成结果失败: {e}", exc_info=True)
            # 即使获取历史记录失败，也要标记任务为完成
            task_data.status = "completed"
            task_data.stage = "completed"
            task_data.progress = 100.0
            task_data.message = "转换完成（结果获取失败）"
            task_data.result = result
            await self._push_task_update(task_data)
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        current_time = time.time()
        cleanup_count = 0
        
        tasks_to_remove = []
        
        for request_id, task_data in self.tasks.items():
            task_age = current_time - task_data.created_at
            if task_age > max_age_hours * 3600:
                tasks_to_remove.append(request_id)
        
        for request_id in tasks_to_remove:
            del self.tasks[request_id]
            # 清理prompt映射
            prompt_ids_to_remove = [pid for pid, rid in self.prompt_to_request.items() if rid == request_id]
            for prompt_id in prompt_ids_to_remove:
                del self.prompt_to_request[prompt_id]
            cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"清理了 {cleanup_count} 个旧任务")
    
    def handle_progress_update(self, prompt_id: str, progress_data: Dict[str, Any]):
        """处理ComfyUI进度更新"""
        logger.info(f"收到进度更新: prompt_id={prompt_id}, data={progress_data}")
        
        request_id = self.prompt_to_request.get(prompt_id)
        if not request_id:
            logger.warning(f"收到未知prompt_id的进度更新: {prompt_id}")
            return
        
        task_data = self.get_task(request_id)
        if not task_data:
            logger.warning(f"任务数据不存在: {request_id}")
            return
        
        # 更新任务进度
        if 'value' in progress_data:
            # WebSocket客户端已经处理了进度计算，value是0-100的百分比
            node_progress = progress_data['value']
            current_step = progress_data.get('current_step', 0)
            total_steps = progress_data.get('total_steps', 1)
            node_id = progress_data.get('node', 'unknown')
            
            # 只显示主要生成节点的进度（通常是多步骤的采样节点）
            # 过滤掉单步骤的预处理节点
            if total_steps > 1:  # 只有多步骤节点才更新进度
                task_data.progress = node_progress  # 直接使用0-100%的真实进度
                task_data.stage = "transform"
            else:
                # 单步骤节点不更新进度，避免进度跳跃
                logger.debug(f"跳过单步骤节点 {node_id} 的进度更新: {node_progress}%")
                return
            
            # 根据是否有详细步数信息来设置消息
            if 'current_step' in progress_data and 'total_steps' in progress_data:
                task_data.message = f"生成进度: {current_step}/{total_steps} ({task_data.progress:.1f}%) - 节点: {node_id}"
            else:
                task_data.message = f"生成进度: {task_data.progress:.1f}% - 节点: {node_id}"
                
            logger.info(f"任务 {request_id} ComfyUI进度更新: 节点{node_progress:.1f}% -> 总体{task_data.progress:.1f}% (步骤: {current_step}/{total_steps})")
            
            # 推送进度更新
            asyncio.create_task(self._push_task_update(task_data))
        elif 'status' in progress_data:
            # 处理状态更新 (如开始、执行等)
            status = progress_data['status']
            
            if status == "started":
                # 任务开始执行，设置进度为30% (下载完成，开始转换)
                task_data.progress = 30.0
                task_data.stage = "transform"
                task_data.message = "开始图像转换..."
                logger.info(f"任务 {request_id} 开始转换")
                asyncio.create_task(self._push_task_update(task_data))
                
            elif status == "executing_node":
                # 节点开始执行
                node_id = progress_data.get('node', 'unknown')
                task_data.stage = "transform"
                task_data.message = f"正在执行节点: {node_id}"
                logger.info(f"任务 {request_id} 执行节点: {node_id}")
                asyncio.create_task(self._push_task_update(task_data))
                
            else:
                # 其他状态更新
                task_data.stage = "transform"
                task_data.message = f"状态: {status}"
                logger.info(f"任务 {request_id} 状态更新: {status}")
                asyncio.create_task(self._push_task_update(task_data))
        else:
            # 没有可处理的进度或状态信息
            logger.debug(f"任务 {request_id} 收到无法处理的进度数据: {progress_data}")
    
    async def handle_completion_update(self, prompt_id: str, result_data: Dict[str, Any]):
        """处理ComfyUI完成事件"""
        # 这个方法与on_comfyui_result类似，我们可以直接调用它
        self.on_comfyui_result(prompt_id, result_data)
    
    async def create_dual_image_transform_task(
        self, 
        request_id: str,
        style_id: str, 
        image1_url: str,
        image2_url: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        创建双图片转换任务（下载 + 转换）
        
        Args:
            request_id: 请求ID，必须唯一
            style_id: 风格ID
            image1_url: 第一张图片URL
            image2_url: 第二张图片URL
            progress_callback: 进度回调函数
        
        Returns:
            str: 请求ID (request_id)
        """
        # 验证参数
        request_id = self.file_naming.validate_request_id(request_id)
        style_id = self.file_naming.validate_style_id(style_id)
        
        # 检查request_id是否已存在
        if request_id in self.tasks:
            raise RPCTransformError(
                code=ErrorCodes.INVALID_PARAMS,
                message=f"任务ID已存在: {request_id}",
                details="请使用不同的request_id"
            )
        
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
                code=ErrorCodes.WORKFLOW_NOT_FOUND,
                message=f"工作流文件不存在: {style_id}",
                details=f"可用工作流: {list(self.style_registry.workflows.keys())}"
            )
        
        # 验证风格是否支持双图片
        style_config = self.style_registry.styles[style_id]
        if not getattr(style_config, 'requires_dual_images', False):
            raise RPCTransformError(
                code=ErrorCodes.INVALID_PARAMS,
                message=f"风格 {style_id} 不支持双图片输入",
                details="请使用支持双图片的风格，如 person_scene_merge"
            )
        
        logger.info(f"开始双图片转换任务: request_id={request_id}, style_id={style_id}")
        
        # 创建任务数据
        task_data = UserTaskData(
            request_id=request_id,
            user_id="",  # 不再使用用户ID
            style_id=style_id,
            status="pending",
            stage="pending",
            progress=0.0,
            message="任务初始化",
            created_at=time.time()
        )
        
        # 存储任务数据
        self.tasks[request_id] = task_data
        
        # 推送初始状态
        await self._push_task_update(task_data)
        
        # 异步执行转换任务
        asyncio.create_task(self._execute_dual_image_transform_task(
            task_data, image1_url, image2_url, progress_callback
        ))
        
        return request_id
    
    async def _execute_dual_image_transform_task(
        self, 
        task_data: UserTaskData, 
        image1_url: str,
        image2_url: str,
        progress_callback: Optional[Callable] = None
    ):
        """执行双图片转换任务"""
        try:
            logger.info(f"开始执行双图片转换任务: {task_data.request_id}")
            
            # 阶段1: 下载第一张图片
            task_data.status = "downloading"
            task_data.stage = "download"
            task_data.progress = 5.0
            task_data.message = "正在下载第一张图片..."
            await self._push_task_update(task_data)
            
            # 下载第一张图片
            image1_path, image1_info = await self.download_service.download_image(
                image1_url, 
                f"image1_{task_data.request_id.replace('-', '')[:8]}.jpg"
            )
            
            # 阶段2: 下载第二张图片
            task_data.progress = 15.0
            task_data.message = "正在下载第二张图片..."
            await self._push_task_update(task_data)
            
            # 下载第二张图片
            image2_path, image2_info = await self.download_service.download_image(
                image2_url,
                f"image2_{task_data.request_id.replace('-', '')[:8]}.jpg"
            )
            
            # 阶段3: 准备转换
            task_data.status = "downloaded"
            task_data.stage = "prepare"
            task_data.progress = 25.0
            task_data.message = "双图片下载完成，准备转换..."
            await self._push_task_update(task_data)
            
            # 获取工作流
            workflow = self.style_registry.workflows[task_data.style_id]
            
            # 准备工作流参数
            workflow_params = {
                'image1_path': image1_path,
                'image2_path': image2_path,
                'output_filename': f"{task_data.request_id}_output.png"
            }
            
            # 阶段4: 开始转换
            task_data.status = "processing"
            task_data.stage = "transform"  
            task_data.progress = 30.0
            task_data.message = "开始双图片转换..."
            await self._push_task_update(task_data)
            
            # 使用工作流的execute_async方法提交到ComfyUI
            prompt_id = await workflow.execute_async(
                self.comfyui_service,
                workflow_params,
                lambda progress, message: self._on_transform_progress(task_data, progress, message)
            )
            self.prompt_to_request[prompt_id] = task_data.request_id
            
            logger.info(f"双图片转换任务 {task_data.request_id} 已提交到ComfyUI，prompt_id: {prompt_id}")
            
            # 等待转换完成（通过回调处理）
            await self._wait_for_transform_completion(task_data, prompt_id)
            
        except Exception as e:
            logger.error(f"双图片转换任务执行失败: {e}", exc_info=True)
            await self._fail_task(task_data, str(e))