"""
ComfyUI Workflow Server RPC客户端

用于与RPC风格的ComfyUI工作流服务器通信
"""

import asyncio
import aiohttp
import json
import logging
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class ComfyUIRPCClient:
    """ComfyUI RPC客户端"""
    
    def __init__(self, base_url: str, user_id: str):
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id
        self.request_id = 0
        self.session: Optional[aiohttp.ClientSession] = None
        
        # RPC端点
        self.rpc_url = f"{self.base_url}/rpc"
        self.ws_url = f"{self.base_url.replace('http', 'ws')}/ws/{user_id}"
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"Content-Type": "application/json"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def call_rpc(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用RPC方法"""
        if params is None:
            params = {}
        
        self.request_id += 1
        payload = {
            "method": method,
            "params": params,
            "id": f"req_{self.request_id}"
        }
        
        logger.debug(f"RPC调用: {method}, 参数: {params}")
        
        try:
            async with self.session.post(self.rpc_url, json=payload) as response:
                result = await response.json()
                
                if "error" in result:
                    error = result["error"]
                    error_msg = f"RPC错误 {error['code']}: {error['message']}"
                    if "data" in error:
                        error_msg += f" - {error['data']}"
                    raise Exception(error_msg)
                
                logger.debug(f"RPC响应: {method} -> {result.get('result', {})}")
                return result["result"]
                
        except aiohttp.ClientError as e:
            logger.error(f"RPC网络错误: {method} - {e}")
            raise Exception(f"网络连接失败: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"RPC响应解析错误: {method} - {e}")
            raise Exception(f"响应格式错误: {str(e)}")
    
    async def batch_call_rpc(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量调用RPC方法"""
        batch_payload = []
        
        for i, call in enumerate(calls):
            method = call["method"]
            params = call.get("params", {})
            
            batch_payload.append({
                "method": method,
                "params": params,
                "id": f"batch_{i}"
            })
        
        logger.debug(f"批量RPC调用: {len(calls)}个请求")
        
        try:
            async with self.session.post(self.rpc_url, json=batch_payload) as response:
                results = await response.json()
                
                processed_results = []
                for result in results:
                    if "error" in result:
                        error = result["error"]
                        processed_results.append({
                            "error": f"RPC错误 {error['code']}: {error['message']}",
                            "data": error.get("data")
                        })
                    else:
                        processed_results.append({"result": result["result"]})
                
                return processed_results
                
        except Exception as e:
            logger.error(f"批量RPC调用失败: {e}")
            raise
    
    # 风格管理方法
    async def get_styles(self) -> Dict[str, Any]:
        """获取所有可用风格"""
        return await self.call_rpc("styles.list")
    
    async def search_styles(self, query: str) -> Dict[str, Any]:
        """搜索风格"""
        return await self.call_rpc("styles.search", {"q": query})
    
    async def get_style(self, style_id: str) -> Dict[str, Any]:
        """获取特定风格详情"""
        return await self.call_rpc("styles.get", {"style_id": style_id})
    
    # 转换任务方法
    async def create_transform(self, style_id: str, image_url: str, request_id: str = None) -> Dict[str, Any]:
        """创建转换任务"""
        # 如果没有提供request_id，自动生成一个
        if not request_id:
            import uuid
            import time
            request_id = f"req_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            logger.debug(f"RPC客户端自动生成request_id: {request_id}")
        
        params = {
            "user_id": self.user_id,
            "style_id": style_id,
            "image_url": image_url,
            "request_id": request_id  # 现在总是包含request_id
        }
        
        return await self.call_rpc("transform.create", params)
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        return await self.call_rpc("transform.get_status", {
            "user_id": self.user_id,
            "task_id": task_id
        })
    
    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        return await self.call_rpc("transform.get_result", {
            "user_id": self.user_id,
            "task_id": task_id
        })
    
    async def list_tasks(self, limit: int = 100, status_filter: List[str] = None) -> Dict[str, Any]:
        """获取任务列表"""
        params = {
            "user_id": self.user_id,
            "limit": limit
        }
        if status_filter:
            params["status_filter"] = status_filter
        
        return await self.call_rpc("transform.list", params)
    
    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务"""
        return await self.call_rpc("transform.cancel", {
            "user_id": self.user_id,
            "task_id": task_id
        })
    
    # 系统方法
    async def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        return await self.call_rpc("system.health")
    
    async def build_filename(self, style_id: str, request_id: str = None, file_type: str = "input", extension: str = "jpg") -> Dict[str, Any]:
        """构建符合规范的文件名"""
        # 如果没有提供request_id，自动生成一个
        if not request_id:
            import uuid
            import time
            request_id = f"req_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            logger.debug(f"RPC客户端自动生成request_id: {request_id}")
        
        params = {
            "style_id": style_id,
            "user_id": self.user_id,
            "request_id": request_id,  # 现在总是包含request_id
            "type": file_type,
            "extension": extension
        }
        
        return await self.call_rpc("system.build_filename", params)
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return await self.call_rpc("system.get_stats")


class ComfyUIWebSocketClient:
    """ComfyUI WebSocket客户端"""
    
    def __init__(self, ws_url: str, message_handler=None):
        self.ws_url = ws_url
        self.message_handler = message_handler
        self.websocket = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 3
    
    async def connect(self):
        """连接WebSocket"""
        try:
            import websockets
            self.websocket = await websockets.connect(self.ws_url)
            self.connected = True
            self.reconnect_attempts = 0
            logger.info(f"WebSocket连接成功: {self.ws_url}")
            
            # 启动消息监听
            asyncio.create_task(self._listen_messages())
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            await self._handle_reconnect()
    
    async def _listen_messages(self):
        """监听WebSocket消息"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    logger.debug(f"收到WebSocket消息: {data}")
                    
                    if self.message_handler:
                        await self.message_handler(data)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"WebSocket消息解析失败: {e}")
                except Exception as e:
                    logger.error(f"WebSocket消息处理失败: {e}")
                    
        except Exception as e:
            logger.error(f"WebSocket监听异常: {e}")
            self.connected = False
            await self._handle_reconnect()
    
    async def _handle_reconnect(self):
        """处理重连"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
            logger.info(f"WebSocket重连尝试 {self.reconnect_attempts}/{self.max_reconnect_attempts}，{delay}秒后重试")
            
            await asyncio.sleep(delay)
            await self.connect()
        else:
            logger.error("WebSocket重连失败，已达到最大重试次数")
    
    async def send_message(self, message: dict):
        """发送消息"""
        if self.connected and self.websocket:
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"WebSocket发送消息失败: {e}")
                self.connected = False
    
    async def send_heartbeat(self):
        """发送心跳"""
        if self.connected:
            await self.send_message({"type": "ping"})
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False