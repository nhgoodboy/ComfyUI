import asyncio
import logging
import websockets
import json
from typing import Dict, Any
from starlette.websockets import WebSocket

from app.client.comfyui_client import comfyui_client
from app.config import settings

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
                ws_url = f"ws://{settings.COMFYUI_WORKFLOW_SERVER_URL.replace('http://', '').replace('https://', '')}/api/v1/ws/push/web_image_transform"
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
        logger.info(f"收到workflow_server推送消息: {data}")
        
        if data.get("type") == "task_update":
            task_id = data.get("task_id")
            update_data = data.get("data", {})
            
            logger.info(f"处理任务更新: task_id={task_id}, data={update_data}")
            
            if task_id:
                await self.transform_service.handle_task_update(task_id, update_data)
            else:
                logger.warning("推送消息中缺少task_id")
        else:
            logger.warning(f"未知的推送消息类型: {data.get('type')}")


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
        """获取可用的风格列表（简化版，无需认证）。"""
        try:
            styles = await comfyui_client.list_styles()
            return styles
        except Exception as e:
            logger.error(f"Failed to get styles: {e}")
            raise

    async def process_transform(
        self,
        session_id: str,
        client_id: str,
        style_id: str,
        file_content: bytes,
        filename: str,
    ):
        """处理完整的图像转换流程（简化版）。"""
        try:
            # 使用session_id作为user_id
            user_id = session_id
            
            # 1. 上传文件
            await manager.send_json(client_id, {"status": "UPLOADING", "message": "正在上传图片..."})
            file_info = await comfyui_client.upload_file(user_id, file_content, filename)
            
            # 构造完整的图片URL
            image_url = f"{settings.COMFYUI_WORKFLOW_SERVER_URL}{file_info['url']}"
            await manager.send_json(client_id, {"status": "UPLOADED", "message": "图片上传成功，正在创建任务..."})

            # 2. 创建任务
            task_result = await comfyui_client.create_task(user_id, style_id, image_url)
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
            logger.warning(f"收到未知任务的更新: {task_id}")
            return

        if not manager.is_connected(client_id):
            logger.warning(f"客户端 {client_id} 已断开连接，清理任务映射")
            self._cleanup_task(task_id)
            return

        try:
            status = update_data.get("status", "unknown")
            progress = update_data.get("progress", 0)
            message = update_data.get("message", "")

            logger.info(f"转发任务更新到客户端: task_id={task_id}, client_id={client_id}, status={status}")

            if status == "completed":
                # 任务完成，获取结果
                try:
                    # 这里需要获取user_id，我们可以从任务映射中获取session_id
                    # 但为了简化，我们可以使用一个更简单的方法
                    await manager.send_json(client_id, {
                        "status": "COMPLETED",
                        "message": "图像转换完成！",
                        "task_id": task_id,
                        "progress": 100
                    })
                    self._cleanup_task(task_id)
                except Exception as e:
                    logger.error(f"获取任务结果失败: {e}")
                    await manager.send_json(client_id, {
                        "status": "FAILED",
                        "message": f"获取结果失败: {str(e)}",
                        "task_id": task_id
                    })
                    self._cleanup_task(task_id)
            elif status == "failed":
                error_msg = update_data.get("error_message", "转换失败")
                await manager.send_json(client_id, {
                    "status": "FAILED",
                    "message": error_msg,
                    "task_id": task_id
                })
                self._cleanup_task(task_id)
            else:
                # 进行中的状态
                await manager.send_json(client_id, {
                    "status": status.upper(),
                    "message": message or f"任务状态: {status}",
                    "task_id": task_id,
                    "progress": progress
                })

        except Exception as e:
            logger.error(f"处理任务更新失败: task_id={task_id}, error={e}")

# 创建全局服务实例
transform_service = TransformService() 