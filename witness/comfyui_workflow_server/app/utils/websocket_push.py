"""
WebSocket 推送管理器
用于向外部客户端推送任务状态更新
"""

import logging
from typing import Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

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
    
    async def push_to_client(self, client_id: str, message: Dict[str, Any]):
        """向指定客户端推送消息"""
        if client_id not in self.active_connections:
            logger.warning(f"找不到客户端连接: {client_id}")
            return
        
        try:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message)
            # logger.info(f"成功推送消息到客户端 {client_id}")
        except Exception as e:
            logger.warning(f"推送消息失败，客户端 {client_id}: {e}")
            self.disconnect(client_id)

    async def push_workflow_update(self, request_id: str, update_data: Dict[str, Any]):
        """向特定请求推送工作流更新（基于request_id）"""
        message = {
            "type": "workflow_update",
            "request_id": request_id,
            "data": update_data
        }
        
        # 使用request_id作为推送目标
        # logger.info(f"准备推送工作流更新: request_id={request_id}, 连接数={len(self.active_connections)}")
        # logger.info(f"推送消息内容: {message}")
        
        # 查找目标连接
        target_connections = []
        
        # 支持两种连接模式：
        # 1. 直接请求连接（使用request_id作为client_id）
        if request_id in self.active_connections:
            target_connections.append((request_id, self.active_connections[request_id]))
        
        # 2. 服务连接（新的一对一模式）
        # 检查是否有web_image_transform_service连接
        service_id = "web_image_transform_service"
        if service_id in self.active_connections:
            target_connections.append((service_id, self.active_connections[service_id]))
        
        if not target_connections:
            logger.warning(f"找不到请求 {request_id} 的WebSocket连接")
            return
        
        # 向目标连接推送消息
        disconnected_clients = []
        for client_id, websocket in target_connections:
            try:
                await websocket.send_json(message)
                # logger.info(f"成功推送工作流更新到客户端 {client_id}: {request_id}")
            except Exception as e:
                logger.warning(f"推送消息失败，客户端 {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)

# 全局推送管理器
push_manager = PushConnectionManager()

# 兼容性别名
push_manager.push_task_update = push_manager.push_workflow_update

# 导出推送管理器供其他模块使用
__all__ = ["push_manager"] 
