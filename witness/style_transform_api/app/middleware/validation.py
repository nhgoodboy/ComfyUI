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

from ..config import settings
from ..schemas.response import ErrorResponse

logger = logging.getLogger(__name__)

class ValidationMiddleware(BaseHTTPMiddleware):
    """输入验证中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.max_image_size = settings.MAX_IMAGE_SIZE
        self.allowed_image_types = settings.ALLOWED_IMAGE_TYPES
        
    async def dispatch(self, request: Request, call_next):
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
    
    async def _validate_request(self, request: Request):
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
        
        # 获取请求体进行验证
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    import json
                    data = json.loads(body)
                    await self._validate_request_data(data, request.url.path)
                    
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
    
    async def _validate_request_data(self, data: dict, path: str):
        """验证请求数据内容"""
        
        # 验证图像变换相关的请求
        if "/transform" in path:
            await self._validate_transform_request(data)
    
    async def _validate_transform_request(self, data: dict):
        """验证图像变换请求"""
        
        # 验证user_id
        user_id = data.get("user_id")
        if not user_id or not isinstance(user_id, str) or len(user_id.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_USER_ID",
                    error_message="user_id 必须是非空字符串"
                ).dict()
            )
        
        # 验证user_id长度和格式
        if len(user_id) > 100:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="USER_ID_TOO_LONG",
                    error_message="user_id 长度不能超过100个字符"
                ).dict()
            )
        
        # 验证user_id格式（只允许字母、数字、下划线、连字符）
        if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_USER_ID_FORMAT",
                    error_message="user_id 只能包含字母、数字、下划线和连字符"
                ).dict()
            )
        
        # 验证图像URL
        image_url = data.get("image_url")
        image_urls = data.get("image_urls", [])
        
        urls_to_validate = []
        if image_url:
            urls_to_validate.append(image_url)
        if image_urls:
            urls_to_validate.extend(image_urls)
        
        for url in urls_to_validate:
            await self._validate_image_url(url)
        
        # 验证批量请求的数量限制
        if image_urls and len(image_urls) > 10:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="TOO_MANY_IMAGES",
                    error_message="批量处理最多支持10张图像"
                ).dict()
            )
        
        # 验证strength参数
        strength = data.get("strength")
        if strength is not None:
            if not isinstance(strength, (int, float)) or strength < 0.1 or strength > 1.0:
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error_code="INVALID_STRENGTH",
                        error_message="strength 必须是0.1到1.0之间的数值"
                    ).dict()
                )
        
        # 验证custom_prompt长度
        custom_prompt = data.get("custom_prompt")
        if custom_prompt and len(custom_prompt) > 1000:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="PROMPT_TOO_LONG",
                    error_message="custom_prompt 长度不能超过1000个字符"
                ).dict()
            )
    
    async def _validate_image_url(self, url: str):
        """验证图像URL的安全性和可访问性"""
        
        if not url or not isinstance(url, str):
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_IMAGE_URL",
                    error_message="image_url 必须是有效的URL字符串"
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
        
        # 检查图像URL的可访问性和类型（可选，为了性能考虑可能会跳过）
        if settings.DEBUG:  # 只在调试模式下进行实际检查
            await self._check_image_accessibility(url)
    
    async def _check_image_accessibility(self, url: str):
        """检查图像的可访问性和类型"""
        try:
            async with aiohttp.ClientSession() as session:
                # 只获取头部信息，不下载完整文件
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=400,
                            detail=ErrorResponse(
                                error_code="IMAGE_NOT_ACCESSIBLE",
                                error_message=f"无法访问图像URL: HTTP {response.status}"
                            ).dict()
                        )
                    
                    # 检查Content-Type
                    content_type = response.headers.get("content-type", "").lower()
                    if content_type and not any(allowed in content_type for allowed in self.allowed_image_types):
                        raise HTTPException(
                            status_code=400,
                            detail=ErrorResponse(
                                error_code="UNSUPPORTED_IMAGE_TYPE",
                                error_message=f"不支持的图像类型: {content_type}"
                            ).dict()
                        )
                    
                    # 检查文件大小
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_image_size:
                        raise HTTPException(
                            status_code=400,
                            detail=ErrorResponse(
                                error_code="IMAGE_TOO_LARGE",
                                error_message=f"图像文件过大，最大允许 {self.max_image_size // (1024*1024)}MB"
                            ).dict()
                        )
        
        except aiohttp.ClientError as e:
            logger.warning(f"图像可访问性检查失败: {e}")
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="IMAGE_ACCESSIBILITY_CHECK_FAILED",
                    error_message="无法验证图像URL的可访问性"
                ).dict()
            ) 