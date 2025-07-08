"""
WebSocket 推送 API
用于向外部客户端（如 web_image_transform）推送任务状态更新
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# 存储WebSocket连接
class PushConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"推送客户端连接: {client_id}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"推送客户端断开: {client_id}")
    
    async def push_task_update(self, task_id: str, update_data: Dict[str, Any]):
        """向所有连接的客户端推送任务更新"""
        message = {
            "type": "task_update",
            "task_id": task_id,
            "data": update_data
        }
        
        logger.info(f"准备推送任务更新: task_id={task_id}, 连接数={len(self.active_connections)}")
        logger.info(f"推送消息内容: {message}")
        
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
                logger.info(f"成功推送任务更新到客户端 {client_id}: {task_id}")
            except Exception as e:
                logger.warning(f"推送消息失败，客户端 {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            
        if not self.active_connections:
            logger.warning("没有活跃的WebSocket连接来推送消息")

# 全局推送管理器
push_manager = PushConnectionManager()

@router.websocket("/push/{client_id}")
async def websocket_push_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket 推送端点
    外部客户端连接到此端点以接收任务状态更新
    """
    await push_manager.connect(websocket, client_id)
    try:
        while True:
            # 保持连接活跃，等待服务器推送
            # 客户端可以发送心跳包或保持空消息
            try:
                await websocket.receive_text()
            except:
                break
    except WebSocketDisconnect:
        pass
    finally:
        push_manager.disconnect(client_id)

# 导出推送管理器供其他模块使用
__all__ = ["push_manager"] 