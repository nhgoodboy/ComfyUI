import requests
import json

from ..utils.logger import get_logger
from .endpoints.prompt import PromptAPI
from .endpoints.file import FileAPI
from .endpoints.system import SystemAPI
from .endpoints.user import UserAPI
from .websocket import WebSocketClient

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

        # 初始化 API 端点模块
        self.prompt = PromptAPI(self)
        self.file = FileAPI(self)
        self.system = SystemAPI(self)
        self.user = UserAPI(self)

        self.logger.info(f"ComfyUIClient 已为服务器 {self.base_url} 初始化")

    def _request(self, method: str, endpoint: str, json_data=None, files=None, params=None):
        """
        一个用于处理所有 HTTP 请求的私有方法。
        """
        url = f"{self.base_url}{endpoint}"
        self.logger.debug(f"发送 {method} 请求到 {url}")
        try:
            response = requests.request(
                method,
                url,
                json=json_data,
                files=files,
                params=params,
                headers=self.headers
            )
            response.raise_for_status()  # 对错误的响应 (4xx 或 5xx) 抛出 HTTPError
            
            if response.headers.get('Content-Type') == 'application/json':
                return response.json()
            return response.content
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API 请求失败: {e}")
            raise

    def get_websocket(self, client_id: str):
        """
        初始化并返回一个 WebSocket 客户端。
        """
        return WebSocketClient(f"ws://{self.server_address}:{self.port}/ws?clientId={client_id}")

# 端点模块的占位符类，以便于初始化
# 这些将在它们各自的文件中被实际的实现所替换。

class BaseAPI:
    def __init__(self, client: 'ComfyUIClient'):
        self._client = client 