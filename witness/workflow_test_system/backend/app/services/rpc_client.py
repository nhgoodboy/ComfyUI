"""
ComfyUIÂ\A°hRPC¢7Ô
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
    """ComfyUI RPC¢7Ô"""
    
    def __init__(self):
        self.base_url = config.COMFYUI_WORKFLOW_SERVER_URL.rstrip('/')
        self.rpc_url = f"{self.base_url}/rpc"
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_counter = 0
    
    async def __aenter__(self):
        """e
á°he„"""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=config.WEBSOCKET_TIMEOUT)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """e
á°h˙„"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _generate_request_id(self) -> str:
        """˜BID"""
        self.request_counter += 1
        return f"rpc_{int(time.time() * 1000)}_{self.request_counter}"
    
    async def call(self, method: str, params: Optional[Dict[str, Any]] = None, 
                   request_id: Optional[str] = None) -> Dict[str, Any]:
        """(RPCπ’"""
        if not self.session or self.session.closed:
            raise RuntimeError("RPC¢7Ô*À˜(async withÌÂ")
        
        if params is None:
            params = {}
        
        if request_id is None:
            request_id = self._generate_request_id()
        
        payload = {
            "method": method,
            "params": params,
            "id": request_id
        }
        
        logger.debug(f"RPC(: {method}, ¬p: {params}")
        
        try:
            async with self.session.post(self.rpc_url, json=payload) as response:
                if not response.ok:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                result = await response.json()
                
                if "error" in result:
                    error = result["error"]
                    error_msg = f"RPCÔ [{error['code']}]: {error['message']}"
                    if "data" in error:
                        error_msg += f" - {error['data']}"
                    raise Exception(error_msg)
                
                logger.debug(f"RPCÕî: {method} -> ü")
                return result["result"]
                
        except aiohttp.ClientError as e:
            logger.error(f"RPCQ‹Ô: {method} - {e}")
            raise Exception(f"Q‹ﬁ•1%: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"RPCÕî„êÔ: {method} - {e}")
            raise Exception(f"Õî<Ô: {str(e)}")
    
    # Â\A¯sπ’
    async def execute_workflow(self, request_id: str, workflow_id: str, 
                             params: Dict[str, Any]) -> Dict[str, Any]:
        """gLÂ\A"""
        return await self.call("workflow.execute", {
            "request_id": request_id,
            "workflow_id": workflow_id,
            "params": params
        })
    
    async def get_workflow_status(self, request_id: str) -> Dict[str, Any]:
        """∑÷Â\A∂"""
        return await self.call("workflow.get_status", {
            "request_id": request_id
        })
    
    async def get_workflow_result(self, request_id: str) -> Dict[str, Any]:
        """∑÷Â\A”ú"""
        return await self.call("workflow.get_result", {
            "request_id": request_id
        })
    
    async def cancel_workflow(self, request_id: str) -> Dict[str, Any]:
        """÷àÂ\A"""
        return await self.call("workflow.cancel", {
            "request_id": request_id
        })
    
    async def list_workflows(self) -> Dict[str, Any]:
        """∑÷Â\Ah"""
        return await self.call("workflow.list")
    
    async def get_workflow_schema(self, workflow_id: str) -> Dict[str, Any]:
        """∑÷Â\A¬p!"""
        return await self.call("workflow.get_schema", {
            "workflow_id": workflow_id
        })
    
    async def search_workflows(self, query: Optional[str] = None) -> Dict[str, Any]:
        """"Â\A"""
        params = {}
        if query:
            params["query"] = query
        return await self.call("workflow.search", params)
    
    # áˆ¯sπ’
    async def get_output_image(self, filename: str) -> Dict[str, Any]:
        """∑÷ì˙˛G"""
        return await self.call("files.get_output_image", {
            "filename": filename
        })
    
    async def get_output_image_info(self, filename: str) -> Dict[str, Any]:
        """∑÷ì˙˛G·o"""
        return await self.call("files.get_output_image_info", {
            "filename": filename
        })
    
    async def list_output_images(self, limit: int = 100, offset: int = 0,
                               pattern: str = "*") -> Dict[str, Any]:
        """˙ì˙˛G"""
        return await self.call("files.list_output_images", {
            "limit": limit,
            "offset": offset,
            "pattern": pattern
        })
    
    # ˚ﬂ¯sπ’
    async def health_check(self) -> Dict[str, Any]:
        """˚ﬂe∑¿Â"""
        return await self.call("system.health")
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """∑÷˚ﬂﬂ°"""
        return await self.call("system.get_stats")
    
    async def parse_filename(self, filename: str) -> Dict[str, Any]:
        """„êáˆ"""
        return await self.call("system.parse_filename", {
            "filename": filename
        })

# h@RPC¢7Ôûã
rpc_client = ComfyUIRPCClient()