from typing import Dict, Optional
from pydantic import BaseModel, Field
import logging

from ..config import get_settings
from ..utils.crypto_utils import CryptoUtils

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
    """用户服务，负责管理API用户"""
    def __init__(self):
        settings = get_settings()
        # 将用户字典的键更改为 username
        self._users: Dict[str, APIUser] = {}
        for api_key, user_data in settings.security.api_users.items():
            username = user_data.get("username", "default_user")
            self._users[username] = APIUser(
                username=username,
                api_key=api_key,
                permissions=user_data.get("permissions", [])
            )
        logger.info(f"用户服务初始化完成，加载了 {len(self._users)} 个用户。")

    def get_user_by_name(self, username: str) -> Optional[APIUser]:
        """通过用户名获取用户"""
        return self._users.get(username)

    def authenticate_user(self, username: str, password_or_api_key: str) -> Optional[APIUser]:
        """通过用户名和密码（API密钥）对用户进行身份验证"""
        user = self.get_user_by_name(username)
        if user and user.api_key == password_or_api_key:
            return user
        return None

# 从安全配置中创建全局用户服务实例 - 这将被移除
# user_service = UserService() 