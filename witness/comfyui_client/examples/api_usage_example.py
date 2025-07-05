"""
ComfyUI客户端完整API使用示例

此示例展示了如何使用ComfyUI客户端的所有API功能，
包括模型管理、文件操作、用户数据管理等。
"""

import asyncio
import json
from comfyui_client import ComfyUIClient

async def main():
    # 初始化客户端
    client = ComfyUIClient(server_address='127.0.0.1', port=8188)
    
    try:
        print("=== ComfyUI 客户端 API 使用示例 ===\n")
        
        # ===== 系统信息 =====
        print("1. 获取系统信息")
        system_stats = await client.system.get_system_stats()
        print(f"系统统计: {system_stats.get('system', {}).get('os', 'Unknown')}")
        
        # ===== 模型管理 =====
        print("\n2. 模型管理")
        model_types = await client.models.get_model_types()
        print(f"可用模型类型: {model_types[:3]}...")  # 只显示前3个
        
        if model_types:
            first_model_type = model_types[0]
            models = await client.models.get_models(first_model_type)
            print(f"{first_model_type} 模型数量: {len(models)}")
        
        # ===== 节点信息 =====
        print("\n3. 节点信息")
        embeddings = await client.system.get_embeddings()
        print(f"可用嵌入数量: {len(embeddings)}")
        
        extensions = await client.system.get_extensions()
        print(f"扩展数量: {len(extensions)}")
        
        # ===== 队列管理 =====
        print("\n4. 队列管理")
        queue_info = await client.prompts.get_queue()
        print(f"运行中任务: {len(queue_info['queue_running'])}")
        print(f"等待中任务: {len(queue_info['queue_pending'])}")
        
        prompt_info = await client.prompts.get_prompt_info()
        print(f"队列剩余: {prompt_info.get('exec_info', {}).get('queue_remaining', 0)}")
        
        # ===== 历史记录 =====
        print("\n5. 历史记录")
        history = await client.prompts.get_history()
        print(f"历史记录数量: {len(history)}")
        
        # ===== 用户管理 =====
        print("\n6. 用户管理")
        users_info = await client.user.get_users()
        print(f"用户存储类型: {users_info.get('storage', 'Unknown')}")
        
        settings = await client.user.get_settings()
        print(f"用户设置项数量: {len(settings)}")
        
        # ===== 用户数据管理 =====
        print("\n7. 用户数据管理")
        try:
            userdata_list = await client.userdata.list_userdata_v2()
            print(f"用户数据文件数量: {len(userdata_list)}")
        except Exception as e:
            print(f"用户数据列表获取失败（可能是权限问题）: {e}")
        
        # ===== 内部API（调试用） =====
        print("\n8. 内部API")
        try:
            folder_paths = await client.internal.get_folder_paths()
            print(f"配置的文件夹路径数量: {len(folder_paths)}")
        except Exception as e:
            print(f"内部API访问失败: {e}")
        
        # ===== 文件操作示例 =====
        print("\n9. 文件操作能力")
        print("支持的文件操作:")
        print("- 图像上传 (client.files.upload_image)")
        print("- 遮罩上传 (client.files.upload_mask)")  
        print("- 文件查看 (client.files.view_file)")
        print("- 用户数据上传/下载/删除/移动")
        
        # ===== 工作流示例 =====
        print("\n10. 工作流提交能力")
        print("支持的工作流操作:")
        print("- 提交工作流 (client.prompts.queue_prompt)")
        print("- 中断执行 (client.prompts.interrupt)")
        print("- 队列管理 (client.prompts.delete_from_queue)")
        print("- 内存管理 (client.prompts.free_memory)")
        
        print("\n=== API 功能展示完成 ===")
        
    except Exception as e:
        print(f"示例执行过程中出错: {e}")
    finally:
        # 关闭客户端连接
        await client.close()

if __name__ == "__main__":
    asyncio.run(main()) 