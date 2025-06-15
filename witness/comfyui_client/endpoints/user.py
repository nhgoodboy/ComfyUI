from .prompt import BaseAPI

class UserAPI(BaseAPI):
    """
    用于用户和设置管理的 API，主要用于多用户模式。
    """
    def get_users(self):
        """
        获取用户列表（在多用户模式下）或迁移状态。
        """
        return self._client._request("GET", "/users")

    def create_user(self, username: str):
        """
        创建一个新用户。

        :param username: 所需的用户名。
        :return: JSON 响应，如果用户名重复，可能包含错误。
        """
        data = {"username": username}
        return self._client._request("POST", "/users", json_data=data)

    def get_settings(self):
        """
        获取当前用户的设置。
        """
        return self._client._request("GET", "/settings")

    def update_settings(self, new_settings: dict):
        """
        更新当前用户的设置。

        :param new_settings: 要更新的设置字典。
        """
        return self._client._request("POST", "/settings", json_data=new_settings) 