"""
RPC请求处理器

负责处理所有RPC请求的核心组件
"""

import json
import logging
import traceback
from typing import Any, Dict
from fastapi import Request
from .router import rpc_router
from .protocol import RPCRequest, RPCResponse
from .validator import RPCValidator
from .formatter import RPCFormatter
from .exceptions import RPCError, RPCInternalError, RPCMethodNotFound, RPCInvalidParams
from .error_codes import ErrorCodes

logger = logging.getLogger(__name__)


class RPCHandler:
    """RPC请求处理器"""
    
    def __init__(self):
        self.validator = RPCValidator()
        self.formatter = RPCFormatter()
    
    async def handle_request(self, request: Request, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个RPC请求"""
        request_id = request_data.get("id", "unknown")
        
        try:
            # 解析RPC请求
            rpc_request = self._parse_request(request_data)
            
            # 获取方法处理器
            handler = rpc_router.get_handler(rpc_request.method)
            
            # 执行方法（过滤健康检查日志）
            if rpc_request.method != "system.health":
                logger.info(f"执行RPC方法: {rpc_request.method}, 请求ID: {request_id}, 参数: {rpc_request.params}")
            result = await self._execute_method(handler, rpc_request.params, request)
            
            # 格式化成功响应
            return self.formatter.format_success(result, request_id)
            
        except RPCError as e:
            logger.warning(f"RPC业务错误: {e.message}, 请求ID: {request_id}", exc_info=True)
            return self.formatter.format_error(e.code, e.message, request_id, e.data)
            
        except Exception as e:
            logger.error(f"RPC内部错误: {str(e)}, 请求ID: {request_id}", exc_info=True)
            return self.formatter.format_error(
                ErrorCodes.INTERNAL_ERROR,
                "内部服务器错误",
                request_id,
                {"error": str(e), "traceback": traceback.format_exc()}
            )
    
    async def handle_batch_request(self, request: Request, batch_data: list) -> list:
        """处理批量RPC请求"""
        responses = []
        
        for request_data in batch_data:
            response = await self.handle_request(request, request_data)
            responses.append(response)
        
        return responses
    
    def _parse_request(self, request_data: Dict[str, Any]) -> RPCRequest:
        """解析RPC请求"""
        try:
            return RPCRequest(**request_data)
        except Exception as e:
            raise RPCInvalidParams(f"请求格式无效: {str(e)}")
    
    async def _execute_method(self, handler, params: Dict[str, Any], request: Request) -> Any:
        """执行RPC方法"""
        try:
            # 检查方法是否是协程
            import inspect
            if inspect.iscoroutinefunction(handler):
                return await handler(params, request)
            else:
                return handler(params, request)
        except RPCError:
            # RPC业务异常直接抛出
            raise
        except Exception as e:
            # 其他异常包装为RPC内部错误
            raise RPCInternalError(f"方法执行失败: {str(e)}", e)


# 全局处理器实例
rpc_handler = RPCHandler()