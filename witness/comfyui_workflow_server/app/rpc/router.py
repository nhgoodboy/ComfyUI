"""
RPC方法路由器

负责将RPC方法调用路由到具体的处理函数
"""

import logging
from typing import Any, Callable, Dict, Optional
from .exceptions import RPCMethodNotFound

logger = logging.getLogger(__name__)


class RPCRouter:
    """RPC方法路由器"""
    
    def __init__(self):
        self._methods: Dict[str, Callable] = {}
    
    def register(self, method_name: str, handler: Callable):
        """注册RPC方法"""
        if method_name in self._methods:
            logger.warning(f"方法 '{method_name}' 已存在，将被覆盖")
        
        self._methods[method_name] = handler
        logger.info(f"RPC方法已注册: {method_name}")
    
    def get_handler(self, method_name: str) -> Callable:
        """获取方法处理器"""
        if method_name not in self._methods:
            raise RPCMethodNotFound(method_name)
        
        return self._methods[method_name]
    
    def list_methods(self) -> list[str]:
        """列出所有已注册的方法"""
        return list(self._methods.keys())
    
    def has_method(self, method_name: str) -> bool:
        """检查方法是否存在"""
        return method_name in self._methods


# 全局路由器实例
rpc_router = RPCRouter()


def rpc_method(method_name: str):
    """RPC方法装饰器"""
    def decorator(func: Callable):
        rpc_router.register(method_name, func)
        return func
    return decorator