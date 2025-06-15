import uuid
import json
import random
import time
from queue import Queue
from PIL import Image
import io

# 这假设 comfyui_client 包位于父目录中
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from comfyui_client import ComfyUIClient
from comfyui_client.websocket import WebSocketClient

# --- WebSocket 处理器 ---
class WorkflowWebSocketHandler(WebSocketClient):
    def __init__(self, url, prompt_id):
        super().__init__(url)
        self.prompt_id = prompt_id
        self.output_images = {}
        self.is_finished = False

    def on_message(self, ws, message):
        try:
            msg = json.loads(message)
            if msg['type'] == 'executing':
                data = msg['data']
                if data['node'] is None and data['prompt_id'] == self.prompt_id:
                    self.logger.info("执行完成。")
                    self.is_finished = True
                    self.close()
            elif msg['type'] == 'executed':
                data = msg['data']
                if 'images' in data['output']:
                    self.logger.info(f"节点 {data['node']} 已生成图片。")
                    self.output_images[data['node']] = data['output']['images']
        except json.JSONDecodeError:
            # 这里处理二进制的预览图片
            pass
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")

# --- 主执行逻辑 ---
def main():
    # 初始化主客户端
    client = ComfyUIClient(server_address='127.0.0.1', port=8188)
    logger = client.logger

    # --- 加载工作流 ---
    # 这是 API 文档示例中的同一个工作流
    try:
        with open('workflow_api.json', 'r') as f:
            prompt_text = f.read()
        logger.info("从 workflow_api.json 加载工作流")
    except FileNotFoundError:
        logger.error("未找到 workflow_api.json。请根据 API 文档创建它。")
        return

    prompt = json.loads(prompt_text)

    # --- 设置随机种子 ---
    # 在此示例中，KSampler 节点的 ID 是 "3"
    prompt["3"]["inputs"]["seed"] = random.randint(0, 9999999999)

    # --- 将提示加入队列 ---
    client_id = str(uuid.uuid4())
    logger.info(f"使用客户端 ID 将提示加入队列: {client_id}")
    response = client.prompt.queue_prompt(prompt, client_id)
    prompt_id = response['prompt_id']
    logger.info(f"提示已成功加入队列。提示 ID: {prompt_id}")

    # --- WebSocket 连接以监控进度 ---
    ws_url = f"ws://{client.server_address}:{client.port}/ws?clientId={client_id}"
    ws_handler = WorkflowWebSocketHandler(ws_url, prompt_id)
    ws_handler.run_forever()
    
    # 等待执行完成
    while not ws_handler.is_finished:
        time.sleep(1)

    # --- 检索并保存输出图片 ---
    logger.info("执行完成。正在检索历史记录...")
    history = client.prompt.get_history(prompt_id).get(prompt_id)

    if not history:
        logger.error("未能检索到该提示的历史记录。")
        return

    for node_id, node_output in history['outputs'].items():
        if 'images' in node_output:
            logger.info(f"在节点 {node_id} 的输出中找到图片")
            for i, image_info in enumerate(node_output['images']):
                filename = image_info['filename']
                subfolder = image_info['subfolder']
                file_type = image_info['type']
                
                logger.info(f"正在下载图片: {filename}")
                image_data = client.file.view_file(filename, file_type, subfolder)
                
                # 保存图片
                try:
                    image = Image.open(io.BytesIO(image_data))
                    output_path = f"output_{node_id}_{i}.png"
                    image.save(output_path)
                    logger.info(f"图片已保存到 {output_path}")
                except Exception as e:
                    logger.error(f"保存图片 {filename} 失败: {e}")

if __name__ == "__main__":
    main()

# 您还需要在同一目录中有一个 `workflow_api.json` 文件。
# 您可以通过从 ComfyUI 界面保存工作流或使用 API 文档中的工作流来获取此文件。
# `workflow_api.json` 示例:
"""
{
  "3": {
    "inputs": {
      "seed": 123,
      "steps": 20,
      "cfg": 8.0,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0,
      "model": [ "4", 0 ],
      "positive": [ "6", 0 ],
      "negative": [ "7", 0 ],
      "latent_image": [ "5", 0 ]
    },
    "class_type": "KSampler"
  },
  "4": {
    "inputs": { "ckpt_name": "v1-5-pruned-emaonly.ckpt" },
    "class_type": "CheckpointLoaderSimple"
  },
  "5": {
    "inputs": { "width": 512, "height": 512, "batch_size": 1 },
    "class_type": "EmptyLatentImage"
  },
  "6": {
    "inputs": {
      "text": "beautiful scenery nature glass bottle landscape, purple galaxy bottle,",
      "clip": [ "4", 1 ]
    },
    "class_type": "CLIPTextEncode"
  },
  "7": {
    "inputs": { "text": "text, watermark", "clip": [ "4", 1 ] },
    "class_type": "CLIPTextEncode"
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI_API_Example",
      "images": [ "3", 0 ]
    },
    "class_type": "SaveImage"
  }
}
""" 