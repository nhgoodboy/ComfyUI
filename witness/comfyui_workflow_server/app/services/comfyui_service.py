import asyncio
import json
import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from pathlib import Path
import aiohttp
import aiofiles
from urllib.parse import urlparse, urljoin
import uuid
import time
import weakref

import sys
from pathlib import Path

# 添加comfyui_client模块路径
witness_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(witness_path))

from comfyui_client.client import ComfyUIClient
from comfyui_client.websocket import ComfyUIWebSocketClient
from ..config import get_settings

if TYPE_CHECKING:
    from ..services.transform_task_service import TransformTaskService

logger = logging.getLogger(__name__)

class ComfyUIService:
    """ComfyUI服务封装"""
    
    def __init__(self):
        settings = get_settings()
        comfyui_config = settings.comfyui
        
        parsed_url = urlparse(comfyui_config.base_url)
        if not parsed_url.hostname or not parsed_url.port:
            raise ValueError(f"无效的ComfyUI地址: {comfyui_config.base_url}")
            
        self.server_address = parsed_url.hostname
        self.port = parsed_url.port
        # 保存完整的base_url用于构建图片URL
        self.base_url = comfyui_config.base_url.rstrip('/')
        # 统一 client_id（配置优先，否则随机生成）
        self.client_id = comfyui_config.client_id or uuid.uuid4().hex

        # 连接池配置（延迟初始化）
        self.connector = None
        self.timeout = None

        self.client = ComfyUIClient(
            server_address=self.server_address,
            port=self.port,
            client_id=self.client_id
        )
        self.ws_client = None
        self._workflow_cache = {}
        self.is_initialized = False
        self.transform_task_service: Optional['TransformTaskService'] = None
        
        # 连接状态管理
        self.connection_pool = None
        self.session = None
        self.health_status = False
        self.last_health_check = 0
        self.health_check_interval = 30  # 30秒检查一次
        
        # 任务状态缓存
        self.prompt_progress: Dict[str, Dict] = {}  # prompt_id -> progress_data
        self.prompt_results: Dict[str, Dict] = {}   # prompt_id -> result_data

        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1.0
        self.backoff_factor = 2.0
        
    async def initialize(self):
        """
        初始化服务, 尝试连接到ComfyUI。
        如果失败, 只记录错误, 不中断服务启动。
        """
        try:
            # 创建连接池配置
            self.connector = aiohttp.TCPConnector(
                limit=100,  # 总连接数限制
                limit_per_host=30,  # 每个主机的连接数限制
                ttl_dns_cache=300,  # DNS缓存时间
                use_dns_cache=True,
                keepalive_timeout=30,  # 保持连接的时间
                enable_cleanup_closed=True,
                force_close=False  # 避免强制关闭连接
            )
            
            # 超时配置
            self.timeout = aiohttp.ClientTimeout(
                total=120,  # 总超时时间，考虑到图像处理可能需要更长时间
                connect=10,  # 连接超时时间
                sock_read=60,  # 读取超时时间
                sock_connect=10  # socket连接超时时间
            )
            
            # 创建连接池
            self.connection_pool = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'StyleTransformAPI/1.0',
                    'Connection': 'keep-alive'
                }
            )
            
            # 测试HTTP连接
            await self.client.system.get_system_stats()
            logger.info("ComfyUI HTTP连接成功")
            
            # 初始化并启动WebSocket客户端
            logger.info(f"初始化WebSocket客户端连接到: {self.server_address}:{self.port}, client_id: {self.client_id}")
            self.ws_client = ComfyUIWebSocketClient(host=self.server_address, port=self.port, client_id=self.client_id)
            self.ws_client.run_forever() # 在后台线程中运行
            
            # 等待WebSocket连接成功
            logger.info("等待WebSocket连接...")
            for i in range(10): # 等待最多10秒
                if self.ws_client.is_connected:
                    logger.info(f"WebSocket连接成功！用时{i+1}秒")
                    break
                await asyncio.sleep(1)
                logger.debug(f"WebSocket连接尝试 {i+1}/10...")

            if not self.ws_client.is_connected:
                logger.error(f"WebSocket连接失败: ws://{self.server_address}:{self.port}/ws?clientId={self.client_id}")
                raise Exception("WebSocket连接超时")

            # 记录当前事件循环, 供线程中的回调使用
            self._loop = asyncio.get_running_loop()

            # 通过线程安全方式把协程投递到主事件循环
            def _safe_call_async(coro_func):
                def _wrapper(*args, **kwargs):
                    try:
                        # 对于async函数，使用run_coroutine_threadsafe
                        fut = asyncio.run_coroutine_threadsafe(
                            coro_func(*args, **kwargs), self._loop
                        )
                        # 等待结果以确保执行完成
                        try:
                            fut.result(timeout=30)  # 30秒超时
                        except Exception as e:
                            logger.error(f"协程执行失败: {e}")
                    except Exception as e:
                        logger.error(f"调度回调失败: {e}")
                return _wrapper
            
            def _safe_call_sync(sync_func):
                def _wrapper(*args, **kwargs):
                    try:
                        # 对于同步函数，使用call_soon_threadsafe
                        self._loop.call_soon_threadsafe(sync_func, *args, **kwargs)
                    except Exception as e:
                        logger.error(f"调度同步回调失败: {e}")
                return _wrapper

            self.ws_client.set_progress_callback(_safe_call_sync(self._on_progress))
            self.ws_client.set_completion_callback(_safe_call_async(self._on_completion))
            
            self.health_status = True
            self.last_health_check = time.time()
            self.is_initialized = True
            logger.info("ComfyUI服务初始化完成 (HTTP和WebSocket)")
            
        except Exception as e:
            self.is_initialized = False
            self.health_status = False
            logger.error(f"ComfyUI初始化失败: {e}. 服务将以非连接模式运行。")
            # 不再向上抛出异常
    
    async def close(self):
        """关闭连接"""
        try:
            if self.ws_client:
                await self.ws_client.disconnect()
            
            if self.connection_pool:
                await self.connection_pool.close()
            
            if self.connector:
                await self.connector.close()
            
            await self.client.close()
            
            self.is_initialized = False
            self.health_status = False
            logger.info("ComfyUI服务连接已关闭")
            
        except Exception as e:
            logger.error(f"关闭连接时发生错误: {e}")
        
    async def health_check(self) -> bool:
        """健康检查"""
        current_time = time.time()
        
        # 如果距离上次检查时间过短，返回缓存的状态
        if current_time - self.last_health_check < self.health_check_interval:
            return self.health_status
        
        try:
            # 执行健康检查
            await self.client.system.get_system_stats()
            self.health_status = True
            self.last_health_check = current_time
            return True
            
        except Exception as e:
            logger.warning(f"健康检查失败: {e}")
            self.health_status = False
            self.last_health_check = current_time
            return False
    
    def set_transform_task_service(self, service: 'TransformTaskService'):
        """注入TransformTaskService实例以处理回调"""
        self.transform_task_service = service
        logger.info("TransformTaskService已成功注入到ComfyUIService")

    def _get_sampler_node_ids(self, workflow: Dict[str, Any]) -> List[str]:
        """从工作流中提取所有采样器节点的ID"""
        sampler_nodes = []
        # 定义常见的采样器节点类型
        sampler_types = ["KSampler", "SamplerCustom", "KSamplerAdvanced"]
        
        for node_id, node in workflow.items():
            if node.get("class_type") in sampler_types:
                sampler_nodes.append(node_id)
        
        return sampler_nodes

    async def download_image(self, image_url: str) -> bytes:
        """下载图像，支持重试机制"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # 使用连接池下载图像
                session = self.connection_pool or aiohttp.ClientSession()
                
                async with session.get(image_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        # 验证是否为有效的图像内容
                        if len(content) < 100:  # 图像文件至少应该有100字节
                            raise Exception(f"图像内容过小: {len(content)} 字节")
                        return content
                    else:
                        raise Exception(f"下载图像失败: HTTP {response.status}")
                        
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.warning(f"下载图像失败 {image_url} (尝试 {attempt + 1}/{self.max_retries}): {e}, {delay}秒后重试")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"下载图像最终失败 {image_url}: {e}")
                    
        if last_exception is None:
            raise Exception(f"下载图像最终失败 {image_url}，但没有捕获到具体异常")
        raise last_exception
    
    async def upload_image(self, image_data: bytes, filename: str) -> str:
        """上传图像到ComfyUI"""
        try:
            # 使用ComfyUI客户端上传图像
            result = await self.client.files.upload_image(
                image_bytes=image_data,
                filename=filename,
                overwrite=True # 允许覆盖
            )
            if not isinstance(result, dict):
                raise TypeError(f"上传图像后期望获得字典，但收到了 {type(result)}")
                
            return result.get("name", filename)
        except Exception as e:
            logger.error(f"上传图像失败: {e}", exc_info=True)
            raise

    async def load_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """
        从文件加载工作流模板, 并缓存。
        同时提取并缓存采样器节点ID。
        """
        if workflow_name in self._workflow_cache:
            return self._workflow_cache[workflow_name]["workflow"]
            
        workflow_path = Path(__file__).parent.parent / "workflows" / f"{workflow_name}.json"
        
        if not workflow_path.exists():
            raise FileNotFoundError(f"工作流文件未找到: {workflow_path}")
            
        async with aiofiles.open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.loads(await f.read())
            
        sampler_node_ids = self._get_sampler_node_ids(workflow)
        
        self._workflow_cache[workflow_name] = {
            "workflow": workflow,
            "sampler_node_ids": sampler_node_ids
        }
        
        return workflow

    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """
        将工作流加入ComfyUI队列。
        返回 prompt_id。
        """
        result = await self.client.prompts.queue_prompt(prompt=workflow)
        if not isinstance(result, dict) or "prompt_id" not in result:
            raise ValueError(f"从ComfyUI获取prompt_id失败，API响应: {result}")
        return result['prompt_id']

    async def get_result(self, prompt_id: str) -> Dict[str, Any]:
        """
        从ComfyUI历史记录中获取结果。
        注意：这是一个简化的实现，仅用于演示。
        在生产环境中，应该使用更健壮的WebSocket消息处理。
        """
        history = await self.client.prompts.get_history(prompt_id)
        if not isinstance(history, dict) or prompt_id not in history:
            return {}
        
        result = history.get(prompt_id, {})
        
        # 注意：这里我们不再需要轮询历史记录，因为WebSocket提供了更可靠的方式
        return result
    
    def get_prompt_status(self, prompt_id: str) -> Dict[str, Any]:
        """从缓存中获取任务状态"""
        if prompt_id in self.prompt_results:
            return {"status": "completed", "result": self.prompt_results[prompt_id]}
        
        if prompt_id in self.prompt_progress:
            return {"status": "running", "progress": self.prompt_progress[prompt_id]}
        
        return {"status": "pending"}
    
    async def submit_workflow(self, request_id: str, workflow: Dict[str, Any]) -> str:
        """
        提交工作流并开始监控
        """
        prompt_id = await self.queue_prompt(workflow)
        logger.info(f"任务 {request_id} 已提交到ComfyUI, prompt_id: {prompt_id}")
        return prompt_id

    def _on_progress(self, prompt_id: str, progress_data: Dict[str, Any]):
        """处理进度更新事件"""
        logger.info(f"ComfyUIService收到进度事件: prompt_id={prompt_id}, data={progress_data}")
        if self.transform_task_service:
            self.transform_task_service.handle_progress_update(prompt_id, progress_data)
        else:
            logger.warning("TransformTaskService未注入，无法处理进度更新")

    async def _on_completion(self, prompt_id: str, result_data: Dict[str, Any]):
        """处理任务完成事件 (成功或失败)"""
        logger.info(f"ComfyUIService收到完成事件: prompt_id={prompt_id}, data={result_data}")
        if self.transform_task_service:
            await self.transform_task_service.handle_completion_update(prompt_id, result_data)
        else:
            logger.warning("TransformTaskService未注入，无法处理完成更新")



    async def _wait_until_view_ready(self, url: str, timeout: int = 10, interval: float = 0.5) -> bool:
        """等待直到/view端点返回有效的图像数据"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            # 简单的检查，确保响应头看起来像一个图像
                            if 'image' in response.headers.get('Content-Type', ''):
                                return True
            except aiohttp.ClientError:
                pass  # 忽略连接错误，继续重试
            await asyncio.sleep(interval)
        return False 