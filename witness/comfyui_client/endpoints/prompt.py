from ..client import ComfyUIClient

class BaseAPI:
    def __init__(self, client: 'ComfyUIClient'):
        self._client = client

class PromptAPI(BaseAPI):
    """
    用于与提示和队列交互的 API。
    """
    def queue_prompt(self, prompt: dict, client_id: str):
        """
        将一个工作流提示提交到队列。

        :param prompt: 一个代表工作流的字典。
        :param client_id: 会话的客户端 ID。
        :return: API 返回的 JSON 响应，包含 prompt_id。
        """
        data = {"prompt": prompt, "client_id": client_id}
        return self._client._request("POST", "/prompt", json_data=data)

    def get_queue(self):
        """
        获取当前队列的状态。
        :return: 包含 'queue_running' 和 'queue_pending' 的 JSON 响应。
        """
        return self._client._request("GET", "/queue")

    def get_history(self, prompt_id: str = None):
        """
        获取执行历史。如果提供了 prompt_id，则获取该特定提示的历史。

        :param prompt_id: 可选。要获取历史的提示 ID。
        :return: 包含历史数据的 JSON 响应。
        """
        if prompt_id:
            return self._client._request("GET", f"/history/{prompt_id}")
        return self._client._request("GET", "/history")

    def interrupt(self):
        """
        中断当前正在执行的提示。
        """
        return self._client._request("POST", "/interrupt")

    def delete_from_queue(self, prompt_ids: list):
        """
        从队列中删除项目。

        :param prompt_ids: 要删除的提示 ID 列表。
        """
        data = {"delete": prompt_ids}
        return self._client._request("POST", "/queue", json_data=data) 