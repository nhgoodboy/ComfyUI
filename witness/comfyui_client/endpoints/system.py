from .prompt import BaseAPI

class SystemAPI(BaseAPI):
    """
    用于获取系统和节点信息的 API。
    """
    def get_system_stats(self):
        """
        获取系统统计信息，包括内存和 GPU 使用情况。
        """
        return self._client._request("GET", "/system_stats")

    def get_object_info(self, node_class: str = None):
        """
        获取所有可用节点或特定节点类的详细信息。

        :param node_class: 可选。要获取信息的节点的类名。
        :return: 包含节点信息的 JSON 响应。
        """
        if node_class:
            return self._client._request("GET", f"/object_info/{node_class}")
        return self._client._request("GET", "/object_info")

    def get_extensions(self):
        """
        获取已安装扩展的列表。
        """
        return self._client._request("GET", "/extensions")

    def get_embeddings(self):
        """
        获取可用嵌入的列表。
        """
        return self._client._request("GET", "/embeddings") 