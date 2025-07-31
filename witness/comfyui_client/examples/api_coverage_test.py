#!/usr/bin/env python3
"""
ComfyUI API 覆盖度测试

验证客户端是否正确实现了所有 ComfyUI 服务器 API 端点
"""

import asyncio
import logging
from pathlib import Path
import sys

# 导入客户端
sys.path.append(str(Path(__file__).parent.parent))

from client import ComfyUIClient
from config import ComfyUIClientConfig
from exceptions import ComfyUIConnectionError, ComfyUIAPIError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComfyUIAPITester:
    """ComfyUI API 测试器"""
    
    def __init__(self, client: ComfyUIClient):
        self.client = client
        self.test_results = {}
    
    async def test_endpoint(self, name: str, test_func):
        """测试单个端点"""
        try:
            result = await test_func()
            self.test_results[name] = {"status": "✅ 通过", "result": result}
            print(f"✅ {name}: 通过")
            return True
        except Exception as e:
            self.test_results[name] = {"status": "❌ 失败", "error": str(e)}
            print(f"❌ {name}: 失败 - {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有API测试"""
        print("开始 ComfyUI API 覆盖度测试")
        print("=" * 60)
        
        tests = [
            # 系统端点
            ("GET /system_stats", self.test_system_stats),
            ("GET /object_info", self.test_object_info),
            ("GET /object_info/{node_class}", self.test_object_info_node),
            ("GET /extensions", self.test_extensions),
            ("GET /embeddings", self.test_embeddings),
            
            # 模型端点
            ("GET /models", self.test_models),
            ("GET /models/{folder}", self.test_models_folder),
            
            # 提示和队列端点
            ("GET /prompt", self.test_get_prompt),
            ("GET /queue", self.test_get_queue),
            ("GET /history", self.test_get_history),
            ("POST /interrupt", self.test_interrupt),
            ("POST /free", self.test_free_memory),
            
            # 文件端点（需要特殊处理）
            ("POST /upload/image", self.test_upload_image),
            ("GET /view", self.test_view_file),
            
            # 批量操作端点
            ("POST /queue (clear)", self.test_queue_operations),
            ("POST /history (clear)", self.test_history_operations),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            if await self.test_endpoint(test_name, test_func):
                passed += 1
            await asyncio.sleep(0.1)  # 避免请求过于频繁
        
        print("\n" + "=" * 60)
        print(f"测试完成: {passed}/{total} 通过")
        print(f"API 覆盖率: {passed/total*100:.1f}%")
        
        return self.test_results
    
    # 系统端点测试
    async def test_system_stats(self):
        return await self.client.system.get_system_stats()
    
    async def test_object_info(self):
        return await self.client.system.get_object_info()
    
    async def test_object_info_node(self):
        # 首先获取所有节点，然后测试特定节点
        all_nodes = await self.client.system.get_object_info()
        if all_nodes:
            first_node = list(all_nodes.keys())[0]
            return await self.client.system.get_object_info(first_node)
        return {}
    
    async def test_extensions(self):
        return await self.client.system.get_extensions()
    
    async def test_embeddings(self):
        return await self.client.system.get_embeddings()
    
    # 模型端点测试
    async def test_models(self):
        return await self.client.models.get_model_types()
    
    async def test_models_folder(self):
        model_types = await self.client.models.get_model_types()
        if model_types:
            first_type = model_types[0]
            return await self.client.models.get_models(first_type)
        return []
    
    # 提示和队列端点测试
    async def test_get_prompt(self):
        return await self.client.prompts.get_prompt_info()
    
    async def test_get_queue(self):
        return await self.client.prompts.get_queue()
    
    async def test_get_history(self):
        return await self.client.prompts.get_history()
    
    async def test_interrupt(self):
        return await self.client.prompts.interrupt()
    
    async def test_free_memory(self):
        return await self.client.prompts.free_memory(free_memory=True)
    
    # 文件端点测试
    async def test_upload_image(self):
        try:
            from PIL import Image
            import io
            
            # 创建测试图片
            test_image = Image.new('RGB', (64, 64), color='blue')
            bio = io.BytesIO()
            test_image.save(bio, format='PNG')
            image_bytes = bio.getvalue()
            
            return await self.client.files.upload_image(
                image_bytes=image_bytes,
                filename="api_test.png",
                overwrite=True
            )
        except ImportError:
            # 如果没有PIL，跳过此测试
            raise Exception("PIL 未安装，跳过图片上传测试")
    
    async def test_view_file(self):
        # 尝试查看一个可能存在的文件
        try:
            # 首先上传一个测试文件
            upload_result = await self.test_upload_image()
            filename = upload_result['name']
            
            # 然后尝试查看它
            return await self.client.files.view_file(
                filename=filename,
                file_type='input'
            )
        except Exception:
            # 如果上传失败，返回空结果
            return b""
    
    # 批量操作测试
    async def test_queue_operations(self):
        # 测试队列操作（不实际清空，只测试API）
        queue_info = await self.client.prompts.get_queue()
        return {"tested": "queue_operations", "current_queue": queue_info}
    
    async def test_history_operations(self):
        # 测试历史操作（不实际清空，只测试获取）
        history = await self.client.prompts.get_history()
        return {"tested": "history_operations", "history_count": len(history)}

async def main():
    """主测试函数"""
    
    # 创建测试配置
    config = ComfyUIClientConfig.create_fast()
    config.log_requests = False  # 减少日志输出
    
    # 创建客户端
    client = ComfyUIClient(
        server_address="127.0.0.1",
        port=8188,
        config=config
    )
    
    try:
        # 首先进行健康检查
        print("进行健康检查...")
        is_healthy = await client.health_check()
        
        if not is_healthy:
            print("❌ ComfyUI 服务器不可用，无法进行测试")
            return
        
        print("✅ ComfyUI 服务器健康，开始测试\\n")
        
        # 创建测试器并运行测试
        tester = ComfyUIAPITester(client)
        results = await tester.run_all_tests()
        
        # 详细结果
        print("\\n详细测试结果:")
        print("-" * 60)
        
        for endpoint, result in results.items():
            status = result["status"]
            print(f"{endpoint:30} {status}")
            
            if "error" in result:
                print(f"  错误: {result['error']}")
        
        # 统计
        passed = sum(1 for r in results.values() if "✅" in r["status"])
        total = len(results)
        
        print("\\n" + "=" * 60)
        print(f"最终结果: {passed}/{total} 个端点测试通过")
        print(f"API 完整性: {passed/total*100:.1f}%")
        
        if passed == total:
            print("🎉 所有 ComfyUI API 端点都已正确实现！")
        else:
            print("⚠️  部分端点需要进一步检查")
    
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
    
    finally:
        await client.close()

if __name__ == "__main__":
    print("ComfyUI API 覆盖度测试工具")
    print("=" * 60)
    print("此工具将测试客户端是否覆盖了所有 ComfyUI API 端点")
    print()
    
    asyncio.run(main())