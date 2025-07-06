#!/usr/bin/env python3
"""
动漫风格转换API使用示例

演示如何使用ComfyUI工作流服务器的动漫风格转换功能。
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

class AnimeStyleAPIClient:
    """动漫风格转换API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        async with self.session.get(f"{self.base_url}/health") as resp:
            return await resp.json()
    
    async def list_workflows(self) -> Dict[str, Any]:
        """列出所有工作流"""
        async with self.session.get(f"{self.base_url}/api/v1/workflows/") as resp:
            return await resp.json()
    
    async def get_workflow_info(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流信息"""
        async with self.session.get(f"{self.base_url}/api/v1/workflows/{workflow_id}") as resp:
            return await resp.json()
    
    async def execute_anime_style_transform(self, image_url: str) -> str:
        """执行动漫风格转换"""
        payload = {
            "workflow_id": "anime_style_transform",
            "parameters": {
                "image_url": image_url
            }
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/workflows/anime_style_transform/execute",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"API调用失败: {resp.status}, {error_text}")
            
            result = await resp.json()
            if not result.get("success"):
                raise Exception(f"执行失败: {result}")
            
            return result["data"]  # 返回task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        async with self.session.get(f"{self.base_url}/api/v1/workflows/tasks/{task_id}") as resp:
            return await resp.json()
    
    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        async with self.session.get(f"{self.base_url}/api/v1/workflows/tasks/{task_id}/result") as resp:
            return await resp.json()
    
    async def wait_for_completion(self, task_id: str, timeout: int = 300) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status_response = await self.get_task_status(task_id)
            
            if not status_response.get("success"):
                raise Exception(f"获取任务状态失败: {status_response}")
            
            task_data = status_response["data"]
            status = task_data["status"]
            progress = task_data.get("progress", 0)
            
            print(f"任务状态: {status}, 进度: {progress:.1%}")
            
            if status == "completed":
                print("任务完成！")
                return await self.get_task_result(task_id)
            elif status == "failed":
                error_msg = task_data.get("error_message", "未知错误")
                raise Exception(f"任务失败: {error_msg}")
            elif status == "cancelled":
                raise Exception("任务被取消")
            
            await asyncio.sleep(2)  # 每2秒检查一次
        
        raise Exception(f"任务超时 ({timeout}秒)")

async def main():
    """主函数"""
    # 示例图片URL（请替换为实际的图片URL）
    test_image_url = "https://example.com/test-image.jpg"
    
    print("🎌 动漫风格转换API示例")
    print("=" * 50)
    
    async with AnimeStyleAPIClient() as client:
        try:
            # 1. 健康检查
            print("1. 检查服务健康状态...")
            health = await client.health_check()
            print(f"   服务状态: {health.get('status', 'unknown')}")
            print(f"   ComfyUI连接: {health.get('comfyui_connected', False)}")
            
            # 2. 列出工作流
            print("\n2. 获取可用工作流...")
            workflows = await client.list_workflows()
            if workflows.get("success"):
                available_workflows = workflows["data"]
                print(f"   可用工作流: {', '.join(available_workflows)}")
                
                if "anime_style_transform" not in available_workflows:
                    print("   ❌ 动漫风格转换工作流不可用")
                    return
            else:
                print(f"   ❌ 获取工作流列表失败: {workflows}")
                return
            
            # 3. 获取工作流详情
            print("\n3. 获取动漫风格转换工作流详情...")
            workflow_info = await client.get_workflow_info("anime_style_transform")
            if workflow_info.get("success"):
                info = workflow_info["data"]
                print(f"   名称: {info['name']}")
                print(f"   描述: {info['description']}")
                print(f"   版本: {info['version']}")
                print(f"   预估时间: {info.get('estimated_time', 'N/A')} 秒")
                print(f"   标签: {', '.join(info.get('tags', []))}")
            
            # 4. 执行动漫风格转换
            print(f"\n4. 执行动漫风格转换...")
            print(f"   输入图片: {test_image_url}")
            
            task_id = await client.execute_anime_style_transform(test_image_url)
            print(f"   任务ID: {task_id}")
            
            # 5. 等待完成
            print("\n5. 等待任务完成...")
            result = await client.wait_for_completion(task_id)
            
            if result.get("success"):
                task_result = result["data"]["result"]
                if task_result and "output_images" in task_result:
                    print(f"\n✅ 转换成功！")
                    print(f"   生成图片数量: {len(task_result['output_images'])}")
                    print(f"   风格类型: {task_result['metadata']['style']}")
                    
                    for i, img in enumerate(task_result["output_images"], 1):
                        print(f"   图片 {i}:")
                        print(f"     文件名: {img['filename']}")
                        print(f"     访问URL: {img['url']}")
                        print(f"     类型: {img['type']}")
                else:
                    print("   ❌ 未生成输出图片")
            else:
                print(f"   ❌ 获取结果失败: {result}")
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")

async def compare_styles():
    """比较黏土风格和动漫风格"""
    test_image_url = "https://example.com/test-image.jpg"
    
    print("\n🔄 风格对比示例")
    print("=" * 50)
    
    async with AnimeStyleAPIClient() as client:
        try:
            print("同时执行黏土风格和动漫风格转换...")
            
            # 并行执行两种风格转换
            clay_payload = {
                "workflow_id": "clay_style_transform",
                "parameters": {"image_url": test_image_url}
            }
            
            anime_payload = {
                "workflow_id": "anime_style_transform", 
                "parameters": {"image_url": test_image_url}
            }
            
            # 并行提交任务
            clay_task_response = await client.session.post(
                f"{client.base_url}/api/v1/workflows/clay_style_transform/execute",
                json=clay_payload
            )
            
            anime_task_response = await client.session.post(
                f"{client.base_url}/api/v1/workflows/anime_style_transform/execute",
                json=anime_payload
            )
            
            clay_result = await clay_task_response.json()
            anime_result = await anime_task_response.json()
            
            if clay_result.get("success") and anime_result.get("success"):
                clay_task_id = clay_result["data"]
                anime_task_id = anime_result["data"]
                
                print(f"黏土风格任务ID: {clay_task_id}")
                print(f"动漫风格任务ID: {anime_task_id}")
                
                # 等待两个任务完成
                print("\n等待两个风格转换完成...")
                clay_final = await client.wait_for_completion(clay_task_id, timeout=300)
                anime_final = await client.wait_for_completion(anime_task_id, timeout=300)
                
                print("\n🎨 转换结果对比:")
                print("黏土风格:", "✅成功" if clay_final.get("success") else "❌失败")
                print("动漫风格:", "✅成功" if anime_final.get("success") else "❌失败")
                
            else:
                print("任务提交失败")
                
        except Exception as e:
            print(f"风格对比失败: {e}")

if __name__ == "__main__":
    print("动漫风格转换API使用说明:")
    print("1. 确保ComfyUI工作流服务器运行在 http://localhost:8000")
    print("2. 修改 test_image_url 变量为实际的图片URL")
    print("3. 运行此脚本")
    print()
    
    # 运行示例
    asyncio.run(main())
    
    # 可选：运行风格对比示例
    # asyncio.run(compare_styles()) 