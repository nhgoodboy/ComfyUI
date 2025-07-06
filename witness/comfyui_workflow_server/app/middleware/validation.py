"""
输入验证中间件

提供全面的输入数据验证，确保API调用的安全性和数据质量。
"""

import re
import aiohttp
import logging
from typing import Optional
from urllib.parse import urlparse
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

from ..config import get_settings
from ..models.api_models import ErrorResponse

logger = logging.getLogger(__name__)

class ValidationMiddleware(BaseHTTPMiddleware):
    """输入验证中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        self.max_file_size = settings.storage.max_file_size
        self.allowed_extensions = settings.storage.allowed_extensions
        
    async def dispatch(self, request: StarletteRequest, call_next):
        """处理请求验证"""
        try:
            # 只对API端点进行验证
            if request.url.path.startswith("/api/v1"):
                await self._validate_request(request)
            
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail
            )
        except Exception as e:
            logger.error(f"验证中间件错误: {e}")
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error_code="VALIDATION_ERROR",
                    error_message="请求验证失败"
                ).dict()
            )
    
    async def _validate_request(self, request: StarletteRequest):
        """验证请求数据"""
        # 验证Content-Type
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error_code="INVALID_CONTENT_TYPE",
                        error_message="请求必须使用 application/json 格式"
                    ).dict()
                )
        
        # 验证请求体大小
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=413,
                detail=ErrorResponse(
                    error_code="REQUEST_TOO_LARGE",
                    error_message="请求体过大，最大允许10MB"
                ).dict()
            )
        
        # 获取请求体进行基本验证
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    import json
                    data = json.loads(body)
                    await self._validate_common_data(data)
                    
                    # 重新设置请求体以供后续处理使用
                    request._body = body
                    
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error_code="INVALID_JSON",
                        error_message="请求体不是有效的JSON格式"
                    ).dict()
                )
    
    async def _validate_common_data(self, data: dict):
        """验证通用请求数据"""
        # 验证工作流ID（如果存在）
        workflow_id = data.get("workflow_id")
        if workflow_id and not isinstance(workflow_id, str):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_WORKFLOW_ID",
                    error_message="workflow_id 必须是字符串类型"
                ).dict()
            )
        
        # 验证参数对象（如果存在）
        parameters = data.get("parameters")
        if parameters and not isinstance(parameters, dict):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_PARAMETERS",
                    error_message="parameters 必须是对象类型"
                ).dict()
            )
        
        # 验证图像URL（如果存在）
        if parameters and isinstance(parameters, dict):
            for key, value in parameters.items():
                if key.endswith("_url") and value:
                    await self._validate_image_url(value)
    
    async def _validate_image_url(self, url: str):
        """验证图像URL的安全性和可访问性"""
        
        if not url or not isinstance(url, str):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_IMAGE_URL",
                    error_message="图像URL必须是有效的URL字符串"
                ).dict()
            )
        
        # 验证URL格式
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("URL格式无效")
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_URL_FORMAT",
                    error_message="URL格式无效"
                ).dict()
            )
        
        # 只允许HTTP和HTTPS协议
        if parsed.scheme not in ["http", "https"]:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="UNSUPPORTED_PROTOCOL",
                    error_message="只支持HTTP和HTTPS协议"
                ).dict()
            )
        
        # 防止访问内网地址（SSRF攻击防护）
        hostname = parsed.hostname
        if hostname:
            import ipaddress
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise HTTPException(
                        status_code=400,
                        detail=ErrorResponse(
                            error_code="PRIVATE_IP_NOT_ALLOWED",
                            error_message="不允许访问内网地址"
                        ).dict()
                    )
            except ipaddress.AddressValueError:
                # 域名情况，检查是否为本地域名
                if hostname in ["localhost", "127.0.0.1", "0.0.0.0"] or hostname.endswith(".local"):
                    raise HTTPException(
                        status_code=400,
                        detail=ErrorResponse(
                            error_code="LOCAL_ADDRESS_NOT_ALLOWED",
                            error_message="不允许访问本地地址"
                        ).dict()
                    )
        
        # 验证URL长度
        if len(url) > 2048:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="URL_TOO_LONG",
                    error_message="URL长度不能超过2048个字符"
                ).dict()
            )
    
    async def _check_image_accessibility(self, url: str):
        """检查图像是否可访问（可选功能）"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=400,
                            detail=ErrorResponse(
                                error_code="IMAGE_NOT_ACCESSIBLE",
                                error_message=f"图像不可访问，状态码: {response.status}"
                            ).dict()
                        )
        except aiohttp.ClientError as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="IMAGE_ACCESS_ERROR",
                    error_message=f"图像访问错误: {e}"
                ).dict()
            ) 