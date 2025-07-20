#!/usr/bin/env python3
"""
ComfyUI工作流服务器API使用示例

展示如何使用新的工作流API进行图像风格变换和其他AI处理任务。
"""

import asyncio
import aiohttp
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional


class WorkflowAPIClient:
    """工作流API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_available_workflows(self) -> list:
        """获取可用的工作流列表"""
        async with self.session.get(f"{self.base_url}/api/v1/workflows/") as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", [])
            else:
                raise Exception(f"获取工作流列表失败: {response.status}")
    
    async def get_workflow_metadata(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流元数据"""
        async with self.session.get(f"{self.base_url}/api/v1/workflows/{workflow_id}") as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", {})
            else:
                raise Exception(f"获取工作流元数据失败: {response.status}")
    
    async def execute_workflow(self, workflow_id: str, parameters: Dict[str, Any]) -> str:
        """执行工作流"""
        payload = {
            "workflow_id": workflow_id,
            "parameters": parameters
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/workflows/{workflow_id}/execute",
            json=payload
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data")  # 返回request_id
            else:
                error_text = await response.text()
                raise Exception(f"执行工作流失败: {response.status} - {error_text}")
    
    async def get_task_status(self, request_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        async with self.session.get(f"{self.base_url}/api/v1/workflows/tasks/{request_id}") as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", {})
            else:
                raise Exception(f"获取任务状态失败: {response.status}")
    
    async def get_task_result(self, request_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        async with self.session.get(f"{self.base_url}/api/v1/workflows/tasks/{request_id}/result") as response:
            if response.status == 200:
                data = await response.json()
                return data.get("data", {})
            else:
                raise Exception(f"获取任务结果失败: {response.status}")
    
    async def wait_for_completion(self, request_id: str, timeout: int = 300) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status_data = await self.get_task_status(request_id)
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            
            print(f"任务 {request_id}: {status} ({progress:.1%})")
            
            if status == "completed":
                result = await self.get_task_result(request_id)
                return result
            elif status == "failed":
                error_msg = status_data.get("error_message", "未知错误")
                raise Exception(f"任务执行失败: {error_msg}")
            
            await asyncio.sleep(2)
        
        raise Exception("任务执行超时")


async def demo_clay_style_transform():
    """演示黏土风格转换工作流"""
    print("=== 黏土风格转换工作流演示 ===")
    
    async with WorkflowAPIClient() as client:
        # 1. 获取可用工作流
        print("1. 获取可用工作流...")
        workflows = await client.get_available_workflows()
        print(f"可用工作流: {workflows}")
        
        # 2. 获取clay_style_transform工作流的元数据
        print("\n2. 获取clay_style_transform工作流元数据...")
        metadata = await client.get_workflow_metadata("clay_style_transform")
        print(f"工作流名称: {metadata.get('name')}")
        print(f"描述: {metadata.get('description')}")
        print(f"参数: {json.dumps(metadata.get('parameter_schema', {}), indent=2, ensure_ascii=False)}")
        
        # 3. 执行黏土风格转换
        print("\n3. 执行黏土风格转换工作流...")
        parameters = {
            "image_url": "https://example.com/test-image.jpg"  # 这里应该是实际的图像URL
        }
        
        request_id = await client.execute_workflow("clay_style_transform", parameters)
        print(f"任务已提交，任务ID: {request_id}")
        
        # 4. 等待完成
        print("\n4. 等待任务完成...")
        try:
            result = await client.wait_for_completion(request_id)
            print(f"任务完成! 结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"任务失败: {e}")


async def demo_workflow_discovery():
    """演示工作流发现功能"""
    print("=== 工作流发现演示 ===")
    
    async with WorkflowAPIClient() as client:
        # 获取所有工作流
        workflows = await client.get_available_workflows()
        
        for workflow_id in workflows:
            print(f"\n--- 工作流: {workflow_id} ---")
            try:
                metadata = await client.get_workflow_metadata(workflow_id)
                print(f"名称: {metadata.get('name')}")
                print(f"类型: {metadata.get('workflow_type')}")
                print(f"描述: {metadata.get('description')}")
                print(f"输入类型: {metadata.get('input_types')}")
                print(f"输出类型: {metadata.get('output_types')}")
                print(f"预估时间: {metadata.get('estimated_time')}秒")
                print(f"需要GPU: {metadata.get('gpu_required')}")
                print(f"标签: {metadata.get('tags')}")
            except Exception as e:
                print(f"获取元数据失败: {e}")


async def demo_api_monitoring():
    """演示API监控功能"""
    print("=== API监控演示 ===")
    
    async with WorkflowAPIClient() as client:
        # 获取统计信息
        async with client.session.get(f"{client.base_url}/api/v1/workflows/statistics") as response:
            if response.status == 200:
                data = await response.json()
                stats = data.get("data", {})
                print("系统统计信息:")
                print(f"  总任务数: {stats.get('total_tasks', 0)}")
                print(f"  运行中任务: {stats.get('running_tasks', 0)}")
                print(f"  平均执行时间: {stats.get('average_duration', 0):.2f}秒")
                print(f"  最大并发数: {stats.get('max_concurrent_tasks', 0)}")
                
                status_counts = stats.get('status_counts', {})
                print("任务状态分布:")
                for status, count in status_counts.items():
                    print(f"  {status}: {count}")
            else:
                print("获取统计信息失败")
        
        # 获取健康状态
        async with client.session.get(f"{client.base_url}/health") as response:
            if response.status == 200:
                health = await response.json()
                print(f"\n服务健康状态: {health.get('status')}")
                print(f"ComfyUI连接: {health.get('comfyui_connected')}")
            else:
                print("获取健康状态失败")


async def demo_parameter_validation():
    """演示参数验证功能"""
    print("=== 参数验证演示 ===")
    
    async with WorkflowAPIClient() as client:
        # 获取参数Schema
        async with client.session.get(f"{client.base_url}/api/v1/workflows/clay_style_transform/schema") as response:
            if response.status == 200:
                data = await response.json()
                schema = data.get("data", {})
                print("参数Schema:")
                print(json.dumps(schema, indent=2, ensure_ascii=False))
            else:
                print("获取参数Schema失败")
        
        # 测试无效参数
        print("\n测试无效参数...")
        invalid_parameters = {
            "image_url": "",  # 空字符串，应该失败
        }
        
        try:
            request_id = await client.execute_workflow("clay_style_transform", invalid_parameters)
            print(f"意外成功: {request_id}")
        except Exception as e:
            print(f"验证失败（预期）: {e}")


async def main():
    """主函数"""
    print("ComfyUI工作流服务器API演示")
    print("=" * 50)
    
    demos = [
        ("工作流发现", demo_workflow_discovery),
        ("参数验证", demo_parameter_validation),
        ("API监控", demo_api_monitoring),
        # ("黏土风格转换", demo_clay_style_transform),  # 需要实际图像URL才能运行
    ]
    
    for name, demo_func in demos:
        print(f"\n{'=' * 20} {name} {'=' * 20}")
        try:
            await demo_func()
        except Exception as e:
            print(f"演示失败: {e}")
        
        print("\n" + "=" * (40 + len(name)))
        await asyncio.sleep(1)  # 短暂延迟


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n演示已中断")
    except Exception as e:
        print(f"\n演示运行失败: {e}") 