"""
RPC风格的转换服务

基于新的RPC接口重构转换服务，支持文件URL上传和实时状态推送
"""

import asyncio
import logging
import os
import uuid
import time
import aiofiles
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

from app.client.rpc_client import ComfyUIRPCClient, ComfyUIWebSocketClient
from app.config import settings

logger = logging.getLogger(__name__)


class TransformService:
    """转换服务 - 基于RPC接口，一对一连接，支持多用户"""
    
    def __init__(self):
        # 单一的RPC和WebSocket客户端（一对一连接）
        self.rpc_client: Optional[ComfyUIRPCClient] = None
        self.ws_client: Optional[ComfyUIWebSocketClient] = None
        
        # 连接管理器，用于向前端推送消息
        self.connection_manager = None
        
        # 用户到前端用户的映射
        self.user_to_frontend: Dict[str, str] = {}  # user_id -> frontend_user_id
        
        # 使用一个服务级别的标识符（仅用于WebSocket连接）
        self.service_id = "web_image_transform_service"
        
        # 确保目录存在
        self.uploads_dir = Path(settings.UPLOAD_DIR)
        self.outputs_dir = Path(settings.OUTPUT_DIR)
        self.uploads_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        
        logger.info("转换服务初始化完成")
    
    def set_connection_manager(self, manager):
        """设置连接管理器"""
        self.connection_manager = manager
    
    async def initialize(self):
        """初始化单一的RPC客户端和WebSocket连接"""
        try:
            # 创建单一的RPC客户端（使用服务级别标识符）
            self.rpc_client = ComfyUIRPCClient(
                base_url=settings.COMFYUI_WORKFLOW_SERVER_URL,
                service_id=self.service_id
            )
            
            # 测试连接
            async with self.rpc_client:
                health = await self.rpc_client.get_system_health()
                logger.info(f"ComfyUI服务状态: {health.get('status', 'unknown')}")
            
            # 创建单一的WebSocket客户端
            ws_url = f"{settings.COMFYUI_WORKFLOW_SERVER_URL.replace('http', 'ws')}/ws/{self.service_id}"
            self.ws_client = ComfyUIWebSocketClient(ws_url, self._handle_ws_message)
            
            # 启动WebSocket监听器
            await self.start_push_listener()
            
            logger.info("转换服务初始化完成（一对一连接模式）")
            
        except Exception as e:
            logger.error(f"转换服务初始化失败: {e}")
            raise
    
    async def check_and_reconnect_if_needed(self):
        """检查连接状态，如果需要则重连"""
        try:
            # 检查WebSocket连接状态
            if not self.ws_client or not self.ws_client.connected:
                logger.warning("WebSocket连接已断开，尝试重新连接...")
                await self.start_push_listener()
            
            # 检查RPC连接状态
            if self.rpc_client:
                async with self.rpc_client:
                    await self.rpc_client.get_system_health()
                    
        except Exception as e:
            logger.warning(f"连接检查失败，尝试重新初始化: {e}")
            try:
                await self.initialize()
            except Exception as init_e:
                logger.error(f"重新初始化失败: {init_e}")
                raise
    
    def register_user(self, user_id: str, frontend_user_id: str):
        """注册用户到前端用户的映射"""
        self.user_to_frontend[user_id] = frontend_user_id
        logger.info(f"用户 {user_id} 已注册，映射到前端用户 {frontend_user_id}")
    
    async def start_push_listener(self):
        """启动WebSocket推送监听器"""
        if self.ws_client:
            await self.ws_client.connect()
            logger.info("WebSocket推送监听器已启动（一对一连接模式）")
    
    async def stop_push_listener(self):
        """停止WebSocket推送监听器"""
        if self.ws_client:
            try:
                await self.ws_client.close()
                logger.info("WebSocket连接已关闭")
            except Exception as e:
                logger.error(f"关闭WebSocket连接失败: {e}")
        
        logger.info("WebSocket推送监听器已停止")
    
    async def _handle_ws_message(self, data: Dict[str, Any]):
        """处理WebSocket消息（一对一连接模式）"""
        try:
            logger.debug(f"收到任务更新: {data}")
            
            # 转发消息给对应的前端客户端
            if self.connection_manager:
                # 提取实际的任务数据 - 数据在data.data中
                task_data = data.get("data", {})
                
                # 从任务数据中获取user_id来确定推送目标
                task_user_id = task_data.get("user_id")
                
                # 构造前端期待的嵌套数据结构
                frontend_data = {
                    "type": "task_update",
                    "request_id": data.get("request_id"),  # request_id在顶层
                    "data": {
                        "status": task_data.get("status"),
                        "progress": task_data.get("progress", 0),
                        "message": task_data.get("message", ""),
                        "stage": task_data.get("stage", "unknown"),
                        "timestamp": task_data.get("timestamp"),
                        "files": task_data.get("files", {}),
                        "style_id": task_data.get("style_id"),
                        "user_id": task_data.get("user_id"),
                        "request_id": task_data.get("request_id")
                    }
                }
                
                # 如果任务完成，添加结果信息
                if task_data.get("status") == "completed" and "result" in task_data:
                    frontend_data["data"]["result"] = task_data["result"]
                
                # 根据任务中的user_id找到对应的前端用户并发送消息
                if task_user_id:
                    frontend_user_id = self.user_to_frontend.get(task_user_id)
                    if frontend_user_id:
                        success = await self.connection_manager.send_json(frontend_user_id, frontend_data)
                        if success:
                            logger.info(f"成功推送任务更新到用户 {task_user_id} 的前端用户 {frontend_user_id}")
                        else:
                            logger.warning(f"推送任务更新失败: 用户 {task_user_id}, 前端用户 {frontend_user_id}")
                    else:
                        logger.warning(f"找不到用户 {task_user_id} 对应的前端用户")
                else:
                    logger.warning("任务数据中缺少user_id，无法确定推送目标")
                
        except Exception as e:
            logger.error(f"处理WebSocket消息失败: {e}")
    
    async def _send_to_task_owner(self, data: Dict[str, Any]):
        """发送消息给任务所有者"""
        if not self.connection_manager:
            return
        
        request_id = data.get("request_id")
        if not request_id:
            logger.warning("消息中缺少request_id，无法确定任务所有者")
            return
        
        # 发送给特定任务的所有者
        success = await self.connection_manager.send_to_task_owner(request_id, data)
        if success:
            logger.info(f"成功推送任务更新到任务所有者: {request_id}")
        else:
            logger.warning(f"推送任务更新失败: {request_id}")
            # 如果找不到任务所有者，可能是旧的广播模式兼容
            logger.info("尝试广播模式作为后备方案")
            await self._broadcast_to_clients_fallback(data)
    
    async def _broadcast_to_clients_fallback(self, data: Dict[str, Any]):
        """广播消息给所有前端客户端（后备方案）"""
        if not self.connection_manager:
            return
        
        # 获取所有连接的用户ID并广播
        for user_id in list(self.connection_manager.active_connections.keys()):
            success = await self.connection_manager.send_json(user_id, data)
            if not success:
                logger.warning(f"向用户 {user_id} 发送消息失败")
    
    async def get_styles(self, user_id: str = None) -> List[Dict[str, Any]]:
        """获取所有可用风格"""
        try:
            # 确保RPC客户端已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 使用单一的RPC客户端
            async with self.rpc_client:
                result = await self.rpc_client.get_styles()
                return result.get("styles", [])
        except Exception as e:
            logger.error(f"获取风格列表失败: {e}")
            # 如果是连接错误，尝试重新初始化
            if "网络连接失败" in str(e) or "Connection" in str(e):
                logger.info("检测到连接问题，尝试重新初始化服务...")
                try:
                    await self.initialize()
                except Exception as init_e:
                    logger.error(f"重新初始化失败: {init_e}")
            raise
    
    async def search_styles(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """搜索风格"""
        try:
            # 确保RPC客户端已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 使用单一的RPC客户端
            async with self.rpc_client:
                result = await self.rpc_client.search_styles(query)
                return result.get("styles", [])
        except Exception as e:
            logger.error(f"搜索风格失败: {e}")
            raise
    
    async def save_uploaded_file(self, user_id: str, file_content: bytes, filename: str, style_id: str, request_id: str = None) -> str:
        """
        保存上传的文件并按照RPC规范命名
        
        Args:
            user_id: 用户ID
            file_content: 文件内容
            filename: 原始文件名
            style_id: 风格ID
            request_id: 请求ID (如果为None则自动生成)
        
        Returns:
            str: 文件访问URL
        """
        try:
            # request_id应该由调用者提供
            if not request_id:
                raise ValueError("request_id是必需的")
            
            # 确保RPC客户端已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 获取文件扩展名
            file_ext = Path(filename).suffix.lower()
            if not file_ext:
                file_ext = ".jpg"
            
            # 使用单一的RPC客户端生成符合规范的文件名，传递实际的user_id
            async with self.rpc_client:
                filename_info = await self.rpc_client.build_filename(
                    style_id=style_id,
                    request_id=request_id,
                    file_type="input",
                    extension=file_ext[1:],  # 去掉点号
                    actual_user_id=user_id  # 传递实际的用户ID用于文件命名
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
    
    async def create_transform_task(self, user_id: str, style_id: str, image_url: str, request_id: str = None) -> Dict[str, Any]:
        """
        创建转换任务
        
        Args:
            user_id: 用户ID
            style_id: 风格ID
            image_url: 图片URL
            request_id: 请求ID (如果为None则自动生成)
        
        Returns:
            Dict: 任务信息
        """
        try:
            # request_id应该由调用者提供
            if not request_id:
                raise ValueError("request_id是必需的")
            
            # 确保RPC客户端已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 使用单一的RPC客户端，但传递实际的user_id
            async with self.rpc_client:
                # 传递实际的user_id给RPC客户端
                result = await self.rpc_client.create_transform(
                    style_id=style_id, 
                    image_url=image_url, 
                    request_id=request_id,
                    actual_user_id=user_id  # 传递实际的用户ID
                )
                
                logger.info(f"转换任务已创建: {result.get('request_id')} (user_id: {user_id}, request_id: {request_id})")
                return result
                
        except Exception as e:
            logger.error(f"创建转换任务失败: {e}")
            raise
    
    async def get_task_status(self, user_id: str, request_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            # 确保RPC客户端已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 使用单一的RPC客户端
            async with self.rpc_client:
                return await self.rpc_client.get_task_status(request_id, actual_user_id=user_id)
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            raise
    
    async def get_task_result(self, user_id: str, request_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        try:
            # 确保RPC客户端已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 使用单一的RPC客户端
            async with self.rpc_client:
                return await self.rpc_client.get_task_result(request_id, actual_user_id=user_id)
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            raise
    
    async def list_user_tasks(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户任务列表"""
        try:
            # 确保RPC客户端已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 使用单一的RPC客户端
            async with self.rpc_client:
                result = await self.rpc_client.list_tasks(limit=limit, actual_user_id=user_id)
                return result.get("tasks", [])
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            raise
    
    async def cancel_task(self, user_id: str, request_id: str) -> bool:
        """取消任务"""
        try:
            # 确保RPC客户端已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 使用单一的RPC客户端
            async with self.rpc_client:
                result = await self.rpc_client.cancel_task(request_id, actual_user_id=user_id)
                return result.get("success", False)
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False
    
    async def get_system_health(self, user_id: str = None) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            # 确保RPC客户端已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 使用单一的RPC客户端
            async with self.rpc_client:
                return await self.rpc_client.get_system_health()
        except Exception as e:
            logger.error(f"获取系统健康状态失败: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def transform_image(self, user_id: str, file_contents: List[bytes], file_names: List[str], 
                             style_id: str, request_id: str = None, mode: str = 'single') -> Dict[str, Any]:
        """
        完整的图像转换流程（上传文件 + 创建任务）
        
        Args:
            user_id: 用户ID
            file_contents: 文件内容列表
            file_names: 文件名列表
            style_id: 风格ID
            request_id: 请求ID (可选)
            mode: 上传模式 ('single' 或 'dual')
        
        Returns:
            Dict: 任务信息
        """
        try:
            # 确保使用同一个request_id
            if not request_id:
                request_id = f"req_{int(time.time())}_{str(uuid.uuid4())[:8]}"
                logger.info(f"生成统一request_id: {request_id}")
            
            logger.info(f"开始图像转换流程 - user_id: {user_id}, mode: {mode}, 文件数量: {len(file_contents)}")
            
            # 1. 保存文件并生成标准URL
            file_urls = []
            for idx, (content, filename) in enumerate(zip(file_contents, file_names)):
                # 生成唯一文件名
                file_ext = Path(filename).suffix.lower() or '.jpg'
                if mode == 'dual':
                    unique_filename = f"{request_id}_image{idx + 1}{file_ext}"
                else:
                    unique_filename = f"{request_id}{file_ext}"
                
                file_path = self.uploads_dir / unique_filename
                
                # 异步保存文件
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)
                
                # 生成标准URL
                file_url = urljoin(settings.BASE_URL, f"/static/uploads/{unique_filename}")
                file_urls.append(file_url)
                logger.info(f"文件{idx + 1}已保存: {unique_filename} -> {file_url}")
            
            # 2. 调用RPC接口创建转换任务
            task_data = await self._create_transform_task_rpc(
                user_id=user_id,
                file_urls=file_urls,
                style_id=style_id,
                request_id=request_id,
                mode=mode
            )
            
            logger.info(f"转换任务创建成功: {task_data}")
            return task_data
            
        except Exception as e:
            logger.error(f"图像转换失败: {e}")
            raise
    
    async def _create_transform_task_rpc(self, user_id: str, file_urls: List[str], style_id: str, 
                                        request_id: str, mode: str) -> Dict[str, Any]:
        """
        通过RPC创建转换任务
        
        Args:
            user_id: 用户ID
            file_urls: 文件URL列表
            style_id: 风格ID
            request_id: 请求ID
            mode: 上传模式
        
        Returns:
            Dict: 任务信息
        """
        try:
            # 确保RPC客户端和WebSocket已初始化
            if not self.rpc_client:
                await self.initialize()
            
            # 检查连接状态
            await self.check_and_reconnect_if_needed()
            
            # 注册任务到连接管理器
            if self.connection_manager:
                self.connection_manager.register_task(user_id, request_id)
            
            # 准备RPC调用参数
            if mode == 'dual' and len(file_urls) >= 2:
                # 双图片模式
                params = {
                    "method": "transform.create_dual_image_task",
                    "params": {
                        "user_id": user_id,
                        "image1_url": file_urls[0],
                        "image2_url": file_urls[1],
                        "style_id": style_id,
                        "request_id": request_id
                    }
                }
            else:
                # 单图片模式
                params = {
                    "method": "transform.create_task",
                    "params": {
                        "user_id": user_id,
                        "image_url": file_urls[0],
                        "style_id": style_id,
                        "request_id": request_id
                    }
                }
            
            logger.info(f"发送RPC请求: {params}")
            
            # 发送RPC请求
            async with self.rpc_client:
                result = await self.rpc_client.call_method(
                    method=params["method"],
                    params=params["params"]
                )
            
            logger.info(f"RPC响应: {result}")
            return result
            
        except Exception as e:
            logger.error(f"RPC调用失败: {e}")
            raise
    
    def cleanup_user(self, user_id: str):
        """清理用户映射"""
        if user_id in self.user_to_frontend:
            del self.user_to_frontend[user_id]
            logger.info(f"用户 {user_id} 映射已清理")


# 创建全局转换服务实例
transform_service = TransformService()