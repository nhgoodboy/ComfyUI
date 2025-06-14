# witness/api_clients/prompt_client.py
# 备注：本文件中的注释已翻译为中文。
from ..utils.http_client import HttpClient
from ..config import settings
import uuid

class PromptClient:
    def __init__(self, http_client: HttpClient = None):
        self.http_client = http_client or HttpClient()
        self.client_id = settings.CLIENT_ID

    def queue_prompt(self, workflow_json: dict, client_id: str = None, add_to_front: bool = False):
        """将工作流程（提示）提交到 ComfyUI API。

        参数:
            workflow_json (dict): JSON 格式的工作流程定义。
            client_id (str, 可选): 客户端的唯一 ID。默认为 settings.CLIENT_ID。
            add_to_front (bool, 可选): 如果为 True，则将任务添加到队列的前面。

        返回:
            dict: API 响应，通常包含 prompt_id、number 和 node_errors。
        """
        actual_client_id = client_id or self.client_id or str(uuid.uuid4())
        
        payload = {
            "prompt": workflow_json,
            "client_id": actual_client_id
        }

        if add_to_front:
            payload["front"] = True
        
        if settings.COMFYUI_API_KEY:
            payload["extra_data"] = {"api_key": settings.COMFYUI_API_KEY}

        try:
            response = self.http_client.post("/prompt", json_data=payload)
            return response
        except Exception as e:
            # 更优雅地记录或处理
            print(f"Error queuing prompt: {e}")
            raise

# 示例用法 (可以删除或移至测试/示例文件)
if __name__ == '__main__':
    # 此示例需要正在运行的 ComfyUI 实例和有效的工作流程。
    # 您可以通过在 ComfyUI 中构建工作流程并使用“保存 (API 格式)”来获取工作流程 JSON。
    sample_workflow = {
        "3": {
            "inputs": {
                "seed": 1234567890,
                "steps": 20,
                "cfg": 8,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler",
            "_meta": {"title": "KSampler"}
        },
        "4": {
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": "加载检查点"}
        },
        "5": {
            "inputs": {"width": 512, "height": 512, "batch_size": 1},
            "class_type": "EmptyLatentImage",
            "_meta": {"title": "空潜在图像"}
        },
        "6": {
            "inputs": {"text": "杰作，最佳质量，美丽的风景", "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "正面提示"}
        },
        "7": {
            "inputs": {"text": "糟糕，丑陋，最差质量", "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "负面提示"}
        },
        "8": {
            "inputs": {"filename_prefix": "ComfyUI_API_Witness", "images": ["3", 0]},
            "class_type": "SaveImage",
            "_meta": {"title": "保存图像"}
        }
    }

    try:
        client = PromptClient()
        print("尝试将示例提示排入队列...")
        # 确保您的 ComfyUI 具有 'v1-5-pruned-emaonly.safetensors' 模型或更改工作流程。
        response = client.queue_prompt(sample_workflow)
        print("成功将提示排入队列:", response)
    except Exception as e:
        print(f"提示示例排队失败: {e}")
        print("请确保 ComfyUI 正在运行并且工作流程（尤其是模型名称）有效。")