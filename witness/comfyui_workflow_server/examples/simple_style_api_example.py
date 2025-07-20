#!/usr/bin/env python3
"""
ComfyUI风格转换API客户端示例

展示如何使用极简化的风格转换API
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any, Optional

class StyleAPIClient:
    """风格转换API客户端"""
    
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
    
    async def get_styles(self) -> List[Dict[str, Any]]:
        """获取所有风格"""
        async with self.session.get(f"{self.base_url}/api/v1/styles/") as resp:
            result = await resp.json()
            return result.get("data", []) if result.get("success") else []
    
    async def get_style(self, style_id: str) -> Optional[Dict[str, Any]]:
        """获取特定风格"""
        async with self.session.get(f"{self.base_url}/api/v1/styles/{style_id}") as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("data") if result.get("success") else None
            return None
    
    async def search_styles(self, query: str) -> List[Dict[str, Any]]:
        """搜索风格"""
        async with self.session.get(f"{self.base_url}/api/v1/styles/search", params={"q": query}) as resp:
            result = await resp.json()
            return result.get("data", []) if result.get("success") else []
    
    async def transform_image(self, style_id: str, image_url: str) -> Optional[str]:
        """执行风格转换"""
        payload = {
            "style_id": style_id,
            "image_url": image_url
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/styles/transform",
            json=payload
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("request_id") if result.get("success") else None
            else:
                error_text = await resp.text()
                print(f"转换失败: {resp.status} - {error_text}")
                return None
    
    async def get_task_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        async with self.session.get(f"{self.base_url}/api/v1/tasks/{request_id}") as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("data") if result.get("success") else None
            return None
    
    async def get_task_result(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        async with self.session.get(f"{self.base_url}/api/v1/tasks/{request_id}/result") as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("data") if result.get("success") else None
            return None
    
    async def wait_for_completion(self, request_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = await self.get_task_status(request_id)
            if not status:
                print(f"❌ 获取任务状态失败: {request_id}")
                return None
            
            status_value = status.get("status", "unknown")
            progress = status.get("progress", 0)
            
            print(f"📊 任务状态: {status_value}, 进度: {progress:.1f}%")
            
            if status_value == "completed":
                print("✅ 任务完成！")
                return await self.get_task_result(request_id)
            elif status_value == "failed":
                error_msg = status.get("error_message", "未知错误")
                print(f"❌ 任务失败: {error_msg}")
                return None
            
            await asyncio.sleep(2)  # 每2秒检查一次
        
        print(f"⏰ 任务超时 ({timeout}秒)")
        return None
    
    async def upload_file(self, file_path: str) -> Optional[str]:
        """上传文件"""
        try:
            with open(file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=file_path)
                
                async with self.session.post(
                    f"{self.base_url}/api/v1/files/upload",
                    data=data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("success"):
                            return result.get("data", {}).get("url")
            return None
        except Exception as e:
            print(f"❌ 上传文件失败: {e}")
            return None

async def demo_basic_usage():
    """基本使用示例"""
    print("🎨 ComfyUI风格转换API使用示例")
    print("=" * 50)
    
    # 示例图片URL（请替换为实际的图片URL）
    test_image_url = "https://example.com/test-image.jpg"
    
    async with StyleAPIClient() as client:
        try:
            # 1. 健康检查
            print("1. 健康检查...")
            health = await client.health_check()
            print(f"   服务状态: {health.get('status', 'unknown')}")
            
            # 2. 获取可用风格
            print("\n2. 获取可用风格...")
            styles = await client.get_styles()
            if styles:
                print(f"   可用风格数量: {len(styles)}")
                for style in styles:
                    print(f"   - {style['id']}: {style['name']}")
                    print(f"     描述: {style['description']}")
                    print(f"     预估时间: {style['estimated_time']}秒")
                    print()
                
                # 3. 选择第一个风格进行转换
                if styles:
                    selected_style = styles[0]
                    print(f"3. 执行风格转换 ({selected_style['name']})...")
                    
                    request_id = await client.transform_image(
                        selected_style['id'], 
                        test_image_url
                    )
                    
                    if request_id:
                        print(f"   请求ID: {request_id}")
                        
                        # 4. 等待完成
                        print("\n4. 等待任务完成...")
                        result = await client.wait_for_completion(request_id)
                        
                        if result:
                            print(f"🎉 转换成功！")
                            print(f"   处理耗时: {result.get('duration', 0):.2f}秒")
                            print(f"   应用风格: {result.get('style_applied', 'N/A')}")
                            
                            # 显示输出图片信息
                            output_images = result.get('output_images', [])
                            if output_images:
                                print(f"   生成图片数量: {len(output_images)}")
                                for i, img in enumerate(output_images, 1):
                                    print(f"     图片{i}: {img.get('filename', 'N/A')}")
                                    print(f"     URL: {img.get('url', 'N/A')}")
                                    print(f"     大小: {img.get('size', 0)} bytes")
                        else:
                            print("❌ 转换失败")
                    else:
                        print("❌ 提交任务失败")
            else:
                print("   ❌ 没有可用的风格")
                
        except Exception as e:
            print(f"❌ 错误: {e}")

async def demo_search_styles():
    """风格搜索示例"""
    print("\n🔍 风格搜索示例")
    print("=" * 50)
    
    async with StyleAPIClient() as client:
        try:
            # 搜索包含"风格"的风格
            search_query = "风格"
            print(f"搜索关键词: {search_query}")
            
            styles = await client.search_styles(search_query)
            if styles:
                print(f"找到 {len(styles)} 个匹配的风格:")
                for style in styles:
                    print(f"- {style['id']}: {style['name']}")
                    print(f"  标签: {', '.join(style.get('tags', []))}")
            else:
                print("未找到匹配的风格")
                
        except Exception as e:
            print(f"❌ 错误: {e}")

async def demo_multiple_styles():
    """多风格并行转换示例"""
    print("\n⚡ 多风格并行转换示例")
    print("=" * 50)
    
    test_image_url = "https://example.com/test-image.jpg"
    
    async with StyleAPIClient() as client:
        try:
            # 获取所有风格
            styles = await client.get_styles()
            if len(styles) >= 2:
                # 选择前两个风格进行并行转换
                selected_styles = styles[:2]
                
                print(f"同时转换 {len(selected_styles)} 种风格...")
                
                # 并行提交任务
                tasks = []
                for style in selected_styles:
                    request_id = await client.transform_image(style['id'], test_image_url)
                    if request_id:
                        tasks.append((style['name'], request_id))
                        print(f"   已提交 {style['name']} 任务: {request_id}")
                
                # 等待所有任务完成
                print("\n等待所有任务完成...")
                results = {}
                for style_name, request_id in tasks:
                    print(f"\n等待 {style_name} 完成...")
                    result = await client.wait_for_completion(request_id)
                    results[style_name] = result
                
                # 显示结果
                print("\n📊 转换结果汇总:")
                for style_name, result in results.items():
                    if result:
                        print(f"✅ {style_name}: 成功 ({result.get('duration', 0):.2f}秒)")
                    else:
                        print(f"❌ {style_name}: 失败")
                        
            else:
                print("可用风格数量不足，跳过并行转换示例")
                
        except Exception as e:
            print(f"❌ 错误: {e}")

async def main():
    """主函数"""
    print("🚀 ComfyUI风格转换API客户端示例")
    print("=" * 50)
    
    # 基本使用
    await demo_basic_usage()
    
    # 风格搜索
    await demo_search_styles()
    
    # 多风格并行转换
    await demo_multiple_styles()
    
    print("\n✨ 示例完成！")

if __name__ == "__main__":
    asyncio.run(main()) 