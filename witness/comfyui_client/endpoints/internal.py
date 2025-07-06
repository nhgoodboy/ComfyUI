from .prompt import BaseAPI

class InternalAPI(BaseAPI):
    """
    用于内部系统管理的 API，包括日志和系统路径管理。
    注意：这些API主要用于调试和系统监控，可能在未来版本中发生变化。
    """
    
    async def get_logs(self):
        """
        获取系统日志（文本格式）。
        
        :return: 格式化的日志文本
        """
        return await self._client._request("GET", "/internal/logs")
    
    async def get_raw_logs(self):
        """
        获取原始日志数据。
        
        :return: 包含日志条目和终端尺寸信息的结构化数据
        """
        return await self._client._request("GET", "/internal/logs/raw")
    
    async def subscribe_logs(self, client_id: str, enabled: bool):
        """
        订阅或取消订阅日志更新。
        
        :param client_id: 客户端ID，用于WebSocket连接
        :param enabled: 是否启用日志订阅
        :return: 订阅结果
        """
        data = {
            "clientId": client_id,
            "enabled": enabled
        }
        return await self._client._request("PATCH", "/internal/logs/subscribe", json_data=data)
    
    async def get_folder_paths(self):
        """
        获取系统文件夹路径配置。
        
        :return: 包含各种文件夹路径的配置信息
        """
        return await self._client._request("GET", "/internal/folder_paths") 