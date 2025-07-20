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
    
    async def push_task_update(self, request_id: str, update_data: Dict[str, Any]):
        """向特定用户推送任务更新（基于任务中的user_id）"""
        message = {
            "type": "task_update",
            "request_id": request_id,
            "data": update_data
        }
        
        # 从任务数据中获取user_id来确定推送目标
        task_user_id = update_data.get("user_id")
        
        logger.info(f"准备推送任务更新: request_id={request_id}, target_user={task_user_id}, 连接数={len(self.active_connections)}")
        logger.info(f"推送消息内容: {message}")
        
        if not task_user_id:
            logger.warning(f"任务 {request_id} 缺少user_id，无法确定推送目标")
            return
        
        # 查找目标用户的连接
        target_connections = []
        
        # 支持两种连接模式：
        # 1. 直接用户连接（旧模式兼容）
        if task_user_id in self.active_connections:
            target_connections.append((task_user_id, self.active_connections[task_user_id]))
        
        # 2. 服务连接（新的一对一模式）
        # 检查是否有web_image_transform_service连接
        service_id = "web_image_transform_service"
        if service_id in self.active_connections:
            target_connections.append((service_id, self.active_connections[service_id]))
        
        if not target_connections:
            logger.warning(f"找不到用户 {task_user_id} 的WebSocket连接")
            return
        
        # 向目标连接推送消息
        disconnected_clients = []
        for client_id, websocket in target_connections:
            try:
                await websocket.send_json(message)
                logger.info(f"成功推送任务更新到客户端 {client_id}: {request_id} (target_user: {task_user_id})")
            except Exception as e:
                logger.warning(f"推送消息失败，客户端 {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)

# 全局推送管理器
push_manager = PushConnectionManager()

# 导出推送管理器供其他模块使用
__all__ = ["push_manager"] 