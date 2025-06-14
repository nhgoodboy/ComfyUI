# witness/utils/http_client.py
# HTTP 客户端工具类，用于与 ComfyUI API 进行交互。
import requests
import json
from ..config import settings

class HttpClient:
    def __init__(self, base_url=None, api_key=None, timeout=None):
        self.base_url = base_url or settings.COMFYUI_API_URL
        self.api_key = api_key or settings.COMFYUI_API_KEY
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self.session = requests.Session()
        if self.api_key:
            # 注意：ComfyUI 的 API 密钥机制可能会有所不同。
            # 此示例假设它可能是 headers 的一部分或特定的 payload 结构。
            # 提供的 API 文档建议它位于 /prompt 的 `extra_data` 中。
            # 对于其他端点，没有明确定义，因此 header 是一种常见的做法。
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def _prepare_payload(self, payload=None):
        """准备 payload，如果特定端点需要，可能会添加 API 密钥。"""
        if payload is None:
            payload = {}
        # 对于 /prompt，API 密钥在 extra_data 中，由特定的客户端方法处理。
        # 如果其他端点期望不同，这是一个通用的占位符。
        return payload

    def get(self, endpoint, params=None, **kwargs):
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            return response.content # 用于二进制数据，例如图像
        except requests.exceptions.RequestException as e:
            print(f"HTTP GET request to {url} failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response content: {e.response.text}")
            raise

    def post(self, endpoint, data=None, json_data=None, **kwargs):
        url = f"{self.base_url}{endpoint}"
        payload = self._prepare_payload(data if data is not None else json_data)
        
        try:
            if json_data is not None:
                response = self.session.post(url, json=payload, timeout=self.timeout, **kwargs)
            else:
                response = self.session.post(url, data=payload, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"HTTP POST request to {url} failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response content: {e.response.text}")
            raise

    def multipart_post(self, endpoint, files=None, data=None, **kwargs):
        url = f"{self.base_url}{endpoint}"
        payload = self._prepare_payload(data)
        try:
            response = self.session.post(url, files=files, data=payload, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"HTTP Multipart POST request to {url} failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response content: {e.response.text}")
            raise

# 示例用法 (可以删除或移动到测试/示例文件)
if __name__ == '__main__':
    client = HttpClient()
    try:
        # 示例：获取系统统计信息 (假设 ComfyUI 正在运行)
        stats = client.get("/system_stats")
        print("系统统计信息:", stats)
    except Exception as e:
        print(f"无法连接或获取统计信息: {e}")