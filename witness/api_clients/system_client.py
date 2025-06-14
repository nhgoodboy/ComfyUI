# witness/api_clients/system_client.py
# 备注：此类用于与 ComfyUI 的系统 API 进行交互。
from ..utils.http_client import HttpClient

class SystemClient:
    def __init__(self, http_client: HttpClient = None):
        """初始化 SystemClient。

        参数:
            http_client (HttpClient, 可选): 用于发出 HTTP 请求的客户端。
                                            如果未提供，则创建一个新的 HttpClient 实例。
        """
        self.http_client = http_client or HttpClient()

    def get_system_stats(self):
        """获取系统统计信息 (CPU, GPU, RAM 使用情况)。"""
        try:
            response = self.http_client.get("/system_stats")
            return response
        except Exception as e:
            print(f"获取系统统计信息时出错: {e}")
            raise

    def get_object_info(self, node_class_type: str = None):
        """获取所有可用节点或特定节点类的信息。

        参数:
            node_class_type (str, 可选): 如果提供，则获取此特定节点类的信息。
                                           否则，获取所有节点的信息。

        返回:
            dict: 节点信息。
        """
        endpoint = "/object_info"
        if node_class_type:
            endpoint = f"/object_info/{node_class_type}"
        
        try:
            response = self.http_client.get(endpoint)
            return response
        except Exception as e:
            print(f"获取对象信息 '{node_class_type if node_class_type else '所有'}' 时出错: {e}")
            raise

    def get_embeddings(self):
        """列出可用的 embedding/Lora 模型。"""
        try:
            response = self.http_client.get("/embeddings")
            return response
        except Exception as e:
            print(f"获取 embeddings 时出错: {e}")
            raise

    def get_extensions(self):
        """列出已加载的 JavaScript 扩展。"""
        try:
            response = self.http_client.get("/extensions")
            return response
        except Exception as e:
            print(f"获取扩展时出错: {e}")
            raise

    def get_models_list(self, model_type: str = None, model_name: str = None):
        """(实验性) 列出模型，可选地按类型和名称筛选。

        参数:
            model_type (str, 可选): 模型类型 (例如 'checkpoints', 'loras')。
            model_name (str, 可选): 模型的特定名称。

        返回:
            list or dict: 模型列表或模型详细信息。
        """
        params = {}
        if model_type:
            params['type'] = model_type
        if model_name:
            params['name'] = model_name
        
        try:
            response = self.http_client.get("/models", params=params if params else None)
            return response
        except Exception as e:
            print(f"获取模型列表时出错 (类型: {model_type}, 名称: {model_name}): {e}")
            raise

# 示例用法 (可以删除或移动到测试/示例文件)
if __name__ == '__main__':
    # 此示例需要一个正在运行的 ComfyUI 实例。
    try:
        system_client = SystemClient()
        
        print("尝试获取系统统计信息...")
        stats = system_client.get_system_stats()
        print("系统统计信息:", stats)

        print("\n尝试获取对象信息 (所有节点)...")
        object_info_all = system_client.get_object_info()
        # print("对象信息 (所有):", object_info_all) # 此输出可能非常大
        print(f"已检索到 {len(object_info_all)} 种节点类型的信息。")

        if object_info_all:
            sample_node_class = list(object_info_all.keys())[0]
            print(f"\n尝试获取节点 {sample_node_class} 的对象信息...")
            object_info_single = system_client.get_object_info(sample_node_class)
            print(f"对象信息 ({sample_node_class}):", object_info_single)

        print("\n尝试获取 embeddings...")
        embeddings = system_client.get_embeddings()
        print("Embeddings:", embeddings)

        print("\n尝试获取扩展...")
        extensions = system_client.get_extensions()
        print("扩展:", extensions)
        
        print("\n尝试获取模型列表 (所有)...")
        models_all = system_client.get_models_list()
        print("所有模型列表:", models_all)
        
        print("\n尝试获取模型列表 (checkpoints)...")
        models_checkpoints = system_client.get_models_list(model_type='checkpoints')
        print("Checkpoint 模型列表:", models_checkpoints)

    except Exception as e:
        print(f"系统客户端示例失败: {e}")
        print("请确保 ComfyUI 正在运行。")