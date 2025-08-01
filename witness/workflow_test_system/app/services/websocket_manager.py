"""
WebSocket连接管理器
负责管理与ComfyUI工作流服务器的WebSocket连接
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Any, Optional, Callable
from ..config import config

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self, message_handler: Optional[Callable] = None):
        self.base_url = config.COMFYUI_WORKFLOW_SERVER_URL.replace('http', 'ws')
        self.ws_url = f"{self.base_url}/ws/workflow_test_system"
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.message_handler = message_handler
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.listen_task: Optional[asyncio.Task] = None
        
    async def connect(self):
        """连接WebSocket"""
        try:
            logger.info(f"连接WebSocket: {self.ws_url}")
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=config.WEBSOCKET_PING_INTERVAL,
                ping_timeout=config.WEBSOCKET_TIMEOUT
            )
            self.connected = True
            self.reconnect_attempts = 0
            logger.info("WebSocket连接成功")
            
            # 启动消息监听任务
            self.listen_task = asyncio.create_task(self._listen_messages())
            
            # 启动心跳任务
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            await self._handle_reconnect()
    
    async def _listen_messages(self):
        """监听WebSocket消息"""
        try:
            async for message in self.websocket:
                try:
                    # 忽略pong消息
                    if message == "pong":
                        continue
                    
                    data = json.loads(message)
                    logger.debug(f"收到WebSocket消息: {data}")
                    
                    if self.message_handler:
                        await self.message_handler(data)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"WebSocket消息解析失败: {e}")
                except Exception as e:
                    logger.error(f"WebSocket消息处理失败: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已断开")
            self.connected = False
            await self._handle_reconnect()
        except Exception as e:
            logger.error(f"WebSocket监听异常: {e}")
            self.connected = False
            await self._handle_reconnect()
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.connected:
            try:
                await asyncio.sleep(config.WEBSOCKET_PING_INTERVAL)
                if self.connected and self.websocket:
                    await self.websocket.send("ping")
                    logger.debug("发送心跳ping")
            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
                self.connected = False
                break
    
    async def _handle_reconnect(self):
        """处理重连"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = min(self.reconnect_delay * (1.5 ** (self.reconnect_attempts - 1)), 60)
            logger.info(f"WebSocket重连 {self.reconnect_attempts}/{self.max_reconnect_attempts}，{delay:.1f}秒后重试")
            
            await asyncio.sleep(delay)
            await self.connect()
        else:
            logger.error("WebSocket重连次数超限！启动持续重连模式")
            asyncio.create_task(self._continuous_reconnect())
    
    async def _continuous_reconnect(self):
        """持续重连模式"""
        logger.info("启动持续重连模式，每60秒重试一次")
        while not self.connected:
            try:
                await asyncio.sleep(60)
                logger.info("持续重连模式：尝试连接...")
                
                self.websocket = await websockets.connect(
                    self.ws_url,
                    ping_interval=config.WEBSOCKET_PING_INTERVAL,
                    ping_timeout=config.WEBSOCKET_TIMEOUT
                )
                self.connected = True
                self.reconnect_attempts = 0
                logger.info("重连成功")
                
                # 重新启动任务
                self.listen_task = asyncio.create_task(self._listen_messages())
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                break
                
            except Exception as e:
                logger.debug(f"重连失败: {e}")
                continue
    
    async def send_message(self, message: Dict[str, Any]):
        """发送消息"""
        if self.connected and self.websocket:
            try:
                await self.websocket.send(json.dumps(message))
                logger.debug(f"发送WebSocket消息: {message}")
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {e}")
                self.connected = False
    
    async def close(self):
        """关闭连接"""
        self.connected = False
        
        # 取消任务
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
        
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
        
        # 关闭WebSocket连接
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket连接已关闭")
    
    def set_message_handler(self, handler: Callable):
        """设置消息处理器"""
        self.message_handler = handler
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected and self.websocket is not None