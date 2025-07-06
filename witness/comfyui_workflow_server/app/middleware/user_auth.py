"""
用户认证模块

基于JWT令牌的用户身份验证和授权
提供用户身份提取和权限验证功能
"""

import jwt
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.jwt_service import get_jwt_service
from app.utils.crypto_utils import SecurityConstants
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer认证方案
security = HTTPBearer()

class UserAuthenticator:
    """用户认证器"""
    
    def __init__(self):
        self.jwt_service = None
    
    def _get_jwt_service(self):
        """获取JWT服务"""
        if self.jwt_service is None:
            self.jwt_service = get_jwt_service()
        return self.jwt_service
    
    def extract_user_from_token(self, token: str) -> Dict[str, Any]:
        """从JWT令牌中提取用户信息"""
        try:
            jwt_service = self._get_jwt_service()
            payload = jwt_service.verify_token(token)
            
            user_info = {
                "user_id": payload.get("user_id"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "token_id": payload.get("jti"),
                "permissions": payload.get("permissions", []),
                "roles": payload.get("roles", [])
            }
            
            logger.debug(f"用户信息提取成功: {user_info['user_id']}")
            return user_info
            
        except Exception as e:
            logger.error(f"用户信息提取失败: {e}")
            raise HTTPException(status_code=401, detail="用户身份验证失败")
    
    def validate_user_permissions(self, user_info: Dict[str, Any], required_permissions: list) -> bool:
        """验证用户权限"""
        if not required_permissions:
            return True
        
        user_permissions = user_info.get("permissions", [])
        return all(perm in user_permissions for perm in required_permissions)
    
    def validate_user_roles(self, user_info: Dict[str, Any], required_roles: list) -> bool:
        """验证用户角色"""
        if not required_roles:
            return True
        
        user_roles = user_info.get("roles", [])
        return any(role in user_roles for role in required_roles)


# 全局认证器实例
authenticator = UserAuthenticator()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """获取当前用户信息（依赖注入）"""
    try:
        token = credentials.credentials
        user_info = authenticator.extract_user_from_token(token)
        
        # 基础验证
        if not user_info.get("user_id"):
            raise HTTPException(status_code=401, detail="用户身份无效")
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户认证失败: {e}")
        raise HTTPException(status_code=401, detail="用户认证失败")


async def get_current_user_id(user_info: Dict[str, Any] = Depends(get_current_user)) -> str:
    """获取当前用户ID（依赖注入）"""
    return user_info["user_id"]


async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """获取可选用户信息（不强制要求认证）"""
    try:
        # 从Authorization头部获取令牌
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None
        
        # 检查Bearer前缀
        if not auth_header.startswith(SecurityConstants.BEARER_PREFIX):
            return None
        
        token = auth_header[len(SecurityConstants.BEARER_PREFIX):]
        if not token:
            return None
        
        # 提取用户信息
        user_info = authenticator.extract_user_from_token(token)
        return user_info
        
    except Exception as e:
        logger.debug(f"可选用户认证失败: {e}")
        return None


def require_permissions(required_permissions: list):
    """权限验证装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 获取用户信息
            user_info = kwargs.get("user_info") or kwargs.get("current_user")
            if not user_info:
                raise HTTPException(status_code=401, detail="用户未认证")
            
            # 验证权限
            if not authenticator.validate_user_permissions(user_info, required_permissions):
                raise HTTPException(status_code=403, detail="权限不足")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_roles(required_roles: list):
    """角色验证装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 获取用户信息
            user_info = kwargs.get("user_info") or kwargs.get("current_user")
            if not user_info:
                raise HTTPException(status_code=401, detail="用户未认证")
            
            # 验证角色
            if not authenticator.validate_user_roles(user_info, required_roles):
                raise HTTPException(status_code=403, detail="角色权限不足")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class UserPermissions:
    """用户权限常量"""
    
    # 基础权限
    READ_STYLES = "read_styles"
    CREATE_TASK = "create_task"
    READ_TASK = "read_task"
    DELETE_TASK = "delete_task"
    
    # 文件权限
    UPLOAD_FILE = "upload_file"
    DOWNLOAD_FILE = "download_file"
    DELETE_FILE = "delete_file"
    
    # 管理权限
    ADMIN_USER = "admin_user"
    ADMIN_SYSTEM = "admin_system"
    
    # 权限组
    BASIC_USER = [READ_STYLES, CREATE_TASK, READ_TASK, UPLOAD_FILE, DOWNLOAD_FILE]
    PREMIUM_USER = BASIC_USER + [DELETE_TASK, DELETE_FILE]
    ADMIN = PREMIUM_USER + [ADMIN_USER, ADMIN_SYSTEM]


class UserRoles:
    """用户角色常量"""
    
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    SYSTEM = "system"


def create_user_dependencies():
    """创建用户相关依赖"""
    
    async def get_user_with_permissions(permissions: list):
        """获取具有特定权限的用户"""
        async def _get_user(user_info: Dict[str, Any] = Depends(get_current_user)):
            if not authenticator.validate_user_permissions(user_info, permissions):
                raise HTTPException(status_code=403, detail="权限不足")
            return user_info
        return _get_user
    
    async def get_user_with_roles(roles: list):
        """获取具有特定角色的用户"""
        async def _get_user(user_info: Dict[str, Any] = Depends(get_current_user)):
            if not authenticator.validate_user_roles(user_info, roles):
                raise HTTPException(status_code=403, detail="角色权限不足")
            return user_info
        return _get_user
    
    return {
        "get_user_with_permissions": get_user_with_permissions,
        "get_user_with_roles": get_user_with_roles
    }


# 预定义的用户依赖
async def get_basic_user(user_info: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """获取基础用户（需要基础权限）"""
    if not authenticator.validate_user_permissions(user_info, UserPermissions.BASIC_USER):
        raise HTTPException(status_code=403, detail="需要基础用户权限")
    return user_info


async def get_premium_user(user_info: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """获取高级用户（需要高级权限）"""
    if not authenticator.validate_user_permissions(user_info, UserPermissions.PREMIUM_USER):
        raise HTTPException(status_code=403, detail="需要高级用户权限")
    return user_info


async def get_admin_user(user_info: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """获取管理员用户（需要管理权限）"""
    if not authenticator.validate_user_roles(user_info, [UserRoles.ADMIN]):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user_info


# 用户认证工具函数
def create_user_token(user_id: str, permissions: list = None, roles: list = None) -> str:
    """创建用户令牌"""
    try:
        jwt_service = get_jwt_service()
        
        extra_claims = {}
        if permissions:
            extra_claims["permissions"] = permissions
        if roles:
            extra_claims["roles"] = roles
        
        token = jwt_service.generate_token(user_id, extra_claims)
        logger.info(f"用户令牌创建成功: {user_id}")
        return token
        
    except Exception as e:
        logger.error(f"用户令牌创建失败: {user_id} - {e}")
        raise HTTPException(status_code=500, detail="令牌创建失败")


def revoke_user_token(token: str) -> bool:
    """撤销用户令牌"""
    try:
        jwt_service = get_jwt_service()
        return jwt_service.revoke_token(token)
        
    except Exception as e:
        logger.error(f"令牌撤销失败: {e}")
        return False


def refresh_user_token(old_token: str) -> str:
    """刷新用户令牌"""
    try:
        jwt_service = get_jwt_service()
        return jwt_service.refresh_token(old_token)
        
    except Exception as e:
        logger.error(f"令牌刷新失败: {e}")
        raise HTTPException(status_code=401, detail="令牌刷新失败")


# 导出
__all__ = [
    "get_current_user",
    "get_current_user_id", 
    "get_optional_user",
    "get_basic_user",
    "get_premium_user",
    "get_admin_user",
    "require_permissions",
    "require_roles",
    "create_user_token",
    "revoke_user_token",
    "refresh_user_token",
    "UserPermissions",
    "UserRoles",
    "authenticator"
] 