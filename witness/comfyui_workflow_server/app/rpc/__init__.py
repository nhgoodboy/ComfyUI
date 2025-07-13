"""
RPC模块

提供JSON-RPC风格的API接口，替代原有的RESTful API
"""

from .handler import RPCHandler
from .router import RPCRouter
from .exceptions import RPCError, RPCMethodNotFound, RPCInvalidParams
from .error_codes import ErrorCodes

__all__ = [
    "RPCHandler",
    "RPCRouter", 
    "RPCError",
    "RPCMethodNotFound",
    "RPCInvalidParams",
    "ErrorCodes"
]