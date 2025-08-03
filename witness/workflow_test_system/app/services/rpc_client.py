"""
ComfyUI工作流服务器RPC客户端
"""

import asyncio
import aiohttp
import json
import logging
import time
from typing import Dict, Any, Optional
from ..config import config

logger = logging.getLogger(__name__)

class ComfyUIRPCClient:
    """ComfyUI RPC客户端"""
    
    def __init__(self):
        self.base_url = config.COMFYUI_WORKFLOW_SERVER_URL.rstrip('/')
        self.rpc_url = f"{self.base_url}/rpc"
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_counter = 0
    
    async def __aenter__(self):
        """异步上下文管理器进入"""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=config.WEBSOCKET_TIMEOUT)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _generate_request_id(self) -> str:
        """生成请求ID"""
        self.request_counter += 1
        return f"rpc_{int(time.time() * 1000)}_{self.request_counter}"
    
    async def call(self, method: str, params: Optional[Dict[str, Any]] = None, 
                   request_id: Optional[str] = None) -> Dict[str, Any]:
        """调用RPC方法"""
        if not self.session or self.session.closed:
            raise RuntimeError("RPC客户端未初始化，请使用async with语句")
        
        if params is None:
            params = {}
        
        if request_id is None:
            request_id = self._generate_request_id()
        
        payload = {
            "method": method,
            "params": params,
            "id": request_id
        }
        
        logger.debug(f"RPC调用: {method}, 参数: {params}")
        
        try:
            async with self.session.post(self.rpc_url, json=payload) as response:
                if not response.ok:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                result = await response.json()
                
                if "error" in result:
                    error = result["error"]
                    error_msg = f"RPC错误 [{error['code']}]: {error['message']}"
                    if "data" in error:
                        error_msg += f" - {error['data']}"
                    raise Exception(error_msg)
                
                logger.debug(f"RPC响应: {method} -> 成功")
                return result["result"]
                
        except aiohttp.ClientError as e:
            logger.error(f"RPC网络错误: {method} - {e}")
            raise Exception(f"网络连接失败: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"RPC响应解析错误: {method} - {e}")
            raise Exception(f"响应格式错误: {str(e)}")
    
    # 工作流相关方法
    async def execute_workflow(self, request_id: str, workflow_id: str, 
                             params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流"""
        return await self.call("workflow.execute", {
            "request_id": request_id,
            "workflow_id": workflow_id,
            "params": params
        })
    
    async def get_workflow_status(self, request_id: str) -> Dict[str, Any]:
        """获取工作流状态"""
        return await self.call("workflow.get_status", {
            "request_id": request_id
        })
    
    async def get_workflow_result(self, request_id: str) -> Dict[str, Any]:
        """获取工作流结果"""
        return await self.call("workflow.get_result", {
            "request_id": request_id
        })
    
    async def cancel_workflow(self, request_id: str) -> Dict[str, Any]:
        """取消工作流"""
        return await self.call("workflow.cancel", {
            "request_id": request_id
        })
    
    async def list_workflows(self) -> Dict[str, Any]:
        """列出工作流"""
        return await self.call("workflow.list")
    
    async def get_workflow_schema(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流参数模式"""
        return await self.call("workflow.get_schema", {
            "workflow_id": workflow_id
        })
    
    async def search_workflows(self, query: Optional[str] = None) -> Dict[str, Any]:
        """搜索工作流"""
        params = {}
        if query:
            params["query"] = query
        return await self.call("workflow.search", params)
    
    # 文件相关方法
    async def get_output_image(self, filename: str) -> Dict[str, Any]:
        """获取输出图像"""
        return await self.call("files.get_output_image", {
            "filename": filename
        })
    
    async def get_output_image_info(self, filename: str) -> Dict[str, Any]:
        """获取输出图像信息"""
        return await self.call("files.get_output_image_info", {
            "filename": filename
        })
    
    async def list_output_images(self, limit: int = 100, offset: int = 0,
                               pattern: str = "*") -> Dict[str, Any]:
        """列出输出图像"""
        return await self.call("files.list_output_images", {
            "limit": limit,
            "offset": offset,
            "pattern": pattern
        })
    
    # 系统相关方法
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return await self.call("system.health")
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        return await self.call("system.get_stats")

# 全局RPC客户端实例
rpc_client = ComfyUIRPCClient()