from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
import uuid
import time

from ..utils.logger import get_logger, log_websocket_connect, log_websocket_disconnect
from .web_api import active_tasks

logger = get_logger("websocket")

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃的WebSocket连接
        self.active_connections: Dict[str, WebSocket] = {}
        # 存储客户端订阅的任务
        self.task_subscriptions: Dict[str, Set[str]] = {}
        # 心跳任务
        self.heartbeat_task = None
    
    async def connect(self, websocket: WebSocket) -> str:
        """接受WebSocket连接"""
        await websocket.accept()
        
        # 生成客户端ID
        client_id = str(uuid.uuid4())
        self.active_connections[client_id] = websocket
        
        log_websocket_connect(client_id)
        logger.info(f"WebSocket客户端连接: {client_id}, 当前连接数: {len(self.active_connections)}")
        
        # 启动心跳任务（如果还没有启动）
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        return client_id
    
    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
            # 清理任务订阅
            for task_id in list(self.task_subscriptions.keys()):
                if client_id in self.task_subscriptions[task_id]:
                    self.task_subscriptions[task_id].discard(client_id)
                    if not self.task_subscriptions[task_id]:
                        del self.task_subscriptions[task_id]
            
            log_websocket_disconnect(client_id)
            logger.info(f"WebSocket客户端断开: {client_id}, 当前连接数: {len(self.active_connections)}")
            
            # 如果没有连接了，停止心跳任务
            if not self.active_connections and self.heartbeat_task:
                self.heartbeat_task.cancel()
                self.heartbeat_task = None
    
    async def send_personal_message(self, message: dict, client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"发送消息失败 {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"广播消息失败 {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def send_to_task_subscribers(self, task_id: str, message: dict):
        """发送消息给任务订阅者"""
        if task_id not in self.task_subscriptions:
            return
        
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected_clients = []
        
        for client_id in self.task_subscriptions[task_id]:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_text(message_text)
                except Exception as e:
                    logger.error(f"发送任务消息失败 {client_id}: {e}")
                    disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def subscribe_to_task(self, client_id: str, task_id: str):
        """订阅任务更新"""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        
        self.task_subscriptions[task_id].add(client_id)
        logger.debug(f"客户端 {client_id} 订阅任务 {task_id}")
    
    def unsubscribe_from_task(self, client_id: str, task_id: str):
        """取消订阅任务"""
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(client_id)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
            logger.debug(f"客户端 {client_id} 取消订阅任务 {task_id}")
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.active_connections:
            try:
                # 发送心跳消息
                heartbeat_message = {
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "connections": len(self.active_connections)
                }
                
                await self.broadcast(heartbeat_message)
                
                # 等待30秒
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                logger.info("心跳任务已取消")
                break
            except Exception as e:
                logger.error(f"心跳任务错误: {e}")
                await asyncio.sleep(5)
    
    async def send_task_progress(self, task_id: str, progress: float, message: str):
        """发送任务进度更新"""
        progress_message = {
            "type": "progress",
            "task_id": task_id,
            "progress": progress,
            "message": message,
            "timestamp": time.time()
        }
        
        await self.send_to_task_subscribers(task_id, progress_message)
    
    async def send_task_completed(self, task_id: str, output_url: str, duration: float):
        """发送任务完成消息"""
        completed_message = {
            "type": "completed",
            "task_id": task_id,
            "output_url": output_url,
            "duration": duration,
            "timestamp": time.time()
        }
        
        await self.send_to_task_subscribers(task_id, completed_message)
    
    async def send_task_error(self, task_id: str, error_message: str):
        """发送任务错误消息"""
        error_msg = {
            "type": "error",
            "task_id": task_id,
            "message": error_message,
            "timestamp": time.time()
        }
        
        await self.send_to_task_subscribers(task_id, error_msg)
    
    async def send_system_stats(self, stats: dict):
        """发送系统统计信息"""
        stats_message = {
            "type": "system_stats",
            "stats": stats,
            "timestamp": time.time()
        }
        
        await self.broadcast(stats_message)
    
    def get_connection_stats(self) -> dict:
        """获取连接统计信息"""
        return {
            "total_connections": len(self.active_connections),
            "active_subscriptions": len(self.task_subscriptions),
            "subscribed_tasks": list(self.task_subscriptions.keys())
        }

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点处理函数"""
    client_id = None
    
    try:
        # 建立连接
        client_id = await websocket_manager.connect(websocket)
        
        # 发送欢迎消息
        welcome_message = {
            "type": "welcome",
            "client_id": client_id,
            "message": "WebSocket连接已建立",
            "timestamp": time.time()
        }
        await websocket_manager.send_personal_message(welcome_message, client_id)
        
        # 监听消息
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_websocket_message(client_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket客户端主动断开: {client_id}")
                break
            except json.JSONDecodeError as e:
                logger.warning(f"WebSocket消息JSON解析失败 {client_id}: {e}")
                error_response = {
                    "type": "error",
                    "message": "消息格式错误",
                    "timestamp": time.time()
                }
                await websocket_manager.send_personal_message(error_response, client_id)
            except Exception as e:
                logger.error(f"WebSocket消息处理错误 {client_id}: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    
    finally:
        # 清理连接
        if client_id:
            websocket_manager.disconnect(client_id)

async def handle_websocket_message(client_id: str, message: dict):
    """处理WebSocket消息"""
    message_type = message.get("type")
    
    try:
        if message_type == "subscribe":
            # 订阅任务更新
            task_id = message.get("task_id")
            if task_id:
                websocket_manager.subscribe_to_task(client_id, task_id)
                
                # 发送当前任务状态
                if task_id in active_tasks:
                    task = active_tasks[task_id]
                    status_message = {
                        "type": "task_status",
                        "task_id": task_id,
                        "status": task["status"],
                        "progress": task["progress"],
                        "message": task["message"],
                        "timestamp": time.time()
                    }
                    await websocket_manager.send_personal_message(status_message, client_id)
        
        elif message_type == "unsubscribe":
            # 取消订阅任务
            task_id = message.get("task_id")
            if task_id:
                websocket_manager.unsubscribe_from_task(client_id, task_id)
        
        elif message_type == "ping":
            # 响应ping消息
            pong_message = {
                "type": "pong",
                "timestamp": time.time()
            }
            await websocket_manager.send_personal_message(pong_message, client_id)
        
        elif message_type == "get_stats":
            # 获取连接统计
            stats = websocket_manager.get_connection_stats()
            stats_message = {
                "type": "connection_stats",
                "stats": stats,
                "timestamp": time.time()
            }
            await websocket_manager.send_personal_message(stats_message, client_id)
        
        else:
            logger.warning(f"未知的WebSocket消息类型: {message_type}")
            error_response = {
                "type": "error",
                "message": f"未知的消息类型: {message_type}",
                "timestamp": time.time()
            }
            await websocket_manager.send_personal_message(error_response, client_id)
    
    except Exception as e:
        logger.error(f"处理WebSocket消息失败 {client_id}: {e}")
        error_response = {
            "type": "error",
            "message": "消息处理失败",
            "timestamp": time.time()
        }
        await websocket_manager.send_personal_message(error_response, client_id)

# 任务进度监控
async def monitor_task_progress():
    """监控任务进度并发送WebSocket更新"""
    last_task_states = {}
    
    while True:
        try:
            current_time = time.time()
            
            for task_id, task in active_tasks.items():
                last_state = last_task_states.get(task_id, {})
                
                # 检查状态是否有变化
                if (task["status"] != last_state.get("status") or 
                    task["progress"] != last_state.get("progress")):
                    
                    if task["status"] == "completed":
                        await websocket_manager.send_task_completed(
                            task_id, 
                            task.get("output_url", ""), 
                            task.get("duration", 0)
                        )
                    elif task["status"] == "failed":
                        await websocket_manager.send_task_error(
                            task_id, 
                            task.get("error_message", "未知错误")
                        )
                    else:
                        await websocket_manager.send_task_progress(
                            task_id, 
                            task["progress"], 
                            task["message"]
                        )
                    
                    # 更新最后状态
                    last_task_states[task_id] = {
                        "status": task["status"],
                        "progress": task["progress"],
                        "message": task["message"]
                    }
            
            # 清理已完成或失败的任务状态记录
            completed_tasks = [
                task_id for task_id, task in active_tasks.items()
                if task["status"] in ["completed", "failed"] and 
                current_time - task.get("end_time", current_time) > 300  # 5分钟后清理
            ]
            
            for task_id in completed_tasks:
                if task_id in last_task_states:
                    del last_task_states[task_id]
            
            # 等待2秒后再次检查
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"任务进度监控错误: {e}")
            await asyncio.sleep(5)

# 启动任务进度监控
def start_task_monitor():
    """启动任务进度监控"""
    asyncio.create_task(monitor_task_progress()) 