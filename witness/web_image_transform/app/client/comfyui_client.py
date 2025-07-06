import time
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
import httpx
from httpx import Response
import asyncio

from app.config import settings

class ComfyUIClient:
    """
    与ComfyUI工作流服务器安全通信的客户端。
    封装了API密钥、请求签名和所有API调用。
    """

    def __init__(self):
        self.base_url = settings.COMFYUI_WORKFLOW_SERVER_URL
        self.api_key = settings.API_KEY
        self.api_secret = settings.API_SECRET_KEY
        self.client = httpx.AsyncClient(timeout=300)

    def _get_secure_headers(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """为API请求生成安全头部。"""
        timestamp = str(int(time.time()))
        
        body_str = ""
        if body:
            body_str = json.dumps(body, separators=(',', ':'), ensure_ascii=False)

        message_to_sign = f"{method.upper()}\n{path}\n{timestamp}\n{body_str}"
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'x-api-key': self.api_key,
            'x-timestamp': timestamp,
            'x-signature': signature,
            'Content-Type': 'application/json',
        }
        return headers

    async def _make_request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, files: Optional[Dict] = None) -> Response:
        """通用请求方法。"""
        url = f"{self.base_url}{path}"
        
        if not headers:
            headers = self._get_secure_headers(method, path, body)
        
        if files:
            headers.pop('Content-Type', None) # httpx handles this for multipart
            response = await self.client.request(method, url, headers=headers, files=files)
        elif body:
            response = await self.client.request(method, url, headers=headers, json=body)
        else:
            response = await self.client.request(method, url, headers=headers)
        
        response.raise_for_status()
        return response

    async def get_user_token(self, user_id: str, expires_in_minutes: int = 60) -> str:
        """为指定用户ID获取JWT令牌。"""
        path = "/api/v1/auth/token"
        method = "POST"
        body = {"user_id": user_id, "expires_in_minutes": expires_in_minutes}
        headers = self._get_secure_headers(method, path, body)
        
        response = await self._make_request(method, path, body, headers)
        return response.json()["access_token"]

    async def list_styles(self, token: str) -> Dict[str, Any]:
        """获取可用风格列表。"""
        path = "/api/v1/styles"
        method = "GET"
        headers = self._get_secure_headers(method, path)
        headers['Authorization'] = f"Bearer {token}"
        
        response = await self._make_request(method, path, headers=headers)
        return response.json()

    async def upload_file(self, file_content: bytes, filename: str, token: str) -> Dict[str, Any]:
        """上传文件。"""
        path = "/api/v1/files/upload"
        method = "POST"
        
        # 签名需要空的body
        headers = self._get_secure_headers(method, path)
        headers['Authorization'] = f"Bearer {token}"
        
        files = {'file': (filename, file_content)}
        
        response = await self._make_request(method, path, headers=headers, files=files)
        return response.json()

    async def create_transform_task(self, style_id: str, image_id: str, token: str) -> Dict[str, Any]:
        """创建转换任务。"""
        path = f"/api/v1/styles/{style_id}/transform"
        method = "POST"
        body = {"image_id": image_id}
        
        headers = self._get_secure_headers(method, path, body)
        headers['Authorization'] = f"Bearer {token}"

        response = await self._make_request(method, path, body=body, headers=headers)
        return response.json()

    async def get_task_status(self, task_id: str, token: str) -> Dict[str, Any]:
        """获取任务状态。"""
        path = f"/api/v1/tasks/{task_id}"
        method = "GET"
        headers = self._get_secure_headers(method, path)
        headers['Authorization'] = f"Bearer {token}"

        response = await self._make_request(method, path, headers=headers)
        return response.json()

    async def get_task_result(self, task_id: str, token: str) -> Dict[str, Any]:
        """获取任务结果。"""
        path = f"/api/v1/tasks/{task_id}/result"
        method = "GET"
        headers = self._get_secure_headers(method, path)
        headers['Authorization'] = f"Bearer {token}"

        response = await self._make_request(method, path, headers=headers)
        return response.json()

# 全局客户端实例
comfyui_client = ComfyUIClient()

async def main():
    # 这是一个简单的测试函数，演示如何使用客户端
    print("Testing ComfyUI Client...")
    try:
        # 1. Get user token
        user_id = "test-web-user-01"
        print(f"Getting token for user: {user_id}")
        token = await comfyui_client.get_user_token(user_id)
        print(f"Token acquired: {token[:20]}...")

        # 2. List styles
        print("\nListing available styles...")
        styles = await comfyui_client.list_styles(token)
        print(f"Found {len(styles)} styles. First one: {styles[0]['name']}")
        
        print("\nClient test successful!")
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # 要运行此测试，请确保你的 .env 文件配置正确
    # 并且 comfyui_workflow_server 正在运行
    asyncio.run(main()) 