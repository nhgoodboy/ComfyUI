import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
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
from ..config import comfyui_config, storage_config

logger = logging.getLogger(__name__)

class ComfyUIService:
    """ComfyUI服务封装"""
    
    def __init__(self):
        parsed_url = urlparse(comfyui_config.base_url)
        if not parsed_url.hostname or not parsed_url.port:
            raise ValueError(f"无效的ComfyUI地址: {comfyui_config.base_url}")
            
        self.server_address = parsed_url.hostname
        self.port = parsed_url.port
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
        
        # 连接状态管理
        self.connection_pool = None
        self.session = None
        self.health_status = False
        self.last_health_check = 0
        self.health_check_interval = 30  # 30秒检查一次
        
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
                filename=filename
            )
            if not isinstance(result, dict):
                raise TypeError(f"上传图像后期望获得字典，但收到了 {type(result)}")
                
            return result.get("name", filename)
        except Exception as e:
            logger.error(f"上传图像失败: {e}")
            raise
    
    async def load_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """加载工作流模板"""
        if workflow_name in self._workflow_cache:
            return self._workflow_cache[workflow_name]
        
        workflow_path = storage_config.workflows_dir / f"{workflow_name}.json"
        
        try:
            async with aiofiles.open(workflow_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                workflow = json.loads(content)
                self._workflow_cache[workflow_name] = workflow
                return workflow
        except Exception as e:
            logger.error(f"加载工作流失败 {workflow_name}: {e}")
            raise
    
# 废弃方法已删除：customize_workflow - 旧架构专用方法
    
    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """将工作流加入队列"""
        try:
            result = await self.client.prompts.queue_prompt(prompt=workflow, client_id=self.client_id)
            
            if not isinstance(result, dict):
                raise TypeError(f"排队请求后期望获得字典，但收到了 {type(result)}")
                
            prompt_id = result.get("prompt_id")
            if not prompt_id:
                raise ValueError(f"API响应中缺少 'prompt_id': {result}")
            return prompt_id
        except Exception as e:
            logger.error(f"加入队列失败: {e}")
            raise
            
    async def get_result(self, prompt_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        try:
            history = await self.client.prompts.get_history(prompt_id)
            if not isinstance(history, dict):
                raise TypeError(f"获取历史记录后期望获得字典，但收到了 {type(history)}")

            if prompt_id not in history:
                return {"status": "pending", "prompt_id": prompt_id}
            
            return history[prompt_id]
        except Exception as e:
            logger.error(f"获取结果失败: {e}")
            raise

    async def get_prompt_status(self, prompt_id: str) -> str:
        """获取提示的状态 (running, completed, etc)"""
        try:
            queue_info = await self.client.prompts.get_queue()
            if isinstance(queue_info, dict):
                # 检查运行中的队列
                for item in queue_info.get("queue_running", []):
                    if item[1] == prompt_id:
                        return "running"
                
                # 检查待处理的队列
                for item in queue_info.get("queue_pending", []):
                    if item[1] == prompt_id:
                        return "pending"
            else:
                 raise TypeError(f"获取队列信息后期望获得字典，但收到了 {type(queue_info)}")

            # 检查历史记录
            history = await self.client.prompts.get_history(prompt_id)
            if isinstance(history, dict) and prompt_id in history:
                return "completed"
            
            return "unknown"
        except Exception as e:
            logger.error(f"获取提示状态失败: {e}")
            return "error"
            
    async def submit_workflow(self, task_id: str, workflow: Dict[str, Any]) -> str:
        """提交工作流并启动后台轮询"""
        try:
            # 提交工作流
            result = await self.client.prompts.queue_prompt(prompt=workflow, client_id=self.client_id)
            prompt_id = result.get("prompt_id")
            
            if not prompt_id:
                raise Exception("未获取到prompt_id")
            
            logger.info(f"任务 {task_id} 提交成功，prompt_id: {prompt_id}, client_id: {self.client_id}")
            return prompt_id
            
        except Exception as e:
            logger.error(f"提交工作流失败 {task_id}: {e}")
            raise
    
# 废弃方法已删除：process_image - 旧架构专用方法
    
    async def _on_progress(self, prompt_id: str, progress_data: Dict[str, Any]):
        """处理进度更新"""
        try:
            logger.debug(f"收到进度更新: {prompt_id}, 数据: {progress_data}")
            
            # 这里可以添加进度处理逻辑
            # 新架构中，进度通过WorkflowManager处理
            
        except Exception as e:
            logger.error(f"处理进度更新失败: {e}")

    async def _on_completion(self, prompt_id: str, result_data: Dict[str, Any]):
        """处理完成事件"""
        try:
            logger.info(f"收到完成事件: {prompt_id}")
            
            # 这里可以添加完成处理逻辑
            # 新架构中，完成事件通过WorkflowManager处理
            
        except Exception as e:
            logger.error(f"处理完成事件失败: {e}")

    async def _find_task_by_prompt_id(self, prompt_id: str) -> Optional[str]:
        """根据prompt_id查找任务ID（暂时返回None，由新架构处理）"""
        # 新架构中，这个映射由WorkflowManager维护
        return None

    async def _poll_history(self, task_id: str, prompt_id: str):
        """轮询ComfyUI历史记录（简化版本）"""
        try:
            logger.debug(f"开始轮询历史记录: {task_id}, {prompt_id}")
            
            # 在新架构中，这个功能被WorkflowManager的监控机制替代
            # 这里只是占位符
            
        except Exception as e:
            logger.error(f"轮询历史记录失败: {e}")

    async def _wait_until_view_ready(self, url: str, timeout: int = 10, interval: float = 0.5) -> bool:
        """等待图像URL可访问"""
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

# 全局服务实例（惰性初始化）
_comfyui_service = None

def get_comfyui_service() -> ComfyUIService:
    """获取ComfyUI服务实例，惰性初始化"""
    global _comfyui_service
    if _comfyui_service is None:
        _comfyui_service = ComfyUIService()
    return _comfyui_service

# 向后兼容
comfyui_service = None 