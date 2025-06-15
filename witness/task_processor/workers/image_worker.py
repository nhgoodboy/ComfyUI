# 此文件包含图像处理工作程序的逻辑
# 工作程序将从队列中获取任务，并调用 ComfyUI API 进行处理

import time
import json
import base64
import os # 用于路径操作
import asyncio # 新增导入
import logging
import uuid # 新增导入

from witness.task_processor.tasks import UserInfo, WorkerTaskPayload
from witness.core.comfy_client import ComfyUIClient
from witness.utils.workflow_utils import load_workflow, update_workflow_image_and_user

logger = logging.getLogger(__name__)

async def process_image_task(task_data: WorkerTaskPayload): # 改为异步函数并使用 WorkerTaskPayload
    """
    处理单个图像处理任务。

    参数:
    - task_data (dict): 包含任务详情的字典，例如:
        {
            "task_id": "some-uuid",
            "image_data": "base64_encoded_image_string",
            "workflow_name": "style_change",
            "user_info": {"user_id": "user123", "user_group": "groupA"}
        }
    """
    task_id = task_data.task_id
    image_data_b64 = task_data.image_data_b64
    workflow_name = task_data.workflow_name
    user_info = task_data.user_info

    logger.info(f"[Worker] 开始处理任务: {task_id}，用户: {user_info.user_id}，工作流: {workflow_name}")

    client = None  # 初始化 client 以便在 finally 中可用
    try:
        # 0. 准备 ComfyUI 客户端 (地址应来自配置)
        # TODO: 从配置模块加载 ComfyUI 服务器地址
        comfy_server_address = os.getenv("COMFYUI_SERVER_ADDRESS", "http://127.0.0.1:8188")
        client = ComfyUIClient(server_address=comfy_server_address)
        # ComfyUIClient.connect() is synchronous and raises an error on failure
        client.connect()
        logger.info(f"[Worker] ComfyUI 客户端已连接 (目标: {comfy_server_address})")

        # 1. 解码图像数据并上传到 ComfyUI
        image_bytes = base64.b64decode(image_data_b64)
        upload_filename = f"{task_id}_{user_info.user_id}_input.png"
        # 使用 user_id 作为子文件夹，以便更好地组织用户上传的文件
        upload_subfolder = user_info.user_id 
        
        logger.info(f"[Worker] 准备上传图像 '{upload_filename}' 到子文件夹 '{upload_subfolder}'")
        upload_response = client.upload_image(
            image_bytes=image_bytes, 
            filename=upload_filename, 
            subfolder=upload_subfolder, # 指定子文件夹
            image_type="input", 
            overwrite=True # 通常对于临时任务输入，覆盖是可以接受的
        )
        # 从响应中构建 LoadImage 节点所需的文件名
        # ComfyUI 的 LoadImage 节点需要相对于其 input 目录的路径
        # FileClient.upload_image 响应包含 'name', 'subfolder', 'type'
        uploaded_image_filename_for_workflow = f"{upload_response['name']}"
        if upload_response.get('subfolder'):
             uploaded_image_filename_for_workflow = f"{upload_response['subfolder']}/{upload_response['name']}"
        
        logger.info(f"[Worker] 图像已上传。工作流将使用图像: {uploaded_image_filename_for_workflow}")

        # 2. 加载指定的工作流 JSON
        # TODO: 工作流路径应该更健壮，例如从配置或项目根目录相对定位
        workflow_base_path = os.path.join(os.path.dirname(__file__), "../../../workflows") # 定位到 witness/workflows
        workflow_path = os.path.normpath(os.path.join(workflow_base_path, f"{workflow_name}.json"))
        api_workflow = load_workflow(workflow_path)
        logger.info(f"[Worker] 已加载工作流: {workflow_path}")

        # 3. 动态修改工作流以包含上传的图像和用户信息
        updated_workflow = update_workflow_image_and_user(
            workflow=api_workflow, 
            uploaded_image_filename=uploaded_image_filename_for_workflow, 
            user_info=user_info
        )
        logger.info(f"[Worker] 工作流已更新以包含用户数据和图像")

        # 4. 提交工作流到 ComfyUI
        logger.info(f"[Worker] 准备提交更新后的工作流到 ComfyUI...")
        result_prompt = client.queue_prompt(updated_workflow)
        prompt_id = result_prompt.get('prompt_id')
        if not prompt_id:
            raise ValueError(f"提交工作流失败，未收到 prompt_id: {result_prompt}")
        logger.info(f"[Worker] 工作流已提交到 ComfyUI，Prompt ID: {prompt_id}")

        # 5. 等待结果 (WebSocket)
        logger.info(f"[Worker] 开始通过 WebSocket 等待 Prompt ID '{prompt_id}' 的结果...")
        output_node_data_list = await client.wait_for_output_ws(prompt_id)
        logger.info(f"[Worker] 从 ComfyUI (WebSocket) 收到处理结果: {output_node_data_list}")
        
        # 假设我们关心的是 SaveImage 节点的输出
        # 这里需要根据实际工作流的输出节点类型和名称来提取数据
        final_output_image_data = "mock_no_image_output_found"
        for node_output_info in output_node_data_list:
            # 假设输出包含 'images' 列表，且每个图像有 'filename', 'subfolder', 'type'
            if node_output_info.get('outputs') and 'images' in node_output_info['outputs']:
                first_image_info = node_output_info['outputs']['images'][0]
                # TODO: 从 ComfyUI 下载图像数据或获取可访问的 URL
                # output_filename = f"{first_image_info['filename']}"
                # output_subfolder = first_image_info.get('subfolder', '')
                # output_type = first_image_info.get('type')
                # image_url_or_data = client.get_image_data(output_filename, output_subfolder, output_type)
                final_output_image_data = f"generated_image_path: {first_image_info.get('subfolder','')}/{first_image_info.get('filename')}"
                break 

        logger.info(f"[Worker] 任务 {task_id} 处理完成。最终输出预览: {final_output_image_data[:100]}")

        # 6. 处理结果 (例如，保存到存储，通知用户)
        # save_result_to_db(task_id, user_info, final_output_image_data)
        # notify_user_via_websocket_or_webhook(user_info.user_id, task_id, "completed", final_output_image_data)

        return {"status": "success", "task_id": task_id, "output_preview": final_output_image_data[:100], "prompt_id": prompt_id}


    except Exception as e:
        logger.error(f"[Worker] 处理任务 {task_id} 时发生严重错误: {e}", exc_info=True)
        # notify_user(user_info.user_id, task_id, "failed", str(e))
        return {"status": "error", "task_id": task_id, "error_message": str(e)}
    finally:
        if client and client.is_ws_connected:
            await client.close_websocket()
            logger.info(f"[Worker] WebSocket 连接已为任务 {task_id} 关闭。")

async def test_process_image_task():
    """Function to directly test the process_image_task for development."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("[Test Worker] 开始直接测试 process_image_task...")

    mock_user = UserInfo(user_id="test_direct_worker_user", user_group="test_direct_group")
    # Minimal valid PNG: 1x1 black pixel, base64 encoded
    minimal_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    test_task_payload = WorkerTaskPayload(
        task_id=str(uuid.uuid4()),
        image_data_b64=minimal_png_b64,
        workflow_name="style_change", # Ensure this workflow exists in witness/workflows/
        user_info=mock_user
    )

    logger.info(f"[Test Worker] 创建测试任务负载: {test_task_payload.task_id}")
    result = await process_image_task(test_task_payload)
    logger.info(f"[Test Worker] process_image_task 完成，结果: {result}")

if __name__ == "__main__":
    # 设置 COMFYUI_SERVER_ADDRESS 环境变量用于测试，如果 ComfyUI 不在默认地址
    # os.environ["COMFYUI_SERVER_ADDRESS"] = "http://your_comfy_ui_server:port"
    
    # 确保 workflows/style_change.json 存在且配置正确
    # 特别是 LoadImage 和 SaveImage 节点的标题或类型需要与 workflow_utils.py 中的默认值匹配
    # 或者在调用 update_workflow_image_and_user 时传递正确的标题
    asyncio.run(test_process_image_task())