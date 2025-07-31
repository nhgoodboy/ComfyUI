import aiohttp
import asyncio
import json
import time
import uuid
from typing import Optional, Union, Any

from .utils.logger import get_logger
from .config import ComfyUIClientConfig
from .exceptions import (
    ComfyUIConnectionError, ComfyUIAPIError, ComfyUIValidationError,
    ComfyUITimeoutError, ComfyUIFileError
)
from .endpoints.prompt import PromptAPI
from .endpoints.file import FileAPI
from .endpoints.system import SystemAPI
from .endpoints.user import UserAPI
from .endpoints.model import ModelAPI
from .endpoints.userdata import UserDataAPI
from .endpoints.internal import InternalAPI
from .websocket import ComfyUIWebSocketClient

class ComfyUIClient:
    """
    用于与 ComfyUI API 交互的主客户端。
    """
    def __init__(self, 
                 server_address: str = "127.0.0.1", 
                 port: int = 8188, 
                 user_id: Optional[str] = None, 
                 client_id: Optional[str] = None,
                 config: Optional[ComfyUIClientConfig] = None,
                 use_api_prefix: bool = False):
        self.server_address = server_address
        self.port = port
        self.user_id = user_id
        self.base_url = f"http://{self.server_address}:{self.port}"
        self.config = config or ComfyUIClientConfig.create_default()
        self.api_prefix = "/api" if use_api_prefix else ""
        self.logger = get_logger()

        # 请求头部信息
        self.headers = {
            'User-Agent': self.config.user_agent
        }
        if self.user_id:
            self.headers['comfy-user'] = self.user_id

        # 为 WebSocket / Prompt 使用的 client_id，可从外部传入以保持与 WebSocket 一致
        self.client_id = client_id or uuid.uuid4().hex

        # 创建 aiohttp 会话
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None

        # 初始化 API 端点模块（统一使用复数属性以符合调用方）
        self.prompts = PromptAPI(self)
        self.files = FileAPI(self)
        # 向后兼容旧代码
        self.file = self.files
        self.system = SystemAPI(self)
        self.user = UserAPI(self)
        self.models = ModelAPI(self)
        self.userdata = UserDataAPI(self)
        self.internal = InternalAPI(self)

        self.logger.info(f"ComfyUIClient 已为服务器 {self.base_url} 初始化")

    async def _ensure_session(self):
        """确保 aiohttp 会话已创建"""
        if self._session is None or self._session.closed:
            if self._connector is None:
                self._connector = self.config.to_aiohttp_connector()
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                connector=self._connector,
                timeout=self.config.to_aiohttp_timeout()
            )

    async def _request(self, method: str, endpoint: str, json_data=None, files=None, params=None):
        """
        统一异步 HTTP 请求处理方法。
        supports json_data / files / params.
        """
        return await self._request_with_retry(method, endpoint, json_data, files, params)

    async def _request_with_data(self, method: str, endpoint: str, data: bytes, params=None):
        """
        发送原始数据的HTTP请求。
        """
        return await self._request_with_retry(method, endpoint, None, None, params, raw_data=data)

    async def _request_with_retry(self, method: str, endpoint: str, json_data=None, files=None, params=None, raw_data=None):
        """
        带重试机制的HTTP请求处理。
        """
        await self._ensure_session()
        if self._session is None:
            raise ComfyUIConnectionError("无法创建HTTP会话")
        
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        # 处理文件上传
        data = json_data
        form = None
        if files:
            # files = {"image": bytes/IO}
            form = aiohttp.FormData()
            for field_name, file_obj in files.items():
                form.add_field(field_name, file_obj, filename=getattr(file_obj, "name", "file"))
            # 额外的json_data放在 form 字段中
            if json_data:
                for k, v in json_data.items():
                    form.add_field(k, str(v))
            data = None  # form will be used instead
        elif raw_data:
            data = raw_data
        
        last_exception = None
        for attempt in range(self.config.max_retries + 1):
            try:
                if self.config.log_requests:
                    self.logger.debug(f"发送 {method} 请求到 {url} (尝试 {attempt + 1}/{self.config.max_retries + 1})")
                
                async with self._session.request(method, url, json=data if not form and not raw_data else None, 
                                               data=form if form else (data if raw_data else None), 
                                               params=params) as resp:
                    if self.config.log_responses:
                        self.logger.debug(f"收到响应: {resp.status}")
                    
                    resp.raise_for_status()
                    content_type = resp.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        return await resp.json()
                    return await resp.read()
                    
            except asyncio.TimeoutError as e:
                last_exception = ComfyUITimeoutError(
                    f"请求超时: {method} {url}", 
                    timeout_seconds=self.config.request_timeout,
                    operation=f"{method} {endpoint}"
                )
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    self.logger.warning(f"请求超时，{delay}秒后重试")
                    await asyncio.sleep(delay)
                    continue
                    
            except aiohttp.ClientResponseError as e:
                last_exception = ComfyUIAPIError(
                    f"API请求失败: {e.message}",
                    endpoint=endpoint,
                    method=method,
                    status_code=e.status
                )
                if attempt < self.config.max_retries and e.status >= 500:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    self.logger.warning(f"服务器错误，{delay}秒后重试")
                    await asyncio.sleep(delay)
                    continue
                break
                
            except aiohttp.ClientConnectorError as e:
                last_exception = ComfyUIConnectionError(
                    f"连接失败: {str(e)}",
                    server_url=self.base_url
                )
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    self.logger.warning(f"连接失败，{delay}秒后重试")
                    await asyncio.sleep(delay)
                    continue
                break
                
            except Exception as e:
                last_exception = ComfyUIAPIError(
                    f"请求处理失败: {str(e)}",
                    endpoint=endpoint,
                    method=method
                )
                break
        
        if last_exception:
            self.logger.error(f"所有重试都失败了: {last_exception}")
            raise last_exception

    def get_websocket(self, client_id: Optional[str] = None):
        """初始化并返回一个 WebSocket 客户端。若未提供 client_id 则使用默认"""
        if client_id is None:
            client_id = self.client_id
        return ComfyUIWebSocketClient(
            f"ws://{self.server_address}:{self.port}/ws?clientId={client_id}",
            debug=self.config.websocket_debug
        )

    async def close(self):
        """关闭 aiohttp 会话和连接器"""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector and not self._connector.closed:
            await self._connector.close()
        self.logger.info("ComfyUIClient 已关闭")
    
    # 便捷方法
    async def health_check(self):
        """
        快速健康检查，测试与 ComfyUI 服务器的连接。
        
        :return: 如果连接正常返回 True，否则返回 False
        """
        try:
            await self.system.get_system_stats()
            return True
        except Exception as e:
            self.logger.warning(f"健康检查失败: {e}")
            return False
    
    async def wait_for_completion(self, prompt_id: str, timeout: float = 300.0, check_interval: float = 1.0):
        """
        等待指定提示的完成。
        
        :param prompt_id: 要等待的提示 ID
        :param timeout: 最大等待时间（秒）
        :param check_interval: 检查间隔（秒）
        :return: 完成后的历史记录
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                history = await self.prompts.get_history(prompt_id)
                if prompt_id in history:
                    return history[prompt_id]
                await asyncio.sleep(check_interval)
            except Exception as e:
                self.logger.warning(f"等待完成时出错: {e}")
                await asyncio.sleep(check_interval)
        
        raise ComfyUITimeoutError(
            f"等待提示 {prompt_id} 完成超时",
            timeout_seconds=timeout,
            operation="wait_for_completion"
        )
    
    async def submit_and_wait(self, prompt: dict, timeout: float = 300.0, check_interval: float = 1.0):
        """
        提交提示并等待完成的便捷方法。
        
        :param prompt: 工作流提示
        :param timeout: 最大等待时间（秒）
        :param check_interval: 检查间隔（秒）
        :return: 完成后的历史记录
        """
        # 提交提示
        result = await self.prompts.queue_prompt(prompt)
        prompt_id = result.get("prompt_id")
        
        if not prompt_id:
            raise ComfyUIAPIError("提交提示后未获得 prompt_id")
        
        # 等待完成
        return await self.wait_for_completion(prompt_id, timeout, check_interval)

# 端点模块的占位符类，以便于初始化
# 这些将在它们各自的文件中被实际的实现所替换。

class BaseAPI:
    def __init__(self, client: 'ComfyUIClient'):
        self._client = client 