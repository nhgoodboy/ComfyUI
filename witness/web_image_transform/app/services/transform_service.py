import asyncio
import logging
import websockets
import json
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
            try:
                await self.active_connections[client_id].send_json(data)
                return True
            except Exception as e:
                logger.warning(f"Failed to send message to client {client_id}: {e}")
                # 连接可能已断开，清理连接
                self.disconnect(client_id)
                return False
        else:
            logger.warning(f"Attempted to send message to disconnected client: {client_id}")
            return False

    def is_connected(self, client_id: str) -> bool:
        """检查客户端是否仍然连接"""
        return client_id in self.active_connections

manager = ConnectionManager()


class WorkflowServerPushListener:
    """监听 workflow_server 的 WebSocket 推送"""
    
    def __init__(self, transform_service):
        self.transform_service = transform_service
        self.websocket = None
        self.is_running = False
        self.reconnect_delay = 5  # 重连间隔（秒）
    
    async def start(self):
        """启动监听器"""
        if self.is_running:
            return
        
        self.is_running = True
        asyncio.create_task(self._maintain_connection())
    
    async def stop(self):
        """停止监听器"""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
    
    async def _maintain_connection(self):
        """维护与 workflow_server 的连接"""
        while self.is_running:
            try:
                # 连接到 workflow_server 的推送端点
                ws_url = "ws://127.0.0.1:8000/api/v1/ws/push/web_image_transform"
                logger.info(f"连接到 workflow_server 推送端点: {ws_url}")
                
                async with websockets.connect(ws_url) as websocket:
                    self.websocket = websocket
                    logger.info("已连接到 workflow_server 推送端点")
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self._handle_push_message(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"解析推送消息失败: {e}")
                        except Exception as e:
                            logger.error(f"处理推送消息失败: {e}")
                            
            except Exception as e:
                if self.is_running:
                    logger.warning(f"与 workflow_server 连接失败: {e}")
                    logger.info(f"{self.reconnect_delay} 秒后重连...")
                    await asyncio.sleep(self.reconnect_delay)
                    # 逐步增加重连间隔，最大30秒
                    self.reconnect_delay = min(self.reconnect_delay * 1.5, 30)
                else:
                    break
        
        self.websocket = None
        logger.info("workflow_server 推送监听器已停止")
    
    async def _handle_push_message(self, data: Dict[str, Any]):
        """处理推送消息"""
        if data.get("type") == "task_update":
            task_id = data.get("task_id")
            update_data = data.get("data", {})
            
            if task_id:
                await self.transform_service.handle_task_update(task_id, update_data)


class TransformService:
    """处理图像转换的核心业务逻辑"""

    def __init__(self):
        self.task_to_client: Dict[str, str] = {}  # {task_id: client_id} 映射
        self.push_listener = WorkflowServerPushListener(self)

    async def start_push_listener(self):
        """启动推送监听器"""
        await self.push_listener.start()

    async def stop_push_listener(self):
        """停止推送监听器"""
        await self.push_listener.stop()

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
        """处理完整的图像转换流程。"""
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
            
            # 保存任务到客户端的映射
            self.task_to_client[task_id] = client_id
            
            await manager.send_json(client_id, {
                "status": "QUEUED", 
                "message": "任务已加入队列，等待处理。", 
                "task_id": task_id
            })

            logger.info(f"任务已创建: {task_id}，等待 workflow_server 推送更新...")

            return {"task_id": task_id}
        except Exception as e:
            logger.error(f"Transform process failed for session {session_id}: {e}", exc_info=True)
            await manager.send_json(client_id, {"status": "FAILED", "message": str(e)})
            raise



    def _cleanup_task(self, task_id: str):
        """清理任务映射"""
        if task_id in self.task_to_client:
            del self.task_to_client[task_id]

    async def handle_task_update(self, task_id: str, update_data: Dict[str, Any]):
        """处理来自workflow_server的任务更新推送"""
        client_id = self.task_to_client.get(task_id)
        if not client_id:
            logger.warning(f"收到任务更新但找不到对应的客户端: {task_id}")
            return
            
        if not manager.is_connected(client_id):
            logger.warning(f"客户端已断开连接，清理任务: {task_id}")
            self._cleanup_task(task_id)
            return
            
        # 根据更新类型发送相应的消息
        status = update_data.get("status")
        if status == "completed":
            await manager.send_json(client_id, {
                "status": "COMPLETED",
                "message": "任务处理完成！",
                "result": update_data.get("result", {})
            })
            self._cleanup_task(task_id)
        elif status == "failed":
            await manager.send_json(client_id, {
                "status": "FAILED",
                "message": "任务处理失败。",
                "details": update_data.get("error_message", "")
            })
            self._cleanup_task(task_id)
        elif status == "running":
            progress = update_data.get("progress", 0)
            await manager.send_json(client_id, {
                "status": "PROCESSING",
                "message": f"任务处理中... ({status})",
                "progress": progress
            })
            logger.debug(f"任务 {task_id} 进度更新: {progress}%")

# 全局服务实例
transform_service = TransformService() 