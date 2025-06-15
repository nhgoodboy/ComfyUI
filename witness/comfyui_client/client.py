import aiohttp
import asyncio
import json
import uuid

from .utils.logger import get_logger
from .endpoints.prompt import PromptAPI
from .endpoints.file import FileAPI
from .endpoints.system import SystemAPI
from .endpoints.user import UserAPI
from .websocket import ComfyUIWebSocketClient

class ComfyUIClient:
    """
    用于与 ComfyUI API 交互的主客户端。
    """
    def __init__(self, server_address: str = "127.0.0.1", port: int = 8188, user_id: str = None):
        self.server_address = server_address
        self.port = port
        self.user_id = user_id
        self.base_url = f"http://{self.server_address}:{self.port}"
        self.logger = get_logger()

        # 请求头部信息
        self.headers = {}
        if self.user_id:
            self.headers['comfy-user'] = self.user_id

        # 为 WebSocket / Prompt 使用的默认 client_id
        self.client_id = uuid.uuid4().hex

        # 创建 aiohttp 会话
        self._session: aiohttp.ClientSession | None = None

        # 初始化 API 端点模块（统一使用复数属性以符合调用方）
        self.prompts = PromptAPI(self)
        self.files = FileAPI(self)
        # 向后兼容旧代码
        self.file = self.files
        self.system = SystemAPI(self)
        self.user = UserAPI(self)

        self.logger.info(f"ComfyUIClient 已为服务器 {self.base_url} 初始化")

    async def _ensure_session(self):
        """确保 aiohttp 会话已创建"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)

    async def _request(self, method: str, endpoint: str, json_data=None, files=None, params=None):
        """
        统一异步 HTTP 请求处理方法。
        supports json_data / files / params.
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        self.logger.debug(f"发送 {method} 请求到 {url}")

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

        try:
            async with self._session.request(method, url, json=data, data=form, params=params) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await resp.json()
                return await resp.read()
        except aiohttp.ClientResponseError as e:
            self.logger.error(f"API 请求失败: {e}")
            raise

    def get_websocket(self, client_id: str | None = None):
        """初始化并返回一个 WebSocket 客户端。若未提供 client_id 则使用默认"""
        if client_id is None:
            client_id = self.client_id
        return ComfyUIWebSocketClient(f"ws://{self.server_address}:{self.port}/ws?clientId={client_id}")

    async def close(self):
        """关闭 aiohttp 会话"""
        if self._session and not self._session.closed:
            await self._session.close()
        self.logger.info("ComfyUIClient 已关闭")

# 端点模块的占位符类，以便于初始化
# 这些将在它们各自的文件中被实际的实现所替换。

class BaseAPI:
    def __init__(self, client: 'ComfyUIClient'):
        self._client = client 