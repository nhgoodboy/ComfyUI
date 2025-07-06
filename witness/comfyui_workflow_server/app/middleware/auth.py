"""
API密钥认证中间件

提供基于API密钥的身份验证功能。
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings
from ..schemas.response import ErrorResponse

logger = logging.getLogger(__name__)

class APIKeyMiddleware(BaseHTTPMiddleware):
    """API密钥认证中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.api_key = settings.API_KEY
        self.protected_paths = ["/api/v1"]  # 需要认证的路径前缀
        self.public_paths = ["/", "/health", "/docs", "/redoc", "/openapi.json"]  # 公开路径
        
    async def dispatch(self, request: Request, call_next):
        """处理认证验证"""
        try:
            # 检查是否需要认证
            if self._should_authenticate(request):
                await self._validate_api_key(request)
            
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail
            )
        except Exception as e:
            logger.error(f"认证中间件错误: {e}")
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error_code="AUTH_ERROR",
                    error_message="认证处理失败"
                ).dict()
            )
    
    def _should_authenticate(self, request: Request) -> bool:
        """判断是否需要进行认证"""
        
        # 如果没有配置API密钥，则不进行认证
        if not self.api_key:
            return False
        
        path = request.url.path
        
        # 检查是否为公开路径
        for public_path in self.public_paths:
            if path == public_path or (public_path.endswith("/") and path.startswith(public_path)):
                return False
        
        # 检查是否为受保护路径
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        
        return False
    
    async def _validate_api_key(self, request: Request):
        """验证API密钥"""
        
        # 从请求头获取API密钥
        api_key = self._extract_api_key(request)
        
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail=ErrorResponse(
                    error_code="API_KEY_MISSING",
                    error_message="缺少API密钥，请在请求头中包含 X-API-Key 或 Authorization",
                    details={
                        "headers_required": ["X-API-Key", "Authorization: Bearer <key>"]
                    }
                ).dict()
            )
        
        # 验证API密钥
        if not self._verify_api_key(api_key):
            # 记录认证失败的IP地址用于安全监控
            client_ip = self._get_client_ip(request)
            logger.warning(f"API密钥认证失败，IP: {client_ip}, 密钥: {api_key[:8]}***")
            
            raise HTTPException(
                status_code=401,
                detail=ErrorResponse(
                    error_code="INVALID_API_KEY",
                    error_message="无效的API密钥"
                ).dict()
            )
        
        # 认证成功，记录日志
        client_ip = self._get_client_ip(request)
        logger.debug(f"API密钥认证成功，IP: {client_ip}")
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """从请求中提取API密钥"""
        
        # 方式1: 从 X-API-Key 头部获取
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key.strip()
        
        # 方式2: 从 Authorization 头部获取 (Bearer token)
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip()
        
        # 方式3: 从查询参数获取 (不推荐，但为了兼容性)
        api_key = request.query_params.get("api_key")
        if api_key:
            logger.warning("通过查询参数传递API密钥不安全，建议使用请求头")
            return api_key.strip()
        
        return None
    
    def _verify_api_key(self, api_key: str) -> bool:
        """验证API密钥是否有效"""
        
        # 简单的字符串比较
        # 在生产环境中，建议使用更安全的比较方法和密钥管理
        return api_key == self.api_key
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        
        # 检查代理头部
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For 可能包含多个IP，取第一个
            return forwarded_for.split(",")[0].strip()
        
        # 检查其他代理头部
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # 直接连接的客户端IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"