import asyncio
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import aiohttp
import aiofiles
from urllib.parse import urlparse, urljoin
import uuid
import time

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
        # 统一 client_id（配置优先，否则随机生成）
        self.client_id = settings.COMFYUI_CLIENT_ID or uuid.uuid4().hex

        self.client = ComfyUIClient(
            server_address=self.server_address,
            port=self.port,
            client_id=self.client_id
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
            self.ws_client = ComfyUIWebSocketClient(host=self.server_address, port=self.port, client_id=self.client_id)
            self.ws_client.run_forever() # 在后台线程中运行
            
            # 等待WebSocket连接成功
            for _ in range(10): # 等待最多10秒
                if self.ws_client.is_connected:
                    break
                await asyncio.sleep(1)

            if not self.ws_client.is_connected:
                raise Exception("WebSocket连接超时")

            # 记录当前事件循环, 供线程中的回调使用
            self._loop = asyncio.get_running_loop()

            # 通过线程安全方式把协程投递到主事件循环
            def _safe_call(coro_func):
                def _wrapper(prompt_id: str, payload: dict):
                    try:
                        fut = asyncio.run_coroutine_threadsafe(
                            coro_func(prompt_id, payload), self._loop
                        )
                        # 可选择忽略返回值
                    except Exception as e:
                        logger.error(f"调度回调失败: {e}")
                return _wrapper

            self.ws_client.set_progress_callback(_safe_call(self._on_progress))
            self.ws_client.set_completion_callback(_safe_call(self._on_completion))
            
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
    
    def _get_sampler_node_ids(self, workflow: Dict[str, Any]) -> list[str]:
        """从工作流中提取所有采样器节点的ID"""
        sampler_nodes = []
        # 定义常见的采样器节点类型
        sampler_types = ["KSampler", "SamplerCustom", "KSamplerAdvanced"]
        
        for node_id, node in workflow.items():
            if node.get("class_type") in sampler_types:
                sampler_nodes.append(node_id)
        
        return sampler_nodes

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
            # 提取采样器节点ID
            sampler_node_ids = self._get_sampler_node_ids(workflow)

            # 提交工作流
            result = await self.client.prompts.queue_prompt(prompt=workflow, client_id=self.client_id)
            prompt_id = result.get("prompt_id")
            
            if not prompt_id:
                raise Exception("未获取到prompt_id")
            
            # 更新任务状态，并存入采样器ID
            await task_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.PROCESSING,
                comfyui_prompt_id=prompt_id,
                sampler_node_ids=sampler_node_ids
            )
            
            logger.info(f"任务 {task_id} 提交成功，prompt_id: {prompt_id}, client_id: {self.client_id}")
            
            # 启动兜底轮询
            asyncio.create_task(self._poll_history(task_id, prompt_id))
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
            if not task:
                return

            # 检查是否是我们关心的采样器节点的进度
            node_id = progress_data.get("node")
            if node_id and task.sampler_node_ids and node_id not in task.sampler_node_ids:
                return # 忽略非采样器节点的进度

            value = progress_data.get("value")
            max_v = progress_data.get("max")

            # 仅当 value 和 max 都存在且有效时才处理
            if isinstance(value, (int, float)) and isinstance(max_v, (int, float)) and max_v > 0:
                progress = min(max(value / max_v * 100, 0), 100)  # 计算并裁剪到 0-100

                await task_manager.update_task_status(
                    task_id=task.task_id,
                    status=TaskStatus.PROCESSING,
                    progress=progress
                )
                logger.debug(f"任务 {task.task_id} 进度: {progress:.1f}%")

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
            
            # 兼容 ComfyUI 不同版本：有的键名为 "outputs"，有的为 "output"
            output_images = result_data.get("outputs") or result_data.get("output") or {}
            
            logger.debug(f"执行完成回调 raw output_images: {output_images}")
            
            if output_images:
                image_info = None

                # 情形1：output_images 本身带有 "images" 字段（较新 ComfyUI 版本）
                if isinstance(output_images, dict) and "images" in output_images:
                    img_list = output_images.get("images", [])
                    if img_list:
                        image_info = img_list[0]

                # 情形2：旧版格式，最外层按 node_id 分组
                if image_info is None and isinstance(output_images, dict):
                    for _node_id, node_output in output_images.items():
                        if isinstance(node_output, dict) and "images" in node_output:
                            img_list = node_output["images"]
                            if img_list:
                                image_info = img_list[0]
                                break

                if image_info:
                    # 构建图像URL
                    filename = image_info["filename"]
                    subfolder = image_info.get("subfolder", "")
                    img_type = image_info.get("type", "")

                    # 如果是 temp 类型且未提供子目录, ComfyUI 实际存放在 temp 目录
                    if not subfolder and img_type == "temp":
                        subfolder = "temp"

                    query_parts = [f"filename={filename}"]
                    # ComfyUI /view 支持 subfolder 和 type 可选参数
                    if subfolder:
                        query_parts.append(f"subfolder={subfolder}")
                    if img_type:
                        query_parts.append(f"type={img_type}")

                    query_string = "&".join(query_parts)
                    # 使用 urljoin 确保 URL 格式正确，避免双斜杠
                    base_view_url = urljoin(settings.COMFYUI_BASE_URL, "view")
                    image_url = f"{base_view_url}?{query_string}"
                    
                    # 等待 /view 端点可访问，避免前端403
                    if await self._wait_until_view_ready(image_url):
                        await task_manager.update_task_status(
                            task_id=task.task_id,
                            status=TaskStatus.COMPLETED,
                            output_image_url=image_url,
                            progress=100.0
                        )
                        logger.info(f"任务 {task.task_id} 完成，输出: {image_url}")
                    else:
                        logger.debug(f"输出 {image_url} 在等待超时内不可访问，延迟完成")
                        return
                else:
                    # executed 消息不包含 output 字段，可能是其他插件事件，忽略
                    return
                
        except Exception as e:
            logger.error(f"处理完成回调失败: {e}")
    
    async def _find_task_by_prompt_id(self, prompt_id: str) -> Optional[TaskInfo]:
        """根据prompt_id查找任务"""
        # 这里需要遍历所有任务，实际使用中可以考虑建立索引
        for task_id, task in task_manager._tasks.items():
            if task.comfyui_prompt_id == prompt_id:
                return task
        return None

    async def _poll_history(self, task_id: str, prompt_id: str):
        """在未收到 WebSocket 事件时轮询 ComfyUI /history 作为兜底"""
        start_time = time.time()
        poll_interval = 3  # 秒
        try:
            while True:
                # 若任务已结束则退出
                task = await task_manager.get_task(task_id)
                if not task or task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    return

                # 超时检查
                if time.time() - start_time > settings.COMFYUI_TIMEOUT:
                    await task_manager.update_task_status(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        error_message="任务超时"
                    )
                    return

                try:
                    history = await self.client.prompts.get_history(prompt_id)
                    # 检查 prompt_id 是否是 history 字典中的一个键
                    if history and prompt_id in history:
                        # 将特定 prompt 的数据传递给完成回调
                        await self._on_completion(prompt_id, history[prompt_id])
                        return
                except Exception as e:
                    logger.debug(f"轮询 history 失败: {e}")

                await asyncio.sleep(poll_interval)
        except Exception as e:
            logger.error(f"轮询任务 {task_id} 失败: {e}")

    async def _wait_until_view_ready(self, url: str, timeout: int = 10, interval: float = 0.5) -> bool:
        """轮询查看 /view 图片是否可访问"""
        start = time.time()
        async with aiohttp.ClientSession() as session:
            while time.time() - start < timeout:
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            return True
                except Exception:
                    pass
                await asyncio.sleep(interval)
        return False

# 全局服务实例
comfyui_service = ComfyUIService() 