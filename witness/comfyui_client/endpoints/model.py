from .prompt import BaseAPI
from typing import Optional

class ModelAPI(BaseAPI):
    """
    用于模型管理的 API。
    """
    async def get_model_types(self):
        """
        获取所有可用的模型类型列表。
        
        :return: 包含模型类型名称的列表
        """
        return await self._client._request("GET", "/models")
    
    async def get_models(self, folder: str):
        """
        获取特定文件夹中的模型文件列表。
        
        :param folder: 模型文件夹名称
        :return: 包含模型文件名的列表
        """
        return await self._client._request("GET", f"/models/{folder}")
    
    async def get_model_metadata(self, folder_name: str, filename: str):
        """
        获取模型文件的元数据信息（仅支持 .safetensors 文件）。
        
        :param folder_name: 模型文件夹名称
        :param filename: 模型文件名（必须是 .safetensors 文件）
        :return: 包含元数据信息的 JSON 响应
        """
        params = {"filename": filename}
        return await self._client._request("GET", f"/view_metadata/{folder_name}", params=params) 