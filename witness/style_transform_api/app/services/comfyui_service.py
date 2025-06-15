import asyncio
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import aiohttp
import aiofiles
from urllib.parse import urlparse

from comfyui_client.client import ComfyUIClient
from comfyui_client.websocket import ComfyUIWebSocketClient
from style_transform_api.app.config import settings
from style_transform_api.app.utils.task_manager import task_manager, TaskInfo
from style_transform_api.app.schemas.response import TaskStatus

logger = logging.getLogger(__name__)

class ComfyUIService:
    """ComfyUI服务封装"""
    
    def __init__(self):
        parsed_url = urlparse(settings.COMFYUI_BASE_URL)
        self.server_address = parsed_url.hostname
        self.port = parsed_url.port
        self.client = ComfyUIClient(
            server_address=self.server_address,
            port=self.port
        )
        self.ws_client = None
        self._workflow_cache = {}
        self.is_initialized = False
        
    async def initialize(self):
        """
        初始化服务, 尝试连接到ComfyUI。
        如果失败, 只记录错误, 不中断服务启动。
        """
        try:
            # 测试HTTP连接
            await self.client.system.get_system_stats()
            logger.info("ComfyUI HTTP连接成功")
            
            # 初始化并启动WebSocket客户端
            ws_url = f"ws://{self.server_address}:{self.port}/ws"
            self.ws_client = ComfyUIWebSocketClient(ws_url)
            self.ws_client.run_forever() # 在后台线程中运行
            
            # 等待WebSocket连接成功
            for _ in range(10): # 等待最多10秒
                if self.ws_client.is_connected:
                    break
                await asyncio.sleep(1)

            if not self.ws_client.is_connected:
                raise Exception("WebSocket连接超时")

            # 设置进度回调
            self.ws_client.set_progress_callback(self._on_progress)
            self.ws_client.set_completion_callback(self._on_completion)
            
            self.is_initialized = True
            logger.info("ComfyUI服务初始化完成 (HTTP和WebSocket)")
            
        except Exception as e:
            self.is_initialized = False
            logger.error(f"ComfyUI初始化失败: {e}. 服务将以非连接模式运行。")
            # 不再向上抛出异常
    
    async def close(self):
        """关闭连接"""
        if self.ws_client:
            await self.ws_client.disconnect()
        await self.client.close()
    
    async def download_image(self, image_url: str) -> bytes:
        """下载图像"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise Exception(f"下载图像失败: HTTP {response.status}")
        except Exception as e:
            logger.error(f"下载图像失败 {image_url}: {e}")
            raise
    
    async def upload_image(self, image_data: bytes, filename: str) -> str:
        """上传图像到ComfyUI"""
        try:
            # 使用ComfyUI客户端上传图像
            result = await self.client.files.upload_image(
                image_bytes=image_data,
                filename=filename
            )
            return result.get("name", filename)
        except Exception as e:
            logger.error(f"上传图像失败: {e}")
            raise
    
    async def load_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """加载工作流模板"""
        if workflow_name in self._workflow_cache:
            return self._workflow_cache[workflow_name]
        
        workflow_path = Path(settings.WORKFLOW_DIR) / f"{workflow_name}.json"
        
        try:
            async with aiofiles.open(workflow_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                workflow = json.loads(content)
                self._workflow_cache[workflow_name] = workflow
                return workflow
        except Exception as e:
            logger.error(f"加载工作流失败 {workflow_name}: {e}")
            raise
    
    async def customize_workflow(self, workflow: Dict[str, Any], 
                                input_image: str, style_type: str,
                                custom_prompt: Optional[str] = None,
                                strength: float = 0.6) -> Dict[str, Any]:
        """自定义工作流参数"""
        # 复制工作流避免修改原始模板
        customized = json.loads(json.dumps(workflow))
        
        # 根据工作流结构更新参数
        # 这里需要根据实际的style_change.json结构来调整
        for node_id, node in customized.items():
            node_type = node.get("class_type", "")
            
            # 更新输入图像
            if node_type == "LoadImage":
                node["inputs"]["image"] = input_image
            
            # 更新提示词
            elif node_type == "CLIPTextEncode":
                if "text" in node["inputs"]:
                    if custom_prompt:
                        node["inputs"]["text"] = custom_prompt
                    else:
                        # 使用预设的风格提示词
                        style_prompts = {
                            "clay": "Clay Style, lovely, 3d, cute",
                            "anime": "Anime Style, beautiful, detailed",
                            "realistic": "Realistic Style, high quality, detailed",
                            "cartoon": "Cartoon Style, colorful, fun",
                            "oil_painting": "Oil Painting Style, artistic, classical"
                        }
                        node["inputs"]["text"] = style_prompts.get(style_type, style_prompts["clay"])
            
            # 更新强度参数
            elif node_type in ["ControlNetApply", "IPAdapter"]:
                if "strength" in node["inputs"]:
                    node["inputs"]["strength"] = strength
        
        return customized
    
    async def submit_workflow(self, task_id: str, workflow: Dict[str, Any]) -> str:
        """提交工作流到ComfyUI"""
        try:
            # 提交工作流
            result = await self.client.prompts.queue_prompt(prompt=workflow)
            prompt_id = result.get("prompt_id")
            
            if not prompt_id:
                raise Exception("未获取到prompt_id")
            
            # 更新任务状态
            await task_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.PROCESSING,
                comfyui_prompt_id=prompt_id
            )
            
            logger.info(f"任务 {task_id} 提交成功，prompt_id: {prompt_id}")
            return prompt_id
            
        except Exception as e:
            logger.error(f"提交工作流失败 {task_id}: {e}")
            await task_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )
            raise
    
    async def process_image(self, task_id: str, image_url: str, 
                          style_type: str, custom_prompt: Optional[str] = None,
                          strength: float = 0.6) -> str:
        """处理单张图像"""
        try:
            # 1. 下载输入图像
            logger.info(f"任务 {task_id}: 下载图像 {image_url}")
            image_data = await self.download_image(image_url)
            
            # 2. 上传到ComfyUI
            filename = f"input_{task_id}.jpg"
            uploaded_name = await self.upload_image(image_data, filename)
            logger.info(f"任务 {task_id}: 图像上传成功 {uploaded_name}")
            
            # 3. 加载并自定义工作流
            workflow = await self.load_workflow("style_change")
            customized_workflow = await self.customize_workflow(
                workflow, uploaded_name, style_type, custom_prompt, strength
            )
            
            # 4. 提交工作流
            prompt_id = await self.submit_workflow(task_id, customized_workflow)
            
            return prompt_id
            
        except Exception as e:
            logger.error(f"处理图像失败 {task_id}: {e}")
            await task_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )
            raise
    
    async def _on_progress(self, prompt_id: str, progress_data: Dict[str, Any]):
        """进度回调"""
        try:
            # 查找对应的任务
            task = await self._find_task_by_prompt_id(prompt_id)
            if task:
                progress = progress_data.get("value", 0) * 100
                await task_manager.update_task_status(
                    task_id=task.task_id,
                    status=TaskStatus.PROCESSING,
                    progress=progress
                )
                logger.debug(f"任务 {task.task_id} 进度: {progress}%")
        except Exception as e:
            logger.error(f"处理进度回调失败: {e}")
    
    async def _on_completion(self, prompt_id: str, result_data: Dict[str, Any]):
        """完成回调"""
        try:
            # 查找对应的任务
            task = await self._find_task_by_prompt_id(prompt_id)
            if not task:
                logger.warning(f"未找到prompt_id {prompt_id} 对应的任务")
                return
            
            # 获取输出图像
            output_images = result_data.get("outputs", {})
            if output_images:
                # 假设输出节点ID为"9"（需要根据实际工作流调整）
                image_info = None
                for node_id, node_output in output_images.items():
                    if "images" in node_output:
                        image_info = node_output["images"][0]
                        break
                
                if image_info:
                    # 构建图像URL
                    filename = image_info["filename"]
                    subfolder = image_info.get("subfolder", "")
                    image_url = f"{settings.COMFYUI_BASE_URL}/view"
                    if subfolder:
                        image_url += f"?filename={filename}&subfolder={subfolder}"
                    else:
                        image_url += f"?filename={filename}"
                    
                    await task_manager.update_task_status(
                        task_id=task.task_id,
                        status=TaskStatus.COMPLETED,
                        output_image_url=image_url,
                        progress=100.0
                    )
                    logger.info(f"任务 {task.task_id} 完成，输出: {image_url}")
                else:
                    await task_manager.update_task_status(
                        task_id=task.task_id,
                        status=TaskStatus.FAILED,
                        error_message="未找到输出图像"
                    )
            else:
                await task_manager.update_task_status(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    error_message="工作流执行失败"
                )
                
        except Exception as e:
            logger.error(f"处理完成回调失败: {e}")
    
    async def _find_task_by_prompt_id(self, prompt_id: str) -> Optional[TaskInfo]:
        """根据prompt_id查找任务"""
        # 这里需要遍历所有任务，实际使用中可以考虑建立索引
        for task_id, task in task_manager._tasks.items():
            if task.comfyui_prompt_id == prompt_id:
                return task
        return None

# 全局服务实例
comfyui_service = ComfyUIService() 