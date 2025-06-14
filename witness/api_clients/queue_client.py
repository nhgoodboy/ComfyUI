# witness/api_clients/queue_client.py
# 备注：此类用于与 ComfyUI 的队列 API 进行交互。
from ..utils.http_client import HttpClient

class QueueClient:
    def __init__(self, http_client: HttpClient = None):
        """初始化 QueueClient。

        参数:
            http_client (HttpClient, 可选): 用于发出 HTTP 请求的客户端。
                                            如果未提供，则创建一个新的 HttpClient 实例。
        """
        self.http_client = http_client or HttpClient()

    def get_queue_info(self):
        """获取队列的当前状态。"""
        try:
            response = self.http_client.get("/queue")
            return response
        except Exception as e:
            print(f"获取队列信息时出错: {e}")
            raise

    def clear_queue(self):
        """清除队列中所有待处理的任务。"""
        try:
            response = self.http_client.post("/queue", json_data={"clear": True})
            # 备注：清除队列操作通常返回确认信息或空响应。
            return response
        except Exception as e:
            print(f"清除队列时出错: {e}")
            raise

    def delete_queue_items(self, prompt_ids: list):
        """通过 prompt_id 从队列中删除特定项目。"""
        if not prompt_ids or not isinstance(prompt_ids, list):
            raise ValueError("prompt_ids 必须是一个非空列表。")
        try:
            response = self.http_client.post("/queue", json_data={"delete": prompt_ids})
            return response
        except Exception as e:
            print(f"删除队列项目 {prompt_ids} 时出错: {e}")
            raise

    def interrupt_current_task(self):
        """中断当前正在执行的任务。"""
        try:
            # API 文档建议 POST /interrupt 返回空响应或确认信息。
            # 如果 Content-Type 是 application/json，http_client 可能会尝试解析 JSON。
            # 如果它确实是空的或非 JSON，则可能需要在此处或 http_client 中进行调整。
            response = self.http_client.post("/interrupt")
            return response # 或者适当地处理非 JSON 响应
        except Exception as e:
            print(f"中断当前任务时出错: {e}")
            raise

    def free_resources(self, unload_models: bool = True, free_memory: bool = True):
        """释放资源，可选地卸载模型并释放 GPU 内存。
           此操作还会中断当前任务并清除队列。
        """
        payload = {}
        if unload_models:
            payload['unload_models'] = True
        if free_memory:
            payload['free_memory'] = True
        
        try:
            response = self.http_client.post("/free", json_data=payload)
            return response
        except Exception as e:
            print(f"Error freeing resources: {e}")
            raise

# 示例用法 (可以删除或移动到测试/示例文件)
if __name__ == '__main__':
    # 此示例需要一个正在运行的 ComfyUI 实例。
    try:
        queue_client = QueueClient()
        print("尝试获取队列信息...")
        queue_info = queue_client.get_queue_info()
        print("队列信息:", queue_info)

        # 示例：中断当前任务 (如果正在运行)
        # print("\n尝试中断当前任务...")
        # interrupt_response = queue_client.interrupt_current_task()
        # print("中断响应:", interrupt_response)
        
        # 示例：释放资源 (请谨慎使用)
        # print("\n尝试释放资源...")
        # free_response = queue_client.free_resources()
        # print("释放资源响应:", free_response)

    except Exception as e:
        print(f"队列客户端示例失败: {e}")
        print("请确保 ComfyUI 正在运行。")