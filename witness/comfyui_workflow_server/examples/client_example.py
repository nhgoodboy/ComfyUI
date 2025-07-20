#!/usr/bin/env python3
"""
ComfyUI工作流服务器客户端使用示例

演示如何调用API进行图像风格变换。
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

class StyleTransformClient:
    """ComfyUI工作流服务器客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "StyleTransformClient/1.0.0"
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            
        return headers
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30
            )
            
            timeout = aiohttp.ClientTimeout(
                total=120,
                connect=10,
                sock_read=60
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._get_headers()
            )
            
        return self.session
    
    async def close(self):
        """关闭客户端连接"""
        if self.session:
            await self.session.close()
            self.session = None
        
    async def transform_image(self, user_id: str, image_url: str, 
                            style_type: str = "clay", 
                            custom_prompt: str = None,
                            strength: float = 0.6) -> Dict[str, Any]:
        """单张图像变换"""
        url = f"{self.base_url}/api/v1/transform"
        
        payload = {
            "user_id": user_id,
            "image_url": image_url,
            "style_type": style_type,
            "strength": strength
        }
        
        if custom_prompt:
            payload["custom_prompt"] = custom_prompt
            
        session = await self._get_session()
        async with session.post(url, json=payload) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(f"API请求失败: {response.status} - {result}")
            return result
    
    async def transform_batch(self, user_id: str, image_urls: list,
                            style_type: str = "clay",
                            custom_prompt: str = None,
                            strength: float = 0.6) -> Dict[str, Any]:
        """批量图像变换"""
        url = f"{self.base_url}/api/v1/transform/batch"
        
        payload = {
            "user_id": user_id,
            "image_urls": image_urls,
            "style_type": style_type,
            "strength": strength
        }
        
        if custom_prompt:
            payload["custom_prompt"] = custom_prompt
            
        session = await self._get_session()
        async with session.post(url, json=payload) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(f"API请求失败: {response.status} - {result}")
            return result
    
    async def get_task_status(self, request_id: str) -> Dict[str, Any]:
        """查询任务状态"""
        url = f"{self.base_url}/api/v1/task/{request_id}"
        
        session = await self._get_session()
        async with session.get(url) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(f"API请求失败: {response.status} - {result}")
            return result
    
    async def get_user_tasks(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """获取用户任务列表"""
        url = f"{self.base_url}/api/v1/user/{user_id}/tasks?limit={limit}"
        
        session = await self._get_session()
        async with session.get(url) as response:
            result = await response.json()
            if response.status != 200:
                raise Exception(f"API请求失败: {response.status} - {result}")
            return result
    
    async def wait_for_completion(self, request_id: str, timeout: int = 300) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = await self.get_task_status(request_id)
            status = result.get("status")
            
            if status == "completed":
                return result
            elif status == "failed":
                raise Exception(f"任务失败: {result.get('error_message')}")
            
            print(f"任务 {request_id} 状态: {status}, 进度: {result.get('progress', 0)}%")
            await asyncio.sleep(2)
        
        raise TimeoutError(f"任务 {request_id} 超时")

async def main():
    """主函数示例"""
    # 创建客户端（如果有API密钥，请传入）
    # client = StyleTransformClient(api_key="your-api-key-here")
    client = StyleTransformClient()
    
    try:
        # 示例1: 单张图像变换
        print("=== 单张图像变换示例 ===")
        
        # 提交任务
        # 提交任务
        result = await client.transform_image(
            user_id="demo_user_001",
            image_url="https://example.com/sample.jpg",
            style_type="clay",
            custom_prompt="Clay Style, lovely, 3d, cute, high quality",
            strength=0.7
        )
        
        print(f"任务创建成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("success"):
            request_id = result["request_id"]
            
            # 等待完成
            print(f"等待任务 {request_id} 完成...")
            final_result = await client.wait_for_completion(request_id)
            
            print(f"任务完成: {json.dumps(final_result, indent=2, ensure_ascii=False)}")
            print(f"输出图像: {final_result.get('output_image_url')}")
        
    except Exception as e:
        print(f"单张图像变换失败: {e}")
    
    # 示例2: 批量图像变换
    print("\n=== 批量图像变换示例 ===")
    
    try:
        # 提交批量任务
        batch_result = await client.transform_batch(
            user_id="demo_user_001",
            image_urls=[
                "https://example.com/sample1.jpg",
                "https://example.com/sample2.jpg"
            ],
            style_type="anime",
            strength=0.6
        )
        
        print(f"批量任务创建成功: {json.dumps(batch_result, indent=2, ensure_ascii=False)}")
        
        if batch_result.get("success"):
            # 等待所有任务完成
            for task_result in batch_result["results"]:
                request_id = task_result["request_id"]
                try:
                    final_result = await client.wait_for_completion(request_id)
                    print(f"任务 {request_id} 完成: {final_result.get('output_image_url')}")
                except Exception as e:
                    print(f"任务 {request_id} 失败: {e}")
        
    except Exception as e:
        print(f"批量图像变换失败: {e}")
    
    # 示例3: 查询用户任务历史
    print("\n=== 用户任务历史示例 ===")
    
    try:
        user_tasks = await client.get_user_tasks("demo_user_001", limit=10)
        print(f"用户任务历史: {json.dumps(user_tasks, indent=2, ensure_ascii=False)}")
        
        except Exception as e:
            print(f"查询用户任务失败: {e}")
    
    finally:
        # 确保关闭客户端连接
        await client.close()
        print("\n客户端连接已关闭")

if __name__ == "__main__":
    # 运行示例
    print("ComfyUI工作流服务器 客户端示例")
    print("支持的功能:")
    print("- 单张图像风格变换")
    print("- 批量图像风格变换") 
    print("- 任务状态查询")
    print("- 用户任务历史查询")
    print("- API密钥认证")
    print("- 连接池优化")
    print()
    
    asyncio.run(main())
 