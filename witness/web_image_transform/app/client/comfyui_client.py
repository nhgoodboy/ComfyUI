import asyncio
import logging
from typing import Dict, Any, Optional
import httpx
from httpx import Response

from app.config import settings

class ComfyUIClient:
    """
    与简化的ComfyUI工作流服务器通信的客户端。
    已移除认证复杂性，专注于核心API调用。
    """

    def __init__(self):
        self.base_url = settings.COMFYUI_WORKFLOW_SERVER_URL
        self.client = httpx.AsyncClient(timeout=300, follow_redirects=True)

    async def _make_request(self, method: str, url: str, **kwargs) -> Response:
        """简化的请求方法，无需认证。"""
        full_url = f"{self.base_url}{url}"
        
        response = await self.client.request(method, full_url, **kwargs)
        response.raise_for_status()
        return response

    async def list_styles(self) -> list[dict]:
        """获取可用风格列表。"""
        url = "/api/v1/styles"
        response = await self._make_request("GET", url)
        return response.json()

    async def upload_file(self, user_id: str, file_content: bytes, filename: str) -> Dict[str, Any]:
        """为指定用户上传文件。"""
        url = f"/api/v1/users/{user_id}/files/upload"
        files = {'file': (filename, file_content)}
        response = await self._make_request("POST", url, files=files)
        return response.json()

    async def create_task(self, user_id: str, style_id: str, image_url: str) -> Dict[str, Any]:
        """为指定用户创建转换任务。"""
        url = f"/api/v1/users/{user_id}/tasks"
        json_data = {"style_id": style_id, "image_url": image_url}
        response = await self._make_request("POST", url, json=json_data)
        return response.json()

    async def get_task_status(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """获取指定用户的任务状态。"""
        url = f"/api/v1/users/{user_id}/tasks/{task_id}"
        response = await self._make_request("GET", url)
        return response.json()

    async def get_task_result(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """获取指定用户的任务结果。"""
        url = f"/api/v1/users/{user_id}/tasks/{task_id}/result"
        response = await self._make_request("GET", url)
        return response.json()

    async def close(self):
        """关闭HTTP客户端。"""
        await self.client.aclose()

# 全局客户端实例
comfyui_client = ComfyUIClient()

async def main():
    """简单的测试函数，演示如何使用简化后的客户端。"""
    print("Testing Simplified ComfyUI Client...")
    try:
        user_id = "test-web-user-01"
        
        # 1. List styles
        print("\nListing available styles...")
        styles = await comfyui_client.list_styles()
        print(f"Found {len(styles)} styles")
        if styles:
            print(f"First style: {styles[0]}")
        
        print("\nClient test successful!")
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await comfyui_client.close()

if __name__ == "__main__":
    # 要运行此测试，请确保简化的 comfyui_workflow_server 正在运行
    asyncio.run(main()) 