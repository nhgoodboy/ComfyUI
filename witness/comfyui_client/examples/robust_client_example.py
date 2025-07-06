"""
ComfyUI 健壮客户端使用示例

展示如何使用配置化的客户端，包括错误处理、重试机制和输入验证。
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加父目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from comfyui_client import (
    ComfyUIClient,
    ComfyUIClientConfig,
    ComfyUIConnectionError,
    ComfyUIAPIError,
    ComfyUITimeoutError,
    ComfyUIValidationError
)


async def main():
    """
    主函数，展示各种客户端配置和错误处理场景。
    """
    
    # 1. 创建健壮的客户端配置（适用于不稳定网络）
    robust_config = ComfyUIClientConfig.create_robust()
    robust_config.log_requests = True  # 启用请求日志
    robust_config.websocket_debug = True  # 启用WebSocket调试
    
    # 2. 创建客户端实例
    client = ComfyUIClient(
        server_address="127.0.0.1",
        port=8188,
        config=robust_config
    )
    
    try:
        # 3. 系统信息获取示例
        print("=== 获取系统信息 ===")
        try:
            system_stats = await client.system.get_system_stats()
            print(f"系统状态: {system_stats}")
        except ComfyUIConnectionError as e:
            print(f"连接错误: {e}")
            return
        except ComfyUIAPIError as e:
            print(f"API错误: {e}")
            return
        
        # 4. 模型列表获取示例
        print("\n=== 获取模型列表 ===")
        try:
            models = await client.models.get_models("checkpoints")
            print(f"可用模型: {models}")
        except ComfyUIValidationError as e:
            print(f"参数验证错误: {e}")
        except Exception as e:
            print(f"其他错误: {e}")
        
        # 5. 用户数据上传示例（包含输入验证）
        print("\n=== 用户数据上传示例 ===")
        try:
            # 创建示例数据
            sample_data = b"Hello, this is a test file!"
            
            # 上传文件（会自动进行输入验证）
            result = await client.userdata.upload_userdata_file(
                file="test/sample.txt",
                data=sample_data,
                overwrite=True,
                full_info=True
            )
            print(f"上传结果: {result}")
            
            # 获取上传的文件
            file_content = await client.userdata.get_userdata_file("test/sample.txt")
            print(f"文件内容: {file_content}")
            
        except ComfyUIValidationError as e:
            print(f"输入验证失败: {e}")
        except ComfyUIFileError as e:
            print(f"文件操作错误: {e}")
        except Exception as e:
            print(f"上传过程中发生错误: {e}")
        
        # 6. 错误处理示例
        print("\n=== 错误处理示例 ===")
        try:
            # 尝试访问不存在的端点（会触发重试机制）
            await client._request("GET", "/nonexistent-endpoint")
        except ComfyUIAPIError as e:
            print(f"预期的API错误: {e}")
        
        # 7. 输入验证示例
        print("\n=== 输入验证示例 ===")
        try:
            # 尝试上传无效数据（会触发验证错误）
            await client.userdata.upload_userdata_file(
                file="",  # 空文件名
                data=b"test",
                overwrite=True
            )
        except ComfyUIValidationError as e:
            print(f"预期的验证错误: {e}")
        
        # 8. WebSocket客户端示例
        print("\n=== WebSocket客户端示例 ===")
        try:
            ws_client = client.get_websocket()
            
            # 设置回调函数
            def on_progress(prompt_id, data):
                print(f"进度更新 - 提示ID: {prompt_id}, 数据: {data}")
            
            def on_completion(prompt_id, data):
                print(f"任务完成 - 提示ID: {prompt_id}, 数据: {data}")
            
            ws_client.set_progress_callback(on_progress)
            ws_client.set_completion_callback(on_completion)
            
            # 启动WebSocket连接
            ws_client.run_forever()
            
            # 等待一段时间以接收消息
            await asyncio.sleep(2)
            
            # 关闭连接
            ws_client.close()
            
        except Exception as e:
            print(f"WebSocket示例错误: {e}")
        
        # 9. 超时处理示例
        print("\n=== 超时处理示例 ===")
        try:
            # 创建快速超时配置
            fast_config = ComfyUIClientConfig.create_fast()
            fast_config.request_timeout = 0.001  # 极短超时，必定失败
            
            fast_client = ComfyUIClient(config=fast_config)
            await fast_client.system.get_system_stats()
            
        except ComfyUITimeoutError as e:
            print(f"预期的超时错误: {e}")
        except Exception as e:
            print(f"其他超时相关错误: {e}")
        finally:
            await fast_client.close()
    
    except Exception as e:
        print(f"主程序发生未处理的错误: {e}")
    
    finally:
        # 10. 清理资源
        print("\n=== 清理资源 ===")
        await client.close()
        print("客户端已关闭")


async def configuration_examples():
    """
    展示不同的配置选项。
    """
    print("\n=== 配置示例 ===")
    
    # 默认配置
    default_config = ComfyUIClientConfig.create_default()
    print(f"默认配置 - 超时: {default_config.request_timeout}s, 重试: {default_config.max_retries}次")
    
    # 快速配置
    fast_config = ComfyUIClientConfig.create_fast()
    print(f"快速配置 - 超时: {fast_config.request_timeout}s, 重试: {fast_config.max_retries}次")
    
    # 健壮配置
    robust_config = ComfyUIClientConfig.create_robust()
    print(f"健壮配置 - 超时: {robust_config.request_timeout}s, 重试: {robust_config.max_retries}次")
    
    # 自定义配置
    custom_config = ComfyUIClientConfig(
        request_timeout=45.0,
        max_retries=2,
        retry_delay=1.5,
        max_file_size=50 * 1024 * 1024,  # 50MB
        log_requests=True,
        enable_compression=True
    )
    print(f"自定义配置 - 超时: {custom_config.request_timeout}s, 文件大小限制: {custom_config.max_file_size}字节")


if __name__ == "__main__":
    # 运行配置示例
    asyncio.run(configuration_examples())
    
    # 运行主示例
    asyncio.run(main()) 