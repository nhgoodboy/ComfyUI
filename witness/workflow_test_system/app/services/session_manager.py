"""
会话管理器
负责管理多个前端会话和消息分发
"""

import asyncio
import uuid
import time
import logging
from typing import Dict, Any, Optional, Set, List
from datetime import datetime
from fastapi import WebSocket
from ..config import config

logger = logging.getLogger(__name__)

class SessionInfo:
    """会话信息"""
    
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.request_ids: Set[str] = set()  # 该会话关联的request_id集合
        self.connected = True

class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionInfo] = {}
        self.request_to_session: Dict[str, str] = {}  # request_id -> session_id  
        self.cleanup_task: Optional[asyncio.Task] = None
        
    def start_cleanup_task(self):
        """启动清理任务"""
        if not self.cleanup_task or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """清理循环任务"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务异常: {e}")
    
    async def _cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session_info in self.sessions.items():
            # 检查会话是否超过配置的超时时间
            time_diff = (current_time - session_info.last_active).total_seconds()
            if time_diff > config.SESSION_TIMEOUT:
                expired_sessions.append(session_id)
                logger.info(f"会话 {session_id} 已过期")
        
        # 移除过期会话
        for session_id in expired_sessions:
            await self.remove_session(session_id)
    
    async def create_session(self, websocket: WebSocket) -> str:
        """创建新会话"""
        # 检查会话数量是否超过限制
        if len(self.sessions) >= config.MAX_SESSIONS:
            logger.warning(f"会话数量达到上限 {config.MAX_SESSIONS}")
            # 移除最旧的会话
            oldest_session = min(self.sessions.values(), key=lambda s: s.created_at)
            await self.remove_session(oldest_session.session_id)
        
        session_id = str(uuid.uuid4())
        session_info = SessionInfo(session_id, websocket)
        self.sessions[session_id] = session_info
        
        logger.info(f"创建会话: {session_id}")
        return session_id
    
    async def remove_session(self, session_id: str):
        """移除会话"""
        if session_id in self.sessions:
            session_info = self.sessions[session_id]
            
            # 清理关联的request_id映射
            for request_id in session_info.request_ids:
                if request_id in self.request_to_session:
                    del self.request_to_session[request_id]
            
            # 关闭WebSocket连接
            if session_info.connected:
                try:
                    await session_info.websocket.close()
                except Exception as e:
                    logger.debug(f"关闭WebSocket连接失败: {e}")
            
            del self.sessions[session_id]
            logger.info(f"移除会话: {session_id}")
    
    def associate_request(self, session_id: str, request_id: str):
        """关联请求ID与会话"""
        if session_id in self.sessions:
            self.sessions[session_id].request_ids.add(request_id)
            self.request_to_session[request_id] = session_id
            self.sessions[session_id].last_active = datetime.now()
            logger.debug(f"关联请求 {request_id} 与会话 {session_id}")
    
    def disassociate_request(self, request_id: str):
        """取消关联请求ID"""
        if request_id in self.request_to_session:
            session_id = self.request_to_session[request_id]
            if session_id in self.sessions:
                self.sessions[session_id].request_ids.discard(request_id)
            del self.request_to_session[request_id]
            logger.debug(f"取消关联请求 {request_id}")
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """向指定会话发送消息"""
        if session_id in self.sessions:
            session_info = self.sessions[session_id]
            if session_info.connected:
                try:
                    await session_info.websocket.send_json(message)
                    session_info.last_active = datetime.now()
                    logger.debug(f"向会话 {session_id} 发送消息: {message.get('type', 'unknown')}")
                except Exception as e:
                    logger.warning(f"向会话 {session_id} 发送消息失败: {e}")
                    session_info.connected = False
                    # 异步移除会话
                    asyncio.create_task(self.remove_session(session_id))
    
    async def broadcast_to_request(self, request_id: str, message: Dict[str, Any]):
        """根据request_id向对应会话发送消息"""
        if request_id in self.request_to_session:
            session_id = self.request_to_session[request_id]
            await self.broadcast_to_session(session_id, message)
        else:
            logger.warning(f"未找到request_id {request_id} 对应的会话")
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """向所有活跃会话发送消息"""
        disconnected_sessions = []
        
        for session_id, session_info in self.sessions.items():
            if session_info.connected:
                try:
                    await session_info.websocket.send_json(message)
                    session_info.last_active = datetime.now()
                except Exception as e:
                    logger.warning(f"向会话 {session_id} 发送消息失败: {e}")
                    session_info.connected = False
                    disconnected_sessions.append(session_id)
        
        # 异步移除断开的会话
        for session_id in disconnected_sessions:
            asyncio.create_task(self.remove_session(session_id))
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        return self.sessions.get(session_id)
    
    def get_active_sessions(self) -> List[str]:
        """获取活跃会话列表"""
        return [sid for sid, info in self.sessions.items() if info.connected]
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        active_sessions = len([s for s in self.sessions.values() if s.connected])
        total_requests = len(self.request_to_session)
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "total_requests": total_requests,
            "max_sessions": config.MAX_SESSIONS,
            "session_timeout": config.SESSION_TIMEOUT
        }
    
    async def handle_websocket_message(self, session_id: str, message: Dict[str, Any]):
        """处理来自前端的WebSocket消息"""
        if session_id in self.sessions:
            self.sessions[session_id].last_active = datetime.now()
            
            # 处理不同类型的消息
            message_type = message.get("type")
            
            if message_type == "ping":
                # 心跳消息
                await self.broadcast_to_session(session_id, {"type": "pong"})
            elif message_type == "subscribe":
                # 订阅request_id更新
                request_id = message.get("request_id")
                if request_id:
                    self.associate_request(session_id, request_id)
            elif message_type == "unsubscribe":
                # 取消订阅request_id
                request_id = message.get("request_id") 
                if request_id:
                    self.disassociate_request(request_id)
            else:
                logger.debug(f"收到未知消息类型: {message_type}")
    
    async def shutdown(self):
        """关闭会话管理器"""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
        
        # 关闭所有会话
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.remove_session(session_id)
        
        logger.info("会话管理器已关闭")

# 全局会话管理器实例
session_manager = SessionManager()