#!/usr/bin/env python3
"""
ComfyUI客户端高级用法示例

演示了完整的API集成，包括：
- API前缀支持
- 批量操作
- 图片处理
- 错误处理
- 异步操作
"""

import asyncio
import json
import logging
from pathlib import Path

# 导入客户端
import sys
sys.path.append(str(Path(__file__).parent.parent))

from client import ComfyUIClient
from config import ComfyUIClientConfig
from exceptions import ComfyUIConnectionError, ComfyUIAPIError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """主函数演示各种API用法"""
    
    # 创建客户端配置
    config = ComfyUIClientConfig.create_robust()
    config.log_requests = True
    
    # 创建客户端，启用API前缀
    client = ComfyUIClient(
        server_address="127.0.0.1",
        port=8188,
        config=config,
        use_api_prefix=True  # 使用 /api 前缀
    )
    
    try:
        # 1. 健康检查
        print("=== 健康检查 ===")
        is_healthy = await client.health_check()
        print(f"服务器健康状态: {'正常' if is_healthy else '异常'}")
        
        if not is_healthy:
            print("服务器不健康，退出示例")
            return
        
        # 2. 获取系统信息
        print("\n=== 系统信息 ===")
        stats = await client.system.get_system_stats()
        print(f"Python版本: {stats['system']['python_version']}")
        print(f"RAM总量: {stats['system']['ram_total'] / 1024**3:.1f}GB")
        
        # 3. 获取模型信息
        print("\n=== 模型信息 ===")
        model_types = await client.models.get_model_types()
        print(f"可用模型类型: {len(model_types)} 种")
        for model_type in model_types[:5]:  # 只显示前5个
            print(f"  - {model_type}")
        
        # 4. 获取可用节点
        print("\n=== 节点信息 ===")
        object_info = await client.system.get_object_info()
        print(f"可用节点数量: {len(object_info)}")
        
        # 显示一些主要节点
        important_nodes = ['KSampler', 'VAEDecode', 'CheckpointLoaderSimple']
        for node in important_nodes:
            if node in object_info:
                node_info = object_info[node]
                print(f"  - {node}: {node_info.get('display_name', node)}")
        
        # 5. 队列管理演示
        print("\n=== 队列管理 ===")
        queue_info = await client.prompts.get_queue()
        print(f"运行中的任务: {len(queue_info['queue_running'])}")
        print(f"等待中的任务: {len(queue_info['queue_pending'])}")
        
        # 6. 文件操作演示（如果有测试图片）
        print("\n=== 文件操作 ===")
        
        # 创建一个简单的测试图片
        try:
            from PIL import Image
            import io
            
            # 创建测试图片
            test_image = Image.new('RGB', (512, 512), color='red')
            bio = io.BytesIO()
            test_image.save(bio, format='PNG')
            image_bytes = bio.getvalue()
            
            # 上传图片
            upload_result = await client.files.upload_image(
                image_bytes=image_bytes,
                filename="test_image.png",
                overwrite=True
            )
            print(f"图片上传成功: {upload_result['name']}")
            
            # 下载图片
            downloaded_bytes = await client.files.download_image(
                filename=upload_result['name'],
                file_type="input"
            )
            print(f"图片下载成功，大小: {len(downloaded_bytes)} 字节")
            
            # 获取预览
            preview_bytes = await client.files.view_image_preview(
                filename=upload_result['name'],
                file_type="input",
                format="webp",
                quality=80
            )
            print(f"预览图片获取成功，大小: {len(preview_bytes)} 字节")
            
        except ImportError:
            print("未安装PIL，跳过图片操作演示")
        except Exception as e:
            print(f"文件操作示例出错: {e}")
        
        # 7. 历史记录管理
        print("\n=== 历史记录管理 ===")
        history = await client.prompts.get_history()
        print(f"历史记录数量: {len(history)}")
        
        # 显示最近的几个任务
        recent_tasks = list(history.keys())[:3]
        for task_id in recent_tasks:
            task_info = history[task_id]
            status = task_info.get('status', {})
            completed = status.get('completed', False)
            print(f"  任务 {task_id[:8]}...: {'已完成' if completed else '未完成'}")
        
        # 8. WebSocket 连接演示
        print("\n=== WebSocket 连接 ===")
        ws_client = client.get_websocket()
        print(f"WebSocket URL: {ws_client.url}")
        
        # 9. 示例工作流提交（简单的文本生成）
        print("\n=== 工作流提交示例 ===")
        
        # 这是一个简化的工作流示例
        simple_workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "model.safetensors"  # 需要实际存在的模型
                }
            }
        }
        
        # 注意：这只是结构示例，实际使用需要完整的工作流
        print("工作流结构准备完成（示例）")
        
        # 10. 批量清理操作
        print("\n=== 批量清理 ===")
        
        # 清空队列（如果需要）
        # await client.prompts.clear_queue()
        # print("队列已清空")
        
        # 释放内存
        await client.prompts.free_memory(free_memory=True)
        print("内存释放完成")
        
    except ComfyUIConnectionError as e:
        print(f"连接错误: {e}")
    except ComfyUIAPIError as e:
        print(f"API错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")
    finally:
        # 关闭客户端
        await client.close()
        print("\n客户端已关闭")

async def demonstrate_batch_operations():
    """演示批量操作"""
    print("\n=== 批量操作演示 ===")
    
    config = ComfyUIClientConfig.create_fast()
    client = ComfyUIClient(config=config)
    
    try:
        # 并发获取多种信息
        tasks = [
            client.system.get_system_stats(),
            client.models.get_model_types(),
            client.prompts.get_queue(),
            client.system.get_embeddings(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print("批量操作结果:")
        operation_names = ["系统统计", "模型类型", "队列状态", "嵌入列表"]
        
        for i, (name, result) in enumerate(zip(operation_names, results)):
            if isinstance(result, Exception):
                print(f"  {name}: 失败 - {result}")
            else:
                print(f"  {name}: 成功")
        
    finally:
        await client.close()

if __name__ == "__main__":
    print("ComfyUI 客户端高级用法演示")
    print("=" * 50)
    
    # 运行主演示
    asyncio.run(main())
    
    # 运行批量操作演示
    asyncio.run(demonstrate_batch_operations())
    
    print("\n演示完成！")