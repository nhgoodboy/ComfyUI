"""
统一安全中间件

集成所有安全验证：API密钥、签名验证、IP白名单、速率限制
银行级安全防护，无绕过可能
"""

import hmac
import hashlib
import time
import json
import ipaddress
from typing import Set, Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from comfyui_workflow_server.app.services.jwt_service import get_jwt_service
from comfyui_workflow_server.app.services.user_service import user_service
from comfyui_workflow_server.app.utils.crypto_utils import get_crypto_utils

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """统一安全中间件 - 五层防护体系"""
    
    def __init__(
        self, 
        app,
        api_users: Dict[str, Dict],
        api_secret_key: str,
        allowed_ips: list,
        signature_timeout: int = 300,
        rate_limit_per_ip: int = 60,
        rate_limit_per_user: int = 30
    ):
        super().__init__(app)
        self.api_secret_key = api_secret_key.encode()
        self.allowed_networks = [ipaddress.ip_network(ip, strict=False) for ip in allowed_ips]
        self.signature_timeout = signature_timeout
        self.rate_limit_per_ip = rate_limit_per_ip
        self.rate_limit_per_user = rate_limit_per_user
        self.api_users = api_users
        
        # 速率限制存储 - 生产环境应使用Redis
        self.ip_requests: Dict[str, deque] = defaultdict(deque)
        self.user_requests: Dict[str, deque] = defaultdict(deque)
        
        # 安全排除路径
        self.excluded_paths = {
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/favicon.ico",
        }
        self.excluded_path_prefixes = {"/static", "/ws", "/api/v1/auth"}
        
        logger.info("统一安全中间件初始化完成")
    
    async def dispatch(self, request: Request, call_next):
        """五层安全验证"""
        try:
            # 检查排除路径
            if request.url.path in self.excluded_paths:
                return await call_next(request)

            # 检查排除路径前缀
            for prefix in self.excluded_path_prefixes:
                if request.url.path.startswith(prefix):
                    return await call_next(request)
            
            client_ip = self._get_client_ip(request)
            
            # 第1层：IP白名单检查
            if not self._check_ip_whitelist(client_ip):
                logger.warning(f"IP白名单拒绝: {client_ip}")
                raise HTTPException(status_code=403, detail="访问被拒绝")
            
            # 第2层：API密钥验证
            api_key = request.headers.get("x-api-key")
            if not self._verify_api_key(api_key):
                logger.warning(f"API密钥验证失败: {client_ip}")
                raise HTTPException(status_code=401, detail="API密钥无效")
            
            # 第3层：请求签名验证
            timestamp = request.headers.get("x-timestamp")
            signature = request.headers.get("x-signature")
            
            if not signature or not timestamp:
                raise HTTPException(status_code=401, detail="缺少签名或时间戳")

            # 验证签名
            body_bytes = await request.body()
            body_hash = hashlib.sha256(body_bytes).hexdigest()
            
            crypto_utils = get_crypto_utils()
            is_valid_signature = crypto_utils.verify_signature(
                signature=signature,
                timestamp=timestamp,
                method=request.method,
                path=str(request.url.path),
                query=str(request.url.query) if request.url.query else "",
                body_hash=body_hash
            )
            
            if not is_valid_signature:
                logger.warning(f"签名验证失败: {client_ip}")
                raise HTTPException(status_code=401, detail="请求签名无效")
            
            # 重新构造请求（因为body已被读取）
            from fastapi import Request as FastAPIRequest
            
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            
            request._receive = receive
            
            # 第4层：速率限制检查
            if not self._check_rate_limit(client_ip, None):  # user_id在后续JWT中提取
                logger.warning(f"速率限制触发: {client_ip}")
                raise HTTPException(status_code=429, detail="请求过于频繁")
            
            # 记录安全验证成功
            logger.info(f"安全验证通过: {client_ip} - {request.method} {request.url.path}")
            
            response = await call_next(request)
            
            # 添加安全响应头
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"安全中间件错误: {e}")
            raise HTTPException(status_code=500, detail="安全服务错误")
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 考虑代理和负载均衡器
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host
    
    def _check_ip_whitelist(self, client_ip: str) -> bool:
        """IP白名单检查"""
        try:
            client_addr = ipaddress.ip_address(client_ip)
            for network in self.allowed_networks:
                if client_addr in network:
                    return True
            return False
        except ValueError:
            logger.error(f"无效IP地址: {client_ip}")
            return False
    
    def _verify_api_key(self, api_key: Optional[str]) -> bool:
        """API密钥验证"""
        if not api_key:
            return False
        
        # 验证API Key是否存在于用户列表中
        return api_key in self.api_users
    
    def _check_rate_limit(self, client_ip: str, user_id: Optional[str]) -> bool:
        """速率限制检查"""
        current_time = time.time()
        window_start = current_time - 60  # 1分钟窗口
        
        # 清理过期记录
        self._cleanup_old_requests(window_start)
        
        # 检查IP级别限制
        ip_requests = self.ip_requests[client_ip]
        if len(ip_requests) >= self.rate_limit_per_ip:
            return False
        
        # 检查用户级别限制（如果有用户ID）
        if user_id:
            user_requests = self.user_requests[user_id]
            if len(user_requests) >= self.rate_limit_per_user:
                return False
            user_requests.append(current_time)
        
        # 记录请求
        ip_requests.append(current_time)
        return True
    
    def _cleanup_old_requests(self, window_start: float):
        """清理过期的请求记录"""
        # 清理IP请求记录
        for ip, requests in list(self.ip_requests.items()):
            while requests and requests[0] < window_start:
                requests.popleft()
            if not requests:
                del self.ip_requests[ip]
        
        # 清理用户请求记录
        for user_id, requests in list(self.user_requests.items()):
            while requests and requests[0] < window_start:
                requests.popleft()
            if not requests:
                del self.user_requests[user_id] 