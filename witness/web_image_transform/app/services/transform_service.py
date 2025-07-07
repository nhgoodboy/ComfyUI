import asyncio
import logging
from typing import Dict, Any
from starlette.websockets import WebSocket

from app.client.comfyui_client import comfyui_client

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    """管理WebSocket连接"""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_json(self, client_id: str, data: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(data)
        else:
            logger.warning(f"Attempted to send message to disconnected client: {client_id}")

manager = ConnectionManager()


class TransformService:
    """处理图像转换的核心业务逻辑"""

    async def get_styles(self, session_id: str) -> Any:
        """获取可用的风格列表。"""
        try:
            # 每个会话都是一个独立用户，为其获取令牌
            token = await comfyui_client.get_user_token(session_id)
            styles = await comfyui_client.list_styles(token)
            return styles
        except Exception as e:
            logger.error(f"Failed to get styles for session {session_id}: {e}")
            raise

    async def process_transform(
        self,
        session_id: str,
        client_id: str,
        style_id: str,
        file_content: bytes,
        filename: str,
    ):
        """处理完整的图像转换流程并启动后台监控。"""
        try:
            # 1. 为上传操作获取一个全新的令牌
            await manager.send_json(client_id, {"status": "UPLOADING", "message": "正在上传图片..."})
            token_for_upload = await comfyui_client.get_user_token(session_id)
            file_info = await comfyui_client.upload_file(file_content, filename, token_for_upload)
            # 构造完整的图片URL
            image_url = f"http://127.0.0.1:8000{file_info['url']}"
            await manager.send_json(client_id, {"status": "UPLOADED", "message": "图片上传成功，正在创建任务..."})

            # 2. 为创建任务操作获取一个全新的令牌
            token_for_task = await comfyui_client.get_user_token(session_id)
            task_result = await comfyui_client.create_transform_task(style_id, image_url, token_for_task)
            task_id = task_result["task_id"]
            await manager.send_json(client_id, {"status": "QUEUED", "message": "任务已加入队列，等待处理。", "task_id": task_id})

            # 3. 为后台监控获取一个全新的令牌
            token_for_monitor = await comfyui_client.get_user_token(session_id)
            asyncio.create_task(self.monitor_task(client_id, task_id, token_for_monitor))

            return {"task_id": task_id}
        except Exception as e:
            logger.error(f"Transform process failed for session {session_id}: {e}", exc_info=True)
            await manager.send_json(client_id, {"status": "FAILED", "message": str(e)})
            raise

    async def monitor_task(self, client_id: str, task_id: str, token: str):
        """后台轮询任务状态，并通过WebSocket发送更新。"""
        while True:
            try:
                status_data = await comfyui_client.get_task_status(task_id, token)
                
                current_status = status_data.get("status")
                progress = status_data.get("progress", 0)

                await manager.send_json(client_id, {
                    "status": "PROCESSING",
                    "message": f"任务处理中... ({current_status})",
                    "progress": progress
                })

                if current_status == "completed":
                    # 任务完成后，调用新的端点获取结果
                    result_data = await comfyui_client.get_task_result(task_id, token)
                    await manager.send_json(client_id, {
                        "status": "COMPLETED",
                        "message": "任务处理完成！",
                        "result": result_data["data"]
                    })
                    break
                elif current_status == "failed":
                    await manager.send_json(client_id, {
                        "status": "FAILED",
                        "message": "任务处理失败。",
                        "details": status_data.get("error_details", "")
                    })
                    break
            
            except Exception as e:
                logger.error(f"Failed to monitor task {task_id}: {e}")
                await manager.send_json(client_id, {"status": "FAILED", "message": "监控任务时发生错误。"})
                break

            await asyncio.sleep(3)  # 每3秒轮询一次

# 全局服务实例
transform_service = TransformService() 