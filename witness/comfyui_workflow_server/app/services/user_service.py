from typing import Dict, Optional
from pydantic import BaseModel, Field
import logging

from ..config import get_settings
from ..utils.crypto_utils import CryptoUtils
from ..models.user_models import APIUser

logger = logging.getLogger(__name__)

class APIUser(BaseModel):
    """API用户模型"""
    username: str
    api_key: str  # 将API密钥保留在此，以便进行身份验证
    permissions: list[str] = Field(default_factory=list)

    @property
    def is_admin(self) -> bool:
        return "admin" in self.permissions

class UserService:
    """用户管理服务"""

    def __init__(self, api_users: Dict[str, Dict]):
        self.users_by_name: Dict[str, APIUser] = {}
        for key, data in api_users.items():
            # 将作为字典键的api_key添加到数据中
            data['api_key'] = key
            user = APIUser(**data)
            self.users_by_name[user.username] = user
        logger.info(f"用户服务初始化完成，加载了 {len(self.users_by_name)} 个用户。")

    def get_user_by_name(self, username: str) -> Optional[APIUser]:
        """通过用户名获取用户"""
        return self.users_by_name.get(username)

    def authenticate_user(self, username: str, api_key: str) -> Optional[APIUser]:
        """验证用户凭据"""
        user = self.get_user_by_name(username)
        if not user:
            return None
        if user.api_key == api_key:
            return user
        return None

# 从安全配置中创建全局用户服务实例 - 这将被移除
# user_service = UserService() 