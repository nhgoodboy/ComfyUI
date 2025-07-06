"""
用户身份认证中间件

从HTTP Header提取用户ID并验证
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

class UserAuthMiddleware(BaseHTTPMiddleware):
    """用户身份认证中间件"""
    
    def __init__(self, app, require_user_id: bool = True):
        super().__init__(app)
        self.require_user_id = require_user_id
        self.excluded_paths = {"/health", "/", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next):
        """处理用户身份验证"""
        try:
            # 检查是否为排除路径
            if request.url.path in self.excluded_paths:
                return await call_next(request)
            
            # 提取用户ID
            user_id = request.headers.get("x-user-id")
            
            # 验证用户ID
            if self.require_user_id and not user_id:
                logger.warning(f"请求缺少用户ID: {request.method} {request.url.path}")
                raise HTTPException(status_code=401, detail="缺少用户身份标识")
            
            if user_id and not self._validate_user_id(user_id):
                logger.warning(f"无效的用户ID: {user_id}")
                raise HTTPException(status_code=401, detail="无效的用户身份标识")
            
            # 将用户ID添加到请求状态
            request.state.user_id = user_id
            
            # 记录用户请求
            if user_id:
                logger.info(f"用户请求: {user_id} - {request.method} {request.url.path}")
            
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"用户身份验证中间件错误: {e}")
            raise HTTPException(status_code=500, detail="身份验证服务错误")
    
    def _validate_user_id(self, user_id: str) -> bool:
        """验证用户ID格式"""
        if not user_id or len(user_id.strip()) == 0:
            return False
        
        # 基本格式验证
        if len(user_id) < 3 or len(user_id) > 64:
            return False
        
        # 可以添加更多验证规则
        return True

def get_current_user_id(request: Request) -> str:
    """获取当前用户ID的依赖函数"""
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(status_code=401, detail="用户身份未验证")
    return user_id 