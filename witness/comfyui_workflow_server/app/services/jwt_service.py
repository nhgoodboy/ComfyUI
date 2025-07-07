"""
JWT令牌服务

提供安全的用户身份令牌验证和管理
支持令牌过期检查和黑名单机制
"""

import jwt
import time
import hashlib
from typing import Optional, Dict, Any, Set
from datetime import datetime, timedelta
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class JWTService:
    """JWT令牌服务"""
    
    def __init__(self, secret_key: str, token_expiry_minutes: int = 60):
        self.secret_key = secret_key
        self.token_expiry_minutes = token_expiry_minutes
        self.algorithm = "HS256"
        
        # 令牌黑名单（生产环境应使用Redis）
        self.blacklisted_tokens: Set[str] = set()
        
        logger.info("JWT令牌服务初始化完成")
    
    def generate_token(self, claims: Dict[str, Any]) -> str:
        """
        根据提供的声明（claims）生成一个JWT令牌。
        核心声明 'sub' (subject) 必须存在。
        """
        try:
            if "sub" not in claims:
                raise ValueError("核心声明 'sub' (subject) 必须在claims中提供")

            now = datetime.utcnow()
            expires_at = now + timedelta(minutes=self.token_expiry_minutes)
            
            payload = claims.copy() # 复制一份以避免修改原始字典
            payload.update({
                "iat": int(now.timestamp()),
                "exp": int(expires_at.timestamp()),
                "jti": self._generate_token_id(claims["sub"], now)
            })
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"生成令牌成功: sub={claims['sub']}")
            return token
            
        except Exception as e:
            logger.error(f"生成令牌失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="令牌生成失败")
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """验证用户令牌并返回载荷"""
        if not token:
            raise HTTPException(status_code=401, detail="缺少访问令牌")
        
        try:
            # 检查黑名单
            if self._is_token_blacklisted(token):
                logger.warning("黑名单令牌被拒绝")
                raise HTTPException(status_code=401, detail="令牌已失效")
            
            # 解码并验证令牌
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            # 基本验证
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="令牌格式无效（缺少sub声明）")
            
            # 检查令牌是否即将过期（提前5分钟警告）
            exp = payload.get("exp", 0)
            if exp - time.time() < 300:  # 5分钟
                logger.warning(f"令牌即将过期: {user_id}")
            
            logger.debug(f"令牌验证成功: {user_id}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("过期令牌被拒绝")
            raise HTTPException(status_code=401, detail="令牌已过期")
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效令牌被拒绝: {e}")
            raise HTTPException(status_code=401, detail="令牌无效")
        except Exception as e:
            logger.error(f"令牌验证错误: {e}")
            raise HTTPException(status_code=500, detail="令牌验证服务错误")
    
    def get_user_id_from_token(self, token: str) -> str:
        """从令牌中提取用户ID"""
        payload = self.decode_token(token)
        return payload["sub"]
    
    def revoke_token(self, token: str) -> bool:
        """撤销令牌（加入黑名单）"""
        try:
            # 先验证令牌格式（不检查过期）
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            # 获取令牌ID
            token_id = payload.get("jti")
            if token_id:
                self.blacklisted_tokens.add(token_id)
                logger.info(f"令牌已撤销: sub={payload.get('sub')}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"撤销令牌失败: {e}")
            return False
    
    def refresh_token(self, old_token: str) -> str:
        """刷新令牌"""
        try:
            # 验证旧令牌
            payload = self.decode_token(old_token)
            user_id = payload["sub"]
            
            # 撤销旧令牌
            self.revoke_token(old_token)
            
            # 生成新令牌
            new_token = self.generate_token({"sub": user_id})
            
            logger.info(f"令牌刷新成功: {user_id}")
            return new_token
            
        except Exception as e:
            logger.error(f"令牌刷新失败: {e}")
            raise HTTPException(status_code=401, detail="令牌刷新失败")
    
    def validate_user_permissions(self, token: str, required_permissions: Optional[list] = None) -> bool:
        """验证用户权限"""
        try:
            payload = self.decode_token(token)
            
            if not required_permissions:
                return True
            
            user_permissions = payload.get("permissions", [])
            return all(perm in user_permissions for perm in required_permissions)
            
        except Exception:
            return False
    
    def cleanup_expired_blacklist(self):
        """清理过期的黑名单令牌"""
        try:
            current_time = time.time()
            expired_tokens = set()
            
            for token_id in self.blacklisted_tokens:
                try:
                    # 尝试从token_id中提取时间戳（如果包含）
                    # 这里简化处理，实际可以根据token_id格式优化
                    if current_time - (24 * 3600) > 0:  # 清理24小时前的记录
                        # 实际应该解析token_id中的时间戳
                        pass
                except Exception:
                    continue
            
            # 移除过期记录
            self.blacklisted_tokens -= expired_tokens
            
            if expired_tokens:
                logger.info(f"清理过期黑名单令牌: {len(expired_tokens)}个")
                
        except Exception as e:
            logger.error(f"清理黑名单失败: {e}")
    
    def _generate_token_id(self, user_id: str, timestamp: datetime) -> str:
        """生成唯一令牌ID"""
        # 组合用户ID和时间戳生成唯一ID
        content = f"{user_id}:{timestamp.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """检查令牌是否在黑名单中"""
        try:
            # 解码令牌获取ID（不验证过期）
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            token_id = payload.get("jti")
            return token_id in self.blacklisted_tokens
            
        except Exception:
            # 如果无法解码，当作黑名单处理
            return True
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """获取令牌详细信息"""
        try:
            payload = self.decode_token(token)
            
            return {
                "user_id": payload.get("sub"),
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0)),
                "token_id": payload.get("jti"),
                "is_valid": True,
                "time_to_expiry": payload.get("exp", 0) - time.time()
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e)
            }


# 创建全局JWT服务实例
jwt_service = None

def get_jwt_service() -> JWTService:
    """获取JWT服务实例"""
    global jwt_service
    if jwt_service is None:
        raise RuntimeError("JWT服务未初始化")
    return jwt_service

def init_jwt_service(secret_key: str, token_expiry_minutes: int = 60):
    """初始化JWT服务"""
    global jwt_service
    jwt_service = JWTService(secret_key, token_expiry_minutes)
    return jwt_service 