"""
多用户API使用示例

展示如何使用多用户风格转换API的完整示例
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiUserAPIClient:
    """多用户API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self, user_id: str) -> Dict[str, str]:
        """获取用户请求头"""
        return {
            "x-user-id": user_id,
            "Content-Type": "application/json"
        }
    
    async def get_styles(self, user_id: str) -> List[Dict]:
        """获取风格列表"""
        url = f"{self.base_url}/api/v1/styles/"
        headers = self._get_headers(user_id)
        
        async with self.session.get(url, headers=headers) as response:
            result = await response.json()
            if result.get("success"):
                return result.get("data", [])
            else:
                raise Exception(f"获取风格失败: {result.get('error')}")
    
    async def upload_image(self, user_id: str, image_path: str) -> Dict:
        """上传图片"""
        url = f"{self.base_url}/api/v1/files/upload"
        headers = {"x-user-id": user_id}
        
        with open(image_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=Path(image_path).name)
            
            async with self.session.post(url, data=data, headers=headers) as response:
                result = await response.json()
                if result.get("success"):
                    return result.get("data", {})
                else:
                    raise Exception(f"上传图片失败: {result.get('error')}")
    
    async def transform_style(self, user_id: str, style_id: str, image_url: str) -> Dict:
        """执行风格转换"""
        url = f"{self.base_url}/api/v1/styles/transform"
        headers = self._get_headers(user_id)
        payload = {
            "style_id": style_id,
            "image_url": image_url
        }
        
        async with self.session.post(url, json=payload, headers=headers) as response:
            result = await response.json()
            if result.get("success"):
                return result
            else:
                raise Exception(f"风格转换失败: {result.get('error')}")
    
    async def get_task_status(self, user_id: str, request_id: str) -> Dict:
        """获取任务状态"""
        url = f"{self.base_url}/api/v1/tasks/{request_id}"
        headers = self._get_headers(user_id)
        
        async with self.session.get(url, headers=headers) as response:
            result = await response.json()
            if result.get("success"):
                return result.get("data", {})
            else:
                raise Exception(f"获取任务状态失败: {result.get('error')}")
    
    async def get_task_result(self, user_id: str, request_id: str) -> Dict:
        """获取任务结果"""
        url = f"{self.base_url}/api/v1/tasks/{request_id}/result"
        headers = self._get_headers(user_id)
        
        async with self.session.get(url, headers=headers) as response:
            result = await response.json()
            if result.get("success"):
                return result.get("data", {})
            else:
                raise Exception(f"获取任务结果失败: {result.get('error')}")
    
    async def list_user_tasks(self, user_id: str, limit: int = 10) -> List[Dict]:
        """列出用户任务"""
        url = f"{self.base_url}/api/v1/tasks/"
        headers = self._get_headers(user_id)
        params = {"limit": limit}
        
        async with self.session.get(url, headers=headers, params=params) as response:
            result = await response.json()
            if result.get("success"):
                return result.get("tasks", [])
            else:
                raise Exception(f"获取任务列表失败: {result.get('error')}")
    
    async def list_user_files(self, user_id: str, limit: int = 10) -> List[Dict]:
        """列出用户文件"""
        url = f"{self.base_url}/api/v1/files/"
        headers = self._get_headers(user_id)
        params = {"limit": limit}
        
        async with self.session.get(url, headers=headers, params=params) as response:
            result = await response.json()
            if result.get("success"):
                return result.get("files", [])
            else:
                raise Exception(f"获取文件列表失败: {result.get('error')}")
    
    async def get_user_stats(self, user_id: str) -> Dict:
        """获取用户统计信息"""
        url = f"{self.base_url}/api/v1/tasks/stats"
        headers = self._get_headers(user_id)
        
        async with self.session.get(url, headers=headers) as response:
            result = await response.json()
            if result.get("success"):
                return result.get("data", {})
            else:
                raise Exception(f"获取用户统计失败: {result.get('error')}")

async def single_user_workflow(user_id: str, image_path: str):
    """单用户工作流示例"""
    logger.info(f"开始用户 {user_id} 的工作流")
    
    async with MultiUserAPIClient() as client:
        try:
            # 1. 获取可用风格
            logger.info("1. 获取可用风格...")
            styles = await client.get_styles(user_id)
            logger.info(f"可用风格: {[s['id'] for s in styles]}")
            
            if not styles:
                logger.error("没有可用的风格")
                return
            
            # 2. 上传图片
            logger.info("2. 上传图片...")
            upload_result = await client.upload_image(user_id, image_path)
            logger.info(f"上传成功: {upload_result['file_id']}")
            
            # 3. 选择风格进行转换
            style_id = styles[0]['id']  # 使用第一个风格
            logger.info(f"3. 开始风格转换: {style_id}")
            
            transform_result = await client.transform_style(
                user_id, 
                style_id, 
                upload_result['url']
            )
            request_id = transform_result['request_id']
            logger.info(f"任务创建成功: {request_id}")
            
            # 4. 轮询任务状态
            logger.info("4. 等待任务完成...")
            while True:
                status = await client.get_task_status(user_id, request_id)
                logger.info(f"任务状态: {status['status']} ({status['progress']}%)")
                
                if status['status'] == 'completed':
                    logger.info("任务完成！")
                    break
                elif status['status'] == 'failed':
                    logger.error(f"任务失败: {status.get('error_message')}")
                    return
                
                await asyncio.sleep(2)
            
            # 5. 获取任务结果
            logger.info("5. 获取任务结果...")
            result = await client.get_task_result(user_id, request_id)
            logger.info(f"转换完成: {result}")
            
            # 6. 获取用户统计
            logger.info("6. 获取用户统计...")
            stats = await client.get_user_stats(user_id)
            logger.info(f"用户统计: {stats}")
            
        except Exception as e:
            logger.error(f"用户 {user_id} 工作流失败: {e}")

async def multi_user_concurrent_workflow():
    """多用户并发工作流示例"""
    logger.info("开始多用户并发工作流")
    
    # 模拟多个用户
    users = [
        {"user_id": "user_001", "image": "test_image_1.jpg"},
        {"user_id": "user_002", "image": "test_image_2.jpg"},
        {"user_id": "user_003", "image": "test_image_3.jpg"},
    ]
    
    # 并发执行所有用户的工作流
    tasks = []
    for user in users:
        task = asyncio.create_task(
            single_user_workflow(user["user_id"], user["image"])
        )
        tasks.append(task)
    
    # 等待所有任务完成
    await asyncio.gather(*tasks)
    logger.info("所有用户工作流完成")

async def demonstrate_user_isolation():
    """演示用户隔离功能"""
    logger.info("演示用户隔离功能")
    
    async with MultiUserAPIClient() as client:
        try:
            # 用户A的任务
            user_a_tasks = await client.list_user_tasks("user_001")
            logger.info(f"用户A的任务数: {len(user_a_tasks)}")
            
            # 用户B的任务
            user_b_tasks = await client.list_user_tasks("user_002")
            logger.info(f"用户B的任务数: {len(user_b_tasks)}")
            
            # 用户C的任务
            user_c_tasks = await client.list_user_tasks("user_003")
            logger.info(f"用户C的任务数: {len(user_c_tasks)}")
            
            # 验证用户只能看到自己的任务
            if user_a_tasks:
                for task in user_a_tasks:
                    assert task['user_id'] == 'user_001', "用户A看到了其他用户的任务！"
            
            if user_b_tasks:
                for task in user_b_tasks:
                    assert task['user_id'] == 'user_002', "用户B看到了其他用户的任务！"
            
            if user_c_tasks:
                for task in user_c_tasks:
                    assert task['user_id'] == 'user_003', "用户C看到了其他用户的任务！"
            
            logger.info("✅ 用户隔离验证通过")
            
        except Exception as e:
            logger.error(f"用户隔离验证失败: {e}")

async def main():
    """主函数"""
    logger.info("开始多用户API示例")
    
    # 检查测试图片是否存在
    test_images = ["test_image_1.jpg", "test_image_2.jpg", "test_image_3.jpg"]
    for img in test_images:
        if not Path(img).exists():
            logger.warning(f"测试图片 {img} 不存在，将跳过相关测试")
    
    try:
        # 1. 单用户工作流
        if Path("test_image_1.jpg").exists():
            await single_user_workflow("user_001", "test_image_1.jpg")
        
        # 2. 多用户并发工作流
        # await multi_user_concurrent_workflow()
        
        # 3. 演示用户隔离
        await demonstrate_user_isolation()
        
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
    
    logger.info("多用户API示例完成")

if __name__ == "__main__":
    asyncio.run(main()) 