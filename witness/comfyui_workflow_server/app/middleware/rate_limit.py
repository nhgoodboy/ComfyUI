"""
限流中间件

提供基于IP和用户的请求限流功能。
"""

import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings
from ..schemas.response import ErrorResponse

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        # 存储每个IP的请求历史: IP -> deque of timestamps
        self.ip_requests: Dict[str, deque] = defaultdict(lambda: deque())
        # 存储每个用户的请求历史: user_id -> deque of timestamps
        self.user_requests: Dict[str, deque] = defaultdict(lambda: deque())
        # 存储每个IP的阻塞状态: IP -> (blocked_until, block_count)
        self.ip_blocks: Dict[str, Tuple[float, int]] = {}
        
        # 配置限流参数
        self.rate_limit_per_minute = 60  # 每分钟最多60个请求
        self.rate_limit_per_hour = 1000  # 每小时最多1000个请求
        self.user_rate_limit_per_minute = 10  # 每个用户每分钟最多10个请求
        self.user_rate_limit_per_hour = 100  # 每个用户每小时最多100个请求
        
        # 阻塞配置
        self.block_duration = 300  # 阻塞时间（秒）
        self.max_violations = 5  # 最大违规次数
        
        # 清理间隔
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5分钟清理一次
        
    async def dispatch(self, request: Request, call_next):
        """处理限流检查"""
        try:
            # 只对API端点进行限流
            if request.url.path.startswith("/api/v1"):
                await self._check_rate_limit(request)
            
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail
            )
        except Exception as e:
            logger.error(f"限流中间件错误: {e}")
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error_code="RATE_LIMIT_ERROR",
                    error_message="限流处理失败"
                ).dict()
            )
    
    async def _check_rate_limit(self, request: Request):
        """检查是否触发限流"""
        
        current_time = time.time()
        client_ip = self._get_client_ip(request)
        
        # 定期清理过期数据
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_data(current_time)
            self.last_cleanup = current_time
        
        # 检查IP是否被阻塞
        if client_ip in self.ip_blocks:
            blocked_until, block_count = self.ip_blocks[client_ip]
            if current_time < blocked_until:
                # 仍在阻塞期间
                remaining_time = int(blocked_until - current_time)
                raise HTTPException(
                    status_code=429,
                    detail=ErrorResponse(
                        error_code="IP_BLOCKED",
                        error_message=f"IP地址被临时阻塞，请{remaining_time}秒后重试",
                        details={
                            "blocked_until": blocked_until,
                            "remaining_seconds": remaining_time,
                            "block_count": block_count
                        }
                    ).dict()
                )
            else:
                # 阻塞期结束，移除阻塞状态
                del self.ip_blocks[client_ip]
        
        # 检查IP限流
        await self._check_ip_rate_limit(client_ip, current_time)
        
        # 检查用户限流（如果请求包含用户信息）
        user_id = await self._extract_user_id(request)
        if user_id:
            await self._check_user_rate_limit(user_id, current_time)
        
        # 记录请求
        self.ip_requests[client_ip].append(current_time)
        if user_id:
            self.user_requests[user_id].append(current_time)
    
    async def _check_ip_rate_limit(self, ip: str, current_time: float):
        """检查IP限流"""
        
        requests = self.ip_requests[ip]
        
        # 清理过期的请求记录
        self._clean_old_requests(requests, current_time)
        
        # 检查每分钟限制
        minute_requests = sum(1 for t in requests if current_time - t <= 60)
        if minute_requests >= self.rate_limit_per_minute:
            self._handle_rate_limit_violation(ip, current_time)
            raise HTTPException(
                status_code=429,
                detail=ErrorResponse(
                    error_code="RATE_LIMIT_EXCEEDED",
                    error_message="请求过于频繁，每分钟最多允许60个请求",
                    details={
                        "limit_type": "per_minute",
                        "current_count": minute_requests,
                        "limit": self.rate_limit_per_minute,
                        "reset_time": current_time + 60
                    }
                ).dict()
            )
        
        # 检查每小时限制
        hour_requests = sum(1 for t in requests if current_time - t <= 3600)
        if hour_requests >= self.rate_limit_per_hour:
            self._handle_rate_limit_violation(ip, current_time)
            raise HTTPException(
                status_code=429,
                detail=ErrorResponse(
                    error_code="RATE_LIMIT_EXCEEDED",
                    error_message="请求过于频繁，每小时最多允许1000个请求",
                    details={
                        "limit_type": "per_hour",
                        "current_count": hour_requests,
                        "limit": self.rate_limit_per_hour,
                        "reset_time": current_time + 3600
                    }
                ).dict()
            )
    
    async def _check_user_rate_limit(self, user_id: str, current_time: float):
        """检查用户限流"""
        
        requests = self.user_requests[user_id]
        
        # 清理过期的请求记录
        self._clean_old_requests(requests, current_time)
        
        # 检查每分钟限制
        minute_requests = sum(1 for t in requests if current_time - t <= 60)
        if minute_requests >= self.user_rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=ErrorResponse(
                    error_code="USER_RATE_LIMIT_EXCEEDED",
                    error_message="用户请求过于频繁，每分钟最多允许10个请求",
                    details={
                        "limit_type": "user_per_minute",
                        "user_id": user_id,
                        "current_count": minute_requests,
                        "limit": self.user_rate_limit_per_minute,
                        "reset_time": current_time + 60
                    }
                ).dict()
            )
        
        # 检查每小时限制
        hour_requests = sum(1 for t in requests if current_time - t <= 3600)
        if hour_requests >= self.user_rate_limit_per_hour:
            raise HTTPException(
                status_code=429,
                detail=ErrorResponse(
                    error_code="USER_RATE_LIMIT_EXCEEDED",
                    error_message="用户请求过于频繁，每小时最多允许100个请求",
                    details={
                        "limit_type": "user_per_hour",
                        "user_id": user_id,
                        "current_count": hour_requests,
                        "limit": self.user_rate_limit_per_hour,
                        "reset_time": current_time + 3600
                    }
                ).dict()
            )
    
    def _handle_rate_limit_violation(self, ip: str, current_time: float):
        """处理限流违规"""
        
        if ip in self.ip_blocks:
            blocked_until, block_count = self.ip_blocks[ip]
            # 增加阻塞次数和时间
            new_block_count = block_count + 1
            new_block_duration = self.block_duration * (2 ** min(new_block_count, 5))  # 指数退避，最多32倍
        else:
            new_block_count = 1
            new_block_duration = self.block_duration
        
        # 设置新的阻塞状态
        self.ip_blocks[ip] = (current_time + new_block_duration, new_block_count)
        
        logger.warning(f"IP {ip} 触发限流，阻塞 {new_block_duration} 秒，违规次数: {new_block_count}")
    
    def _clean_old_requests(self, requests: deque, current_time: float):
        """清理过期的请求记录"""
        
        # 只保留最近1小时的请求
        while requests and current_time - requests[0] > 3600:
            requests.popleft()
    
    def _cleanup_old_data(self, current_time: float):
        """清理过期数据"""
        
        # 清理过期的请求记录
        for ip in list(self.ip_requests.keys()):
            requests = self.ip_requests[ip]
            self._clean_old_requests(requests, current_time)
            # 如果没有请求记录了，删除这个IP
            if not requests:
                del self.ip_requests[ip]
        
        for user_id in list(self.user_requests.keys()):
            requests = self.user_requests[user_id]
            self._clean_old_requests(requests, current_time)
            # 如果没有请求记录了，删除这个用户
            if not requests:
                del self.user_requests[user_id]
        
        # 清理过期的阻塞状态
        for ip in list(self.ip_blocks.keys()):
            blocked_until, _ = self.ip_blocks[ip]
            if current_time >= blocked_until:
                del self.ip_blocks[ip]
        
        logger.debug(f"清理完成，当前跟踪 {len(self.ip_requests)} 个IP，{len(self.user_requests)} 个用户")
    
    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """从请求中提取用户ID"""
        
        # 尝试从请求体中提取用户ID
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    import json
                    data = json.loads(body)
                    user_id = data.get("user_id")
                    if user_id and isinstance(user_id, str):
                        return user_id
                    # 重新设置请求体
                    request._body = body
            except:
                pass
        
        # 尝试从查询参数中提取
        user_id = request.query_params.get("user_id")
        if user_id:
            return user_id
        
        # 尝试从请求头中提取
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        return None
    
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
    
    def get_stats(self) -> dict:
        """获取限流统计信息"""
        
        current_time = time.time()
        
        # 统计活跃IP数量
        active_ips = len([ip for ip, requests in self.ip_requests.items() 
                         if requests and current_time - requests[-1] <= 300])  # 5分钟内活跃
        
        # 统计活跃用户数量
        active_users = len([user for user, requests in self.user_requests.items() 
                           if requests and current_time - requests[-1] <= 300])  # 5分钟内活跃
        
        # 统计被阻塞的IP数量
        blocked_ips = len([ip for ip, (blocked_until, _) in self.ip_blocks.items() 
                          if current_time < blocked_until])
        
        return {
            "total_tracked_ips": len(self.ip_requests),
            "active_ips": active_ips,
            "blocked_ips": blocked_ips,
            "total_tracked_users": len(self.user_requests),
            "active_users": active_users,
            "rate_limits": {
                "ip_per_minute": self.rate_limit_per_minute,
                "ip_per_hour": self.rate_limit_per_hour,
                "user_per_minute": self.user_rate_limit_per_minute,
                "user_per_hour": self.user_rate_limit_per_hour
            }
        } 