# witness/api_clients/history_client.py
# 备注：本文件中的注释已翻译为中文。
from ..utils.http_client import HttpClient

class HistoryClient:
    def __init__(self, http_client: HttpClient = None):
        self.http_client = http_client or HttpClient()

    def get_history(self, prompt_id: str = None):
        """获取执行历史记录。

        参数:
            prompt_id (str, 可选): 如果提供，则获取特定 prompt_id 的历史记录。
                                       否则，获取整个历史记录。

        返回:
            dict: 历史数据。
        """
        endpoint = "/history"
        if prompt_id:
            endpoint = f"/history/{prompt_id}"
        
        try:
            response = self.http_client.get(endpoint)
            return response
        except Exception as e:
            print(f"Error getting history for {prompt_id if prompt_id else 'all'}: {e}")
            raise

    def clear_history(self):
        """清除所有执行历史记录。"""
        try:
            response = self.http_client.post("/history", json_data={"clear": True})
            return response
        except Exception as e:
            print(f"Error clearing history: {e}")
            raise

    def delete_history_item(self, prompt_id: str):
        """通过 prompt_id 删除历史记录中的特定项目。"""
        if not prompt_id:
            raise ValueError("prompt_id must be provided to delete a history item.")
        try:
            response = self.http_client.post("/history", json_data={"delete": [prompt_id]})
            return response
        except Exception as e:
            print(f"Error deleting history item {prompt_id}: {e}")
            raise

# 示例用法 (可以删除或移至测试/示例文件)
if __name__ == '__main__':
    # 此示例需要正在运行的 ComfyUI 实例。
    # 您可能需要先将提示排入队列才能拥有历史记录。
    try:
        history_client = HistoryClient()
        print("尝试获取所有历史记录...")
        all_history = history_client.get_history()
        print("所有历史记录:", all_history)

        if all_history and isinstance(all_history, dict) and len(all_history) > 0:
            # 获取找到的第一个 prompt_id 的历史记录
            sample_prompt_id = list(all_history.keys())[0]
            print(f"\n尝试获取 prompt_id 的历史记录: {sample_prompt_id}...")
            single_history = history_client.get_history(sample_prompt_id)
            print(f"prompt_id {sample_prompt_id} 的历史记录:", single_history)
            
            # 删除示例 (请谨慎使用，这将删除它)
            # print(f"\n尝试删除 prompt_id 的历史记录: {sample_prompt_id}...")
            # delete_response = history_client.delete_history_item(sample_prompt_id)
            # print("删除响应:", delete_response)

        # 清除历史记录示例 (请极其谨慎使用，这将删除所有历史记录)
        # print("\n尝试清除所有历史记录...")
        # clear_response = history_client.clear_history()
        # print("清除历史记录响应:", clear_response)

    except Exception as e:
        print(f"历史客户端示例失败: {e}")
        print("请确保 ComfyUI 正在运行。")