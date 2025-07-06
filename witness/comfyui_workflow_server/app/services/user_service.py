from typing import Dict, Optional
from pydantic import BaseModel, Field
import logging

from ..config import get_settings
from ..utils.crypto_utils import CryptoUtils

logger = logging.getLogger(__name__)

class APIUser(BaseModel):
    """API用户模型"""
    api_key: str
    username: str
    permissions: list[str] = Field(default_factory=list)

class UserService:
    """用户服务，负责管理API用户"""
    def __init__(self):
        settings = get_settings()
        self.api_users = settings.security.api_users
        self._users: Dict[str, APIUser] = {}
        for api_key, user_data in self.api_users.items():
            self._users[api_key] = APIUser(
                api_key=api_key,
                username=user_data.get("username", "default_user"),
                permissions=user_data.get("permissions", [])
            )
        logger.info(f"用户服务初始化完成，加载了 {len(self._users)} 个用户。")

    def get_user_by_api_key(self, api_key: str) -> Optional[APIUser]:
        """通过API Key获取用户"""
        return self._users.get(api_key)

# 从安全配置中创建全局用户服务实例 - 这将被移除
# user_service = UserService() 