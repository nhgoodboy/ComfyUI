#!/usr/bin/env python3
"""
通用风格转换API使用示例

演示如何使用新的配置驱动风格转换系统。
支持多种风格转换，新增风格只需添加配置。
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List

class UniversalStyleAPIClient:
    """通用风格转换API客户端"""
    
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
    
    async def execute_style_transform(self, style_id: str, image_url: str) -> str:
        """执行风格转换"""
        payload = {
            "workflow_id": style_id,
            "parameters": {
                "image_url": image_url
            }
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/workflows/{style_id}/execute",
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

async def demo_single_style_transform():
    """演示单个风格转换"""
    # 示例图片URL（请替换为实际的图片URL）
    test_image_url = "https://example.com/test-image.jpg"
    
    print("🎨 单个风格转换示例")
    print("=" * 50)
    
    async with UniversalStyleAPIClient() as client:
        try:
            # 1. 获取可用工作流
            print("1. 获取可用工作流...")
            workflows = await client.list_workflows()
            if workflows.get("success"):
                available_workflows = workflows["data"]
                print(f"   可用工作流: {', '.join(available_workflows)}")
                
                # 选择第一个风格进行测试
                if available_workflows:
                    selected_style = available_workflows[0]
                    print(f"   选择风格: {selected_style}")
                    
                    # 2. 获取工作流详情
                    print(f"\n2. 获取 {selected_style} 工作流详情...")
                                         workflow_info = await client.get_workflow_info(selected_style)
                     if workflow_info.get("success"):
                         info = workflow_info["data"]
                         print(f"   名称: {info['name']}")
                         print(f"   描述: {info['description']}")
                         print(f"   预估时间: {info.get('estimated_time', 'N/A')} 秒")
                         print(f"   标签: {', '.join(info.get('tags', []))}")
                    
                    # 3. 执行风格转换
                    print(f"\n3. 执行 {selected_style} 风格转换...")
                    print(f"   输入图片: {test_image_url}")
                    
                    task_id = await client.execute_style_transform(selected_style, test_image_url)
                    print(f"   任务ID: {task_id}")
                    
                    # 4. 等待完成
                    print("\n4. 等待任务完成...")
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
                else:
                    print("   ❌ 没有可用的工作流")
            else:
                print(f"   ❌ 获取工作流列表失败: {workflows}")
                
        except Exception as e:
            print(f"\n❌ 错误: {e}")

async def demo_multiple_styles_comparison():
    """演示多种风格对比"""
    test_image_url = "https://example.com/test-image.jpg"
    
    print("\n🔄 多种风格对比示例")
    print("=" * 50)
    
    async with UniversalStyleAPIClient() as client:
        try:
            # 1. 获取可用工作流
            workflows = await client.list_workflows()
            if not workflows.get("success"):
                print("❌ 获取工作流列表失败")
                return
            
            available_workflows = workflows["data"]
            print(f"可用风格: {', '.join(available_workflows)}")
            
            # 2. 并行执行多种风格转换
            print("\n同时执行多种风格转换...")
            
            tasks = []
            style_task_map = {}
            
            for style_id in available_workflows:
                try:
                    payload = {
                        "workflow_id": style_id,
                        "parameters": {"image_url": test_image_url}
                    }
                    
                    task_response = await client.session.post(
                        f"{client.base_url}/api/v1/workflows/{style_id}/execute",
                        json=payload
                    )
                    
                    task_result = await task_response.json()
                    
                    if task_result.get("success"):
                        task_id = task_result["data"]
                        style_task_map[style_id] = task_id
                        print(f"   {style_id} 任务ID: {task_id}")
                    else:
                        print(f"   ❌ {style_id} 任务提交失败")
                        
                except Exception as e:
                    print(f"   ❌ {style_id} 提交失败: {e}")
            
            # 3. 等待所有任务完成
            print(f"\n等待 {len(style_task_map)} 个风格转换完成...")
            
            results = {}
            for style_id, task_id in style_task_map.items():
                try:
                    print(f"\n等待 {style_id} 完成...")
                    result = await client.wait_for_completion(task_id, timeout=300)
                    results[style_id] = result
                except Exception as e:
                    print(f"   ❌ {style_id} 失败: {e}")
                    results[style_id] = None
            
            # 4. 显示结果对比
            print("\n🎨 风格转换结果对比:")
            print("-" * 50)
            
            for style_id, result in results.items():
                if result and result.get("success"):
                    task_result = result["data"]["result"]
                    if task_result and "output_images" in task_result:
                        image_count = len(task_result["output_images"])
                        style_name = task_result["metadata"]["style"]
                        print(f"✅ {style_id}: 成功生成 {image_count} 张图片 ({style_name})")
                    else:
                        print(f"⚠️  {style_id}: 任务完成但未生成图片")
                else:
                    print(f"❌ {style_id}: 失败")
                    
        except Exception as e:
            print(f"多风格对比失败: {e}")

async def demo_style_discovery():
    """演示风格发现和元数据查看"""
    print("\n🔍 风格发现示例")
    print("=" * 50)
    
    async with UniversalStyleAPIClient() as client:
        try:
            # 1. 健康检查
            print("1. 系统健康检查...")
            health = await client.health_check()
            print(f"   服务状态: {health.get('status', 'unknown')}")
            print(f"   ComfyUI连接: {health.get('comfyui_connected', False)}")
            
            # 2. 列出所有工作流
            print("\n2. 发现可用风格...")
            workflows = await client.list_workflows()
            if workflows.get("success"):
                available_workflows = workflows["data"]
                print(f"   发现 {len(available_workflows)} 种风格")
                
                # 3. 获取每种风格的详细信息
                print("\n3. 风格详细信息:")
                for i, style_id in enumerate(available_workflows, 1):
                    try:
                        info_response = await client.get_workflow_info(style_id)
                        if info_response.get("success"):
                                                         info = info_response["data"]
                             print(f"\n   {i}. {info['name']} ({style_id})")
                             print(f"      描述: {info['description']}")
                             print(f"      标签: {', '.join(info.get('tags', []))}")
                             print(f"      预估时间: {info.get('estimated_time', 'N/A')} 秒")
                        else:
                            print(f"   ❌ 获取 {style_id} 信息失败")
                    except Exception as e:
                        print(f"   ❌ 获取 {style_id} 信息出错: {e}")
            else:
                print(f"   ❌ 获取工作流列表失败: {workflows}")
                
        except Exception as e:
            print(f"风格发现失败: {e}")

async def main():
    """主函数"""
    print("🚀 通用风格转换API示例")
    print("=" * 60)
    print("新架构特点:")
    print("- 配置驱动的风格系统")
    print("- 新增风格只需添加JSON文件和配置")
    print("- 统一的API接口")
    print("- 自动工作流注册")
    print("=" * 60)
    
    # 运行各种示例
    await demo_style_discovery()
    await demo_single_style_transform()
    await demo_multiple_styles_comparison()

if __name__ == "__main__":
    print("通用风格转换API使用说明:")
    print("1. 确保ComfyUI工作流服务器运行在 http://localhost:8000")
    print("2. 确保风格配置文件已正确配置")
    print("3. 修改示例中的图片URL为实际地址")
    print("4. 运行此脚本")
    print()
    
    # 运行示例
    asyncio.run(main()) 