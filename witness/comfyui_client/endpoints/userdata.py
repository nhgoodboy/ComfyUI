from .prompt import BaseAPI
from typing import Optional
from ..utils.validation import validate_required_string, validate_bytes_data, validate_file_path

class UserDataAPI(BaseAPI):
    """
    用于用户数据管理的 API，支持文件上传、下载、删除和移动操作。
    """
    
    async def list_userdata(self, dir: str = "", recurse: bool = False, 
                           full_info: bool = False, split: bool = False):
        """
        列出用户数据文件。
        
        :param dir: 要列出文件的目录
        :param recurse: 是否递归列出子目录中的文件
        :param full_info: 是否返回详细的文件信息
        :param split: 是否分割文件路径（仅在 full_info=False 时生效）
        :return: 文件列表或文件信息列表
        """
        params = {"dir": dir}
        if recurse:
            params["recurse"] = "true"
        if full_info:
            params["full_info"] = "true"
        if split:
            params["split"] = "true"
        
        return await self._client._request("GET", "/userdata", params=params)
    
    async def list_userdata_v2(self, path: str = ""):
        """
        列出用户数据文件和目录（v2版本）。
        
        :param path: 用户数据目录中的相对路径
        :return: 包含文件和目录信息的结构化列表
        """
        params = {"path": path} if path else {}
        return await self._client._request("GET", "/v2/userdata", params=params)
    
    async def get_userdata_file(self, file: str):
        """
        获取用户数据文件。
        
        :param file: 文件路径
        :return: 文件内容
        """
        validated_file = validate_required_string(file, "file")
        return await self._client._request("GET", f"/userdata/{validated_file}")
    
    async def upload_userdata_file(self, file: str, data: bytes, 
                                  overwrite: bool = True, full_info: bool = False):
        """
        上传用户数据文件。
        
        :param file: 目标文件路径
        :param data: 文件内容（字节数据）
        :param overwrite: 是否覆盖现有文件
        :param full_info: 是否返回详细文件信息
        :return: 上传结果
        """
        # 输入验证
        validated_file = validate_required_string(file, "file")
        validated_data = validate_bytes_data(data, "data", max_size=self._client.config.max_file_size)
        
        params = {}
        if not overwrite:
            params["overwrite"] = "false"
        if full_info:
            params["full_info"] = "true"
        
        # 发送原始字节数据作为请求体
        return await self._client._request_with_data("POST", f"/userdata/{validated_file}", 
                                                   data=validated_data, params=params)
    
    async def delete_userdata_file(self, file: str):
        """
        删除用户数据文件。
        
        :param file: 要删除的文件路径
        :return: 删除结果
        """
        validated_file = validate_required_string(file, "file")
        return await self._client._request("DELETE", f"/userdata/{validated_file}")
    
    async def move_userdata_file(self, file: str, dest: str, 
                                overwrite: bool = True, full_info: bool = False):
        """
        移动或重命名用户数据文件。
        
        :param file: 源文件路径
        :param dest: 目标文件路径
        :param overwrite: 是否覆盖现有文件
        :param full_info: 是否返回详细文件信息
        :return: 移动结果
        """
        # 输入验证
        validated_file = validate_required_string(file, "file")
        validated_dest = validate_required_string(dest, "dest")
        
        params = {}
        if not overwrite:
            params["overwrite"] = "false"
        if full_info:
            params["full_info"] = "true"
        
        return await self._client._request("POST", f"/userdata/{validated_file}/move/{validated_dest}", 
                                         params=params) 