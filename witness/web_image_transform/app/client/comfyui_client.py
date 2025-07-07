import time
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
import httpx
from httpx import Response
import asyncio
import logging
import urllib.parse

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

    def _get_secure_headers(self, method: str, path: str, query: str = "", body: Optional[bytes] = None) -> Dict[str, str]:
        """为API请求生成安全头部，与服务器逻辑完全匹配。"""
        timestamp = str(int(time.time()))
        
        # 1. 计算Body哈希
        body_hash = hashlib.sha256(body if body else b"").hexdigest()

        # 2. 构造服务器端签名字符串
        # 格式: timestamp + method + path + query + body_hash
        message_to_sign = f"{timestamp}{method.upper()}{path}{query}{body_hash}"
        
        # 3. 计算HMAC-SHA256签名
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

    async def _make_request(self, method: str, path: str, data: Optional[Dict[str, str]] = None, body: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, files: Optional[Dict] = None, token: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Response:
        """通用请求方法。"""
        url = f"{self.base_url}{path}"
        
        # --- 修复：为签名生成正确的查询字符串 ---
        query_string = ""
        if params:
            query_string = urllib.parse.urlencode(params)
        
        body_bytes: Optional[bytes] = None
        if body:
            body_bytes = json.dumps(body, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

        # 优先使用外部传入的headers，否则生成基础签名头
        final_headers = headers if headers is not None else self._get_secure_headers(method, path, query=query_string, body=body_bytes)

        # 如果提供了token，确保Authorization头存在
        if token:
            final_headers['Authorization'] = f"Bearer {token}"

        if files:
            # 文件上传时，签名时不包含文件内容，body_hash是空字符串的哈希
            # 我们需要重新生成签名头，但保留其他头部（如Authorization）
            upload_headers = self._get_secure_headers(method, path, query=query_string, body=b"")
            # 合并其他重要的头
            if 'Authorization' in final_headers:
                upload_headers['Authorization'] = final_headers['Authorization']
            
            upload_headers.pop('Content-Type', None) # httpx handles this for multipart
            
            # --- 决定性调试日志 ---
            logging.warning(f"DEBUG: Uploading with headers: {upload_headers}")
            
            response = await self.client.request(method, url, headers=upload_headers, files=files, params=params)
        elif data:
            # 对于表单数据（如认证），签名时body部分为空，且不需要Bearer token
            form_headers = self._get_secure_headers(method, path, query=query_string, body=b"")
            form_headers['Content-Type'] = 'application/x-www-form-urlencoded'
            response = await self.client.request(method, url, headers=form_headers, data=data, params=params)
        elif body_bytes:
            response = await self.client.request(method, url, headers=final_headers, content=body_bytes, params=params)
        else:
            response = await self.client.request(method, url, headers=final_headers, params=params)
        
        response.raise_for_status()
        return response

    async def get_user_token(self, user_id: str, expires_in_minutes: int = 60) -> str:
        """为指定用户ID获取JWT令牌。"""
        path = "/api/v1/auth/token"
        method = "POST"

        form_data = {
            "grant_type": "password",
            "username": settings.API_USERNAME,
            "password": settings.API_KEY
        }
        
        # --- 修复：添加缓存破坏者参数 ---
        cache_buster_params = {"_": int(time.time())}
        
        response = await self._make_request(method, path, data=form_data, params=cache_buster_params)
        return response.json()["access_token"]

    async def list_styles(self, token: str) -> list[dict]:
        """获取可用风格列表。"""
        path = "/api/v1/styles/"
        method = "GET"
        response = await self._make_request(method, path, token=token)
        return response.json()

    async def upload_file(self, file_content: bytes, filename: str, token: str) -> Dict[str, Any]:
        """上传文件。"""
        path = "/api/v1/files/upload"
        method = "POST"
        files = {'file': (filename, file_content)}
        response = await self._make_request(method, path, files=files, token=token)
        upload_result = response.json()
        return upload_result

    async def create_transform_task(self, style_id: str, image_id: str, token: str) -> Dict[str, Any]:
        """创建转换任务。"""
        path = "/api/v1/styles/transform"
        method = "POST"
        body = {"style_id": style_id, "image_url": image_id}
        response = await self._make_request(method, path, body=body, token=token)
        return response.json()

    async def get_task_status(self, task_id: str, token: str) -> Dict[str, Any]:
        """获取任务状态。"""
        path = f"/api/v1/tasks/{task_id}"
        method = "GET"
        response = await self._make_request(method, path, token=token)
        return response.json()

    async def get_task_result(self, task_id: str, token: str) -> Dict[str, Any]:
        """获取任务结果。"""
        path = f"/api/v1/tasks/{task_id}/result"
        method = "GET"
        response = await self._make_request(method, path, token=token)
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