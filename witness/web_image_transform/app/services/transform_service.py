"""
RPC风格的转换服务

基于新的RPC接口重构转换服务，支持文件URL上传和实时状态推送
"""

import asyncio
import logging
import os
import uuid
import aiofiles
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

from app.client.rpc_client import ComfyUIRPCClient, ComfyUIWebSocketClient
from app.config import settings

logger = logging.getLogger(__name__)


class TransformService:
    """转换服务 - 基于RPC接口"""
    
    def __init__(self):
        self.rpc_client: Optional[ComfyUIRPCClient] = None
        self.ws_client: Optional[ComfyUIWebSocketClient] = None
        self.session_id = str(uuid.uuid4())  # 使用session_id作为user_id
        
        # 连接管理器，用于向前端推送消息
        self.connection_manager = None
        
        # 确保目录存在
        self.uploads_dir = Path(settings.UPLOAD_DIR)
        self.outputs_dir = Path(settings.OUTPUT_DIR)
        self.uploads_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        
        logger.info(f"转换服务初始化，session_id: {self.session_id}")
    
    def set_connection_manager(self, manager):
        """设置连接管理器"""
        self.connection_manager = manager
    
    async def initialize(self):
        """初始化RPC客户端和WebSocket连接"""
        try:
            # 创建RPC客户端
            self.rpc_client = ComfyUIRPCClient(
                base_url=settings.COMFYUI_WORKFLOW_SERVER_URL,
                user_id=self.session_id
            )
            
            # 测试连接
            async with self.rpc_client:
                health = await self.rpc_client.get_system_health()
                logger.info(f"ComfyUI服务状态: {health.get('status', 'unknown')}")
            
            # 创建并启动WebSocket客户端
            ws_url = f"{settings.COMFYUI_WORKFLOW_SERVER_URL.replace('http', 'ws')}/ws/{self.session_id}"
            self.ws_client = ComfyUIWebSocketClient(ws_url, self._handle_ws_message)
            
            # 启动WebSocket监听器
            await self.start_push_listener()
            
            logger.info("转换服务初始化完成（包含WebSocket连接）")
            
        except Exception as e:
            logger.error(f"转换服务初始化失败: {e}")
            raise
    
    async def start_push_listener(self):
        """启动WebSocket推送监听器"""
        if self.ws_client:
            await self.ws_client.connect()
            logger.info("WebSocket推送监听器已启动")
    
    async def stop_push_listener(self):
        """停止WebSocket推送监听器"""
        if self.ws_client:
            await self.ws_client.close()
            logger.info("WebSocket推送监听器已停止")
    
    async def _handle_ws_message(self, data: Dict[str, Any]):
        """处理WebSocket消息"""
        try:
            logger.debug(f"收到任务更新: {data}")
            
            # 转发消息给前端客户端
            if self.connection_manager:
                # 添加一些前端需要的字段
                frontend_data = {
                    "type": "task_update",
                    "task_id": data.get("task_id"),
                    "status": data.get("status"),
                    "progress": data.get("progress", 0),
                    "message": data.get("message", ""),
                    "stage": data.get("stage", "unknown"),
                    "timestamp": data.get("timestamp"),
                    "files": data.get("files", {}),
                    "style_id": data.get("style_id"),
                    "user_id": data.get("user_id")
                }
                
                # 如果任务完成，添加结果信息
                if data.get("status") == "completed" and "result" in data:
                    frontend_data["result"] = data["result"]
                
                # 广播给所有连接的前端客户端
                await self._broadcast_to_clients(frontend_data)
                
        except Exception as e:
            logger.error(f"处理WebSocket消息失败: {e}")
    
    async def _broadcast_to_clients(self, data: Dict[str, Any]):
        """广播消息给所有前端客户端"""
        if not self.connection_manager:
            return
        
        # 获取所有连接的客户端ID并广播
        for client_id in list(self.connection_manager.active_connections.keys()):
            success = await self.connection_manager.send_json(client_id, data)
            if not success:
                logger.warning(f"向客户端 {client_id} 发送消息失败")
    
    async def get_styles(self) -> List[Dict[str, Any]]:
        """获取所有可用风格"""
        try:
            async with self.rpc_client:
                result = await self.rpc_client.get_styles()
                return result.get("styles", [])
        except Exception as e:
            logger.error(f"获取风格列表失败: {e}")
            raise
    
    async def search_styles(self, query: str) -> List[Dict[str, Any]]:
        """搜索风格"""
        try:
            async with self.rpc_client:
                result = await self.rpc_client.search_styles(query)
                return result.get("styles", [])
        except Exception as e:
            logger.error(f"搜索风格失败: {e}")
            raise
    
    async def save_uploaded_file(self, file_content: bytes, filename: str, style_id: str) -> str:
        """
        保存上传的文件并按照RPC规范命名
        
        Args:
            file_content: 文件内容
            filename: 原始文件名
            style_id: 风格ID
        
        Returns:
            str: 文件访问URL
        """
        try:
            # 获取文件扩展名
            file_ext = Path(filename).suffix.lower()
            if not file_ext:
                file_ext = ".jpg"
            
            # 使用RPC客户端生成符合规范的文件名
            async with self.rpc_client:
                filename_info = await self.rpc_client.build_filename(
                    style_id=style_id,
                    file_type="input",
                    extension=file_ext[1:]  # 去掉点号
                )
            
            standard_filename = filename_info["filename"]
            
            # 保存文件
            file_path = self.uploads_dir / standard_filename
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # 生成访问URL
            file_url = f"http://{settings.PUBLIC_HOST}:{settings.APP_PORT}/uploads/{standard_filename}"
            
            logger.info(f"文件已保存: {standard_filename} -> {file_url}")
            return file_url
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            raise
    
    async def create_transform_task(self, style_id: str, image_url: str) -> Dict[str, Any]:
        """
        创建转换任务
        
        Args:
            style_id: 风格ID
            image_url: 图片URL
        
        Returns:
            Dict: 任务信息
        """
        try:
            async with self.rpc_client:
                result = await self.rpc_client.create_transform(style_id, image_url)
                
                logger.info(f"转换任务已创建: {result.get('task_id')}")
                return result
                
        except Exception as e:
            logger.error(f"创建转换任务失败: {e}")
            raise
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            async with self.rpc_client:
                return await self.rpc_client.get_task_status(task_id)
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            raise
    
    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        try:
            async with self.rpc_client:
                return await self.rpc_client.get_task_result(task_id)
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            raise
    
    async def list_user_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户任务列表"""
        try:
            async with self.rpc_client:
                result = await self.rpc_client.list_tasks(limit=limit)
                return result.get("tasks", [])
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            raise
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            async with self.rpc_client:
                result = await self.rpc_client.cancel_task(task_id)
                return result.get("success", False)
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False
    
    async def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            async with self.rpc_client:
                return await self.rpc_client.get_system_health()
        except Exception as e:
            logger.error(f"获取系统健康状态失败: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def transform_image(self, file_content: bytes, filename: str, style_id: str) -> Dict[str, Any]:
        """
        完整的图像转换流程（上传文件 + 创建任务）
        
        Args:
            file_content: 文件内容
            filename: 文件名
            style_id: 风格ID
        
        Returns:
            Dict: 任务信息
        """
        try:
            # 1. 保存文件并生成标准URL
            image_url = await self.save_uploaded_file(file_content, filename, style_id)
            
            # 2. 创建转换任务
            task_info = await self.create_transform_task(style_id, image_url)
            
            # 3. 添加文件信息到响应
            task_info["image_url"] = image_url
            
            return task_info
            
        except Exception as e:
            logger.error(f"图像转换失败: {e}")
            raise
    
    def get_session_id(self) -> str:
        """获取当前会话ID"""
        return self.session_id


# 创建全局转换服务实例
transform_service = TransformService()