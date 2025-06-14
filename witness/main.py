# witness/main.py
# 主程序入口，演示了如何使用 witness 包中的各个 API 客户端与 ComfyUI 进行交互。
import asyncio
import json
import time
import os

from config import settings
from utils.http_client import HttpClient
from api_clients.prompt_client import PromptClient
from api_clients.history_client import HistoryClient
from api_clients.queue_client import QueueClient
from api_clients.file_client import FileClient
from api_clients.system_client import SystemClient
from api_clients.user_client import UserClient
from api_clients.websocket_client import WebSocketClient

# --- WebSocket 消息处理示例 ---
def handle_websocket_message(ws_app, message):
    try:
        data = json.loads(message)
        client_id = ws_app.client_id if hasattr(ws_app, 'client_id') else 'N/A' # 获取客户端 ID
        print(f"[MainApp WS Handler - Client: {client_id}] Type: {data.get('type')}")
        
        if data['type'] == 'status':
            status_data = data.get('data', {}).get('status', {})
            exec_info = status_data.get('exec_info', {})
            print(f"  状态: 队列剩余: {exec_info.get('queue_remaining')}")
        elif data['type'] == 'execution_start':
            print(f"  执行开始: 提示 ID {data.get('data', {}).get('prompt_id')}")
        elif data['type'] == 'execution_cached':
            prompt_id = data.get('data', {}).get('prompt_id')
            nodes_cached = data.get('data', {}).get('nodes', [])
            print(f"  执行已缓存: 提示 ID {prompt_id}, 节点: {nodes_cached}")
        elif data['type'] == 'executing':
            node_id = data.get('data', {}).get('node')
            prompt_id = data.get('data', {}).get('prompt_id')
            print(f"  正在执行: 节点 {node_id}，提示 ID {prompt_id}")
        elif data['type'] == 'progress':
            progress_data = data.get('data', {})
            print(f"  进度: {progress_data.get('value')}/{progress_data.get('max')}")
        elif data['type'] == 'executed':
            executed_data = data.get('data', {})
            prompt_id = executed_data.get('prompt_id')
            output = executed_data.get('output', {})
            print(f"  已执行: 提示 ID {prompt_id}, 输出键: {list(output.keys())}")
            # 示例: if 'images' in output: print(f"    生成了 {len(output['images'])} 张图片.")
        elif data['type'] == 'bria_progress': # 自定义节点类型的示例
            bria_data = data.get('data', {})
            print(f"  自定义节点进度 (bria_progress): 步骤 {bria_data.get('step')}, 总步骤 {bria_data.get('total_steps')}")
        # 根据需要添加更多特定的处理程序

    except json.JSONDecodeError:
        print(f"[主应用 WS 处理程序] 非 JSON: {message[:100]}...") # 打印前 100 个字符
    except Exception as e:
        print(f"[主应用 WS 处理程序] 处理消息时出错: {e}")

def handle_websocket_open(ws_app):
    client_id = ws_app.client_id if hasattr(ws_app, 'client_id') else 'N/A'
    print(f"[主应用 WS 处理程序 - 客户端: {client_id}] WebSocket 连接已打开。")

def handle_websocket_error(ws_app, error):
    client_id = ws_app.client_id if hasattr(ws_app, 'client_id') else 'N/A'
    print(f"[主应用 WS 处理程序 - 客户端: {client_id}] WebSocket 错误: {error}")

def handle_websocket_close(ws_app, close_status_code, close_msg):
    client_id = ws_app.client_id if hasattr(ws_app, 'client_id') else 'N/A'
    print(f"[主应用 WS 处理程序 - 客户端: {client_id}] WebSocket 已关闭。代码: {close_status_code}, 消息: {close_msg}")

async def main_async_operations():
    print("--- ComfyUI Witness 系统主演示 ---")
    print(f"API URL: {settings.COMFYUI_API_URL}")
    print(f"WS URL: {settings.COMFYUI_WS_URL}")
    if settings.COMFYUI_API_KEY:
        print("API 密钥已配置。")
    else:
        print("API 密钥未配置 (将从 /prompt 请求中省略)。")

    # 初始化 HttpClient (可在客户端之间共享)
    http_client = HttpClient()

    # 初始化 API 客户端
    prompt_client = PromptClient(http_client)
    history_client = HistoryClient(http_client)
    queue_client = QueueClient(http_client)
    file_client = FileClient(http_client)
    system_client = SystemClient(http_client)
    user_client = UserClient(http_client)
    
    # --- WebSocket 客户端示例 ---
    print("\n--- WebSocket 客户端演示 ---")
    # 为此 WebSocket 连接创建一个唯一的 client_id
    ws_client_id = f"witness-main-{os.getpid()}"
    ws_client = WebSocketClient(
        client_id=ws_client_id,
        on_message_callback=lambda ws, msg: handle_websocket_message(ws.app, msg),
        on_open_callback=lambda ws: handle_websocket_open(ws.app),
        on_error_callback=lambda ws, err: handle_websocket_error(ws.app, err),
        on_close_callback=lambda ws, code, cmsg: handle_websocket_close(ws.app, code, cmsg)
    )
    # 使 client_id 可通过 ws.app.client_id 在回调中访问
    # 由于 WebSocketApp 构建回调的方式，这有点取巧
    if ws_client.ws_app:
         ws_client.ws_app.app = ws_client # 在 ws_app 上存储客户端实例
    
    ws_client.connect()
    # 在继续执行可能触发 WS 事件的 API 调用之前，给 WS 一些连接时间
    await asyncio.sleep(2) 

    try:
        # --- 系统客户端演示 ---
        print("\n--- 系统客户端演示 ---")
        system_stats = system_client.get_system_stats()
        print(f"系统统计: 主机名: {system_stats.get('system', {}).get('hostname', 'N/A')}, Python 版本: {system_stats.get('system', {}).get('python_version', 'N/A')}")
        
        embeddings = system_client.get_embeddings()
        print(f"找到 {len(embeddings)} 个 embeddings/Loras。")

        # --- 队列客户端演示 ---
        print("\n--- 队列客户端演示 ---")
        queue_info = queue_client.get_queue_info()
        print(f"队列信息: 正在运行的提示: {len(queue_info.get('queue_running', []))}, 待处理: {len(queue_info.get('queue_pending', []))}")

        # --- 提示客户端演示 (简单工作流) ---
        print("\n--- 提示客户端演示 ---")
        # 一个非常基础的工作流: KSampler (Efficient) -> SaveImage
        # 注意: 此工作流可能需要您的 ComfyUI 设置中可用的特定模型/节点。
        # 这是一个占位符；请替换为适用于您环境的有效工作流 JSON。
        sample_workflow = {
            "3": {
                "inputs": {
                    "seed": int(time.time()), # 动态种子
                    "steps": 20,
                    "cfg": 8,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler", # 基础 KSampler
            },
            "4": {
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}, # 替换为您的模型
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {"width": 512, "height": 512, "batch_size": 1},
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {"text": "beautiful scenery nature glass bottle landscape, purple galaxy bottle", "clip": ["4", 1]},
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {"text": "text, watermark", "clip": ["4", 1]},
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {"filename_prefix": "comfy_witness_example", "images": ["3", 0]},
                "class_type": "SaveImage"
            }
        }
        
        print("正在排队一个示例提示...")
        # 如果要关联它们，请将 WebSocket client_id 用于提示
        prompt_response = prompt_client.queue_prompt(sample_workflow, client_id=ws_client_id)
        queued_prompt_id = prompt_response.get('prompt_id')
        print(f"提示已成功排队！提示 ID: {queued_prompt_id}, 编号: {prompt_response.get('number')}")
        
        # 稍等片刻以查看与此提示相关的 WebSocket 消息
        print("等待 10 秒以观察已排队提示的 WebSocket 消息...")
        await asyncio.sleep(10) 

        # --- 历史客户端演示 ---
        if queued_prompt_id:
            print("\n--- 历史客户端演示 ---")
            print(f"正在获取提示 ID 的历史记录: {queued_prompt_id}...")
            # 再等一会儿，以确保执行可能已完成以获取历史记录
            await asyncio.sleep(5) 
            prompt_history = history_client.get_history_for_prompt(queued_prompt_id)
            if prompt_history and queued_prompt_id in prompt_history:
                print(f"提示 {queued_prompt_id} 的历史记录: 状态 - {prompt_history[queued_prompt_id].get('status', {}).get('status_str')}")
                outputs = prompt_history[queued_prompt_id].get('outputs', {})
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        print(f"  节点 {node_id} 生成了 {len(node_output['images'])} 张图片。")
                        for img_data in node_output['images']:
                            print(f"    - 图片: {img_data['filename']} (类型: {img_data['type']}, 子文件夹: {img_data.get('subfolder', '')})")
                            # --- 文件客户端演示 (查看图片 - 如果使用了 SaveImage) ---
                            # 这是一个基本示例；实际查看图片需要将字节保存到文件
                            # 或使用 Pillow 之类的库来显示它。
                            # print(f"      正在尝试查看图片: {img_data['filename']}")
                            # image_bytes = file_client.view_file(img_data['filename'], subfolder=img_data.get('subfolder', ''), file_type=img_data['type'])
                            # print(f"      收到了 {len(image_bytes) if image_bytes else 0} 字节的图片数据。")
            else:
                print(f"无法检索提示 ID {queued_prompt_id} 的历史记录，或者它尚未完成。")
        
        all_history = history_client.get_history()
        print(f"Total history items: {len(all_history)}")

        # --- User Client Demo ---
        print("\n--- User Client Demo ---")
        i18n_en = user_client.get_i18n_translations('en-US')
        print(f"Fetched {len(i18n_en)} i18n keys for en-US.")

        # --- File Client Demo (Upload - if you have an image to upload) ---
        # print("\n--- File Client Demo (Upload) ---")
        # # Create a dummy image file for upload demonstration
        # dummy_image_path = "dummy_upload_image.png"
        # try:
        #     from PIL import Image
        #     img = Image.new('RGB', (60, 30), color = 'red')
        #     img.save(dummy_image_path)
        #     print(f"Created dummy image: {dummy_image_path}")
            
        #     upload_response = file_client.upload_image(dummy_image_path, overwrite=True)
        #     print(f"Upload response: {upload_response}")
        #     if upload_response and 'name' in upload_response:
        #         print(f"Uploaded file as: {upload_response['name']}")
        #         # You could then use this uploaded image name in a workflow (e.g., LoadImage node)
        # except ImportError:
        #     print("Pillow library not found, skipping image creation for upload demo.")
        # except Exception as e:
        #     print(f"Error during file upload demo: {e}")
        # finally:
        #     if os.path.exists(dummy_image_path):
        #         os.remove(dummy_image_path)

        print("\n--- Demo Finished --- Waiting for final WebSocket messages (5s) ---")
        await asyncio.sleep(5)

    except Exception as e:
        print(f"An error occurred during the main demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ws_client.is_running:
            print("Disconnecting WebSocket client...")
            ws_client.disconnect()
        print("Main demo sequence complete.")

if __name__ == "__main__":
    # For asyncio operations like waiting for WebSocket messages
    try:
        asyncio.run(main_async_operations())
    except KeyboardInterrupt:
        print("\nExiting demo due to KeyboardInterrupt.")
    finally:
        print("Witness system demo shutdown.")