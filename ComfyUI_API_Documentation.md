[MODE: REVIEW]

实施与计划完全匹配。

好的，我已经理解您的需求，您希望了解如何通过外部API调用（特别是使用JSON格式的工作流）来接入ComfyUI进行图像生成，而不是关于ComfyUI内部的API节点。基于我们之前收集的信息，我为您准备了以下ComfyUI API接入开发文档：

# ComfyUI API 接入开发文档

## 1. 简介

本文档旨在帮助开发者理解和使用ComfyUI的HTTP API，以便通过外部应用程序编程方式控制ComfyUI进行图像生成和工作流处理。

### 1.1 核心概念

*   **ComfyUI**：一个强大的、基于节点的图形用户界面，用于稳定扩散（Stable Diffusion）模型的实验和创作。
*   **API (Application Programming Interface)**：一组规则和协议，允许不同的软件应用程序之间进行通信。ComfyUI提供HTTP API，允许外部程序与其交互。
*   **工作流 (Workflow/Prompt)**：在ComfyUI中，工作流是指连接在一起的节点图，定义了从输入到最终图像输出的处理流程。通过API，这些工作流可以表示为JSON对象并提交执行。

## 2. 准备工作

*   **ComfyUI 安装与运行**：确保您的ComfyUI实例已正确安装并正在运行。默认情况下，API服务监听在 `http://127.0.0.1:8188`。
*   **API 可访问性**：如果您的ComfyUI运行在远程服务器或容器中，请确保API端口（默认为8188）已正确暴露并可从您的应用程序访问。

## 3. 认证

根据 <mcfile name="basic_api_example.py" path="script_examples/basic_api_example.py"></mcfile> 中的示例，API密钥（如果配置）可以通过在提交到 `/prompt` 端点的JSON载荷中的 `extra_data` 字段下的 `api_key` 传递。然而，ComfyUI本身默认可能不需要API密钥即可访问本地实例的API。如果使用了如 `api_key_comfy_org` 这样的特定集成或自定义配置，则需要遵循其特定的认证机制。

对于标准的本地部署，通常不需要显式的API密钥。如果您的ComfyUI设置了 `--api-key` 启动参数，则需要在请求中包含该密钥。

**示例 (在 `/prompt` 请求中包含API Key)**:

```json
{
  "prompt": { /* ... 您的工作流节点 ... */ },
  "extra_data": {
    "api_key": "YOUR_API_KEY_HERE" // 如果ComfyUI启动时配置了API Key
  }
}
```

## 4. 核心API端点：执行工作流

### `POST /prompt`

这是执行ComfyUI工作流最核心的API端点。

*   **方法**: `POST`
*   **URL**: `http://127.0.0.1:8188/prompt` (替换为您的ComfyUI服务器地址和端口)
*   **Content-Type**: `application/json`
*   **请求体 (Request Body)**: 一个JSON对象，包含要执行的工作流（prompt）以及可选的客户端ID和额外数据。

    ```json
    {
        "prompt": { /* 工作流定义 */ },
        "client_id": "your_client_id_optional", // 可选，用于标识客户端
        "extra_data": { // 可选，用于传递额外参数，如API Key
            "api_key": "YOUR_API_KEY_HERE" // 如果需要
        }
        // "front": true // 可选，如果为true，则将此任务添加到队列前端
    }
    ```

*   **响应 (Response)**:
    *   **成功 (200 OK)**: 返回一个JSON对象，包含 `prompt_id`（已提交工作流的ID），`number`（队列中的任务编号），以及 `node_errors` (如果有节点配置错误)。
        ```json
        {
            "prompt_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
            "number": 10,
            "node_errors": {}
        }
        ```
    *   **失败**: 返回相应的HTTP错误状态码和错误信息。

## 5. 工作流JSON结构

提交到 `/prompt` 端点的工作流 (prompt) 是一个JSON对象，其键是节点ID，值是该节点的定义。每个节点定义包含：

*   `inputs`: 一个对象，包含节点的输入参数。
*   `class_type`: 节点的类名。
*   `_meta`: 一个可选对象，可以包含元数据，如节点的标题。

**示例：一个简单的工作流JSON** (改编自 <mcfile name="basic_api_example.py" path="script_examples/basic_api_example.py"></mcfile>)

```json
{
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
    "_meta": {
      "title": "KSampler"
    }
  },
  "4": {
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "6": {
    "inputs": {
      "text": "masterpiece, best quality, beautiful scenery",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "Positive Prompt"
    }
  },
  "7": {
    "inputs": {
      "text": "bad, ugly, worst quality",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "Negative Prompt"
    }
  },
  "8": {
    "inputs": {
      "filename_prefix": "ComfyUI_API",
      "images": ["3", 0]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  }
}
```

**关键点**:

*   **节点ID**: 每个节点由一个唯一的字符串ID标识（例如 `"3"`, `"4"`）。这些ID用于连接节点输出到其他节点的输入。
*   **输入连接**: 当一个节点的输入来自另一个节点的输出时，它表示为一个数组，第一个元素是源节点ID（字符串），第二个元素是源节点的输出索引（整数）。例如，`"model": ["4", 0]` 表示KSampler节点的 `model` 输入来自ID为 `"4"` (CheckpointLoaderSimple) 的节点的第0个输出。
*   **`class_type`**: 对应ComfyUI中节点的Python类名。
*   **`inputs`**: 包含节点的具体参数值。

要获取特定工作流的JSON表示，您可以在ComfyUI界面中构建您的工作流，然后使用界面上的 "Save (API Format)" 或类似功能导出其JSON。

## 6. 其他HTTP API端点

以下是一些其他有用的API端点，可以通过HTTP请求与之交互：

### 6.1 WebSocket (`/ws`)

*   **URL**: `ws://127.0.0.1:8188/ws`
*   **用途**: 用于接收关于工作流执行状态的实时更新。当您提交一个prompt后，可以通过WebSocket连接监听事件，例如执行开始、进度更新、执行完成或错误。
*   **消息格式**: JSON。消息类型包括 `status`, `execution_start`, `execution_cached`, `executing`, `progress`, `executed`, `execution_interrupted`, `execution_error`。
*   **连接参数**: 可以传递 `clientId` 作为查询参数，例如 `ws://127.0.0.1:8188/ws?clientId=your_client_id`。

### 6.2 文件上传 (`/upload/image`, `/upload/mask`)

*   **`POST /upload/image`**: 上传图像文件。
    *   **方法**: `POST`
    *   **请求**: `multipart/form-data`。表单字段应包含一个名为 `image` 的文件，以及可选的 `overwrite` (boolean, 如果为true且文件名已存在则覆盖) 和 `subfolder` (string, 指定子文件夹)。
    *   **响应**: JSON对象，包含上传文件的 `name`, `subfolder`, 和 `type` (通常是 `input`)。
*   **`POST /upload/mask`**: 上传遮罩文件，行为与 `/upload/image` 类似，但通常用于特定的遮罩输入节点。

### 6.3 查看文件 (`/view`)

*   **`GET /view`**: 查看由ComfyUI生成或管理的图像/文件。
    *   **方法**: `GET`
    *   **查询参数**:
        *   `filename`: 要查看的文件名。
        *   `subfolder`: 文件所在的子文件夹 (例如 `outputs`, `inputs`, `temp`)。
        *   `type`: 文件夹类型 (例如 `output`, `input`, `temp`)。
        *   `channel`: 对于多通道图像 (如预览)，可以是 `rgb`, `alpha`, `rgba`。
        *   `preview`: (可选) 预览格式，如 `png`, `jpeg`。
    *   **响应**: 文件内容，Content-Type取决于文件类型。

### 6.4 查看元数据 (`/view_metadata/{folder_type}/{filename}`)

*   **`GET /view_metadata/{folder_type}/{filename}`**: 获取特定文件的元数据，通常是嵌入在PNG图像中的工作流信息。
    *   **方法**: `GET`
    *   **URL参数**:
        *   `folder_type`: 如 `outputs`。
        *   `filename`: 文件名。
    *   **响应**: JSON对象，包含 `workflow` (原始工作流的JSON字符串) 和 `prompt` (处理后的工作流JSON对象)。

### 6.5 队列管理

*   **`GET /queue`**: 获取当前队列状态。
    *   **响应**: JSON对象，包含 `queue_running` (当前正在执行的任务列表) 和 `queue_pending` (等待执行的任务列表)。
*   **`POST /queue`**: 修改队列。
    *   **请求体**: JSON对象，例如 `{"delete": ["prompt_id1", "prompt_id2"]}` 来删除队列中的任务，或 `{"clear": true}` 来清空队列。
*   **`POST /interrupt`**: 中断当前正在执行的任务。
    *   **响应**: 空响应或确认信息。
*   **`POST /free`**: 释放GPU内存，中断当前任务并清空队列。
    *   **请求体**: JSON对象，例如 `{"unload_models": true, "free_memory": true}`。

### 6.6 历史记录

*   **`GET /history`**: 获取已执行任务的历史记录。
    *   **响应**: JSON对象，键是 `prompt_id`，值是包含该任务详细信息的对象 (如 `outputs`, `status`, `prompt`)。
*   **`GET /history/{prompt_id}`**: 获取特定 `prompt_id` 的历史记录。
*   **`POST /history`**: 修改历史记录，例如 `{"clear": true}` 来清空历史，或 `{"delete": ["prompt_id1"]}` 来删除特定条目。

### 6.7 系统和模型信息

*   **`GET /system_stats`**: 获取系统统计信息 (CPU, GPU, RAM 使用情况)。
*   **`GET /object_info`**: 获取所有可用节点及其属性的详细信息。
    *   **响应**: 一个大的JSON对象，键是节点 `class_type`，值包含节点的 `input`, `output`, `name`, `display_name`, `description`, `category` 等。
*   **`GET /object_info/{node_class_type}`**: 获取特定节点类的信息。
*   **`GET /embeddings`**: 列出可用的embedding/Lora模型。
*   **`GET /extensions`**: 列出已加载的JavaScript扩展。
*   **`GET /models`**: (实验性) 列出模型，可带 `type` (e.g., `checkpoints`, `loras`, `controlnet`) 和 `name` 查询参数。

### 6.8 用户和设置

*   **`GET /users`**, **`POST /users`**, **`DELETE /users/{user_id}`**: 用户管理 (如果启用了用户账户)。
*   **`GET /userdata`**, **`POST /userdata`**: 用户特定数据 (如果启用了用户账户)。
*   **`GET /settings`**, **`POST /settings`**: 获取和修改应用设置 (如在 <mcfile name="app_settings.py" path="app/app_settings.py"></mcfile> 中定义的)。
*   **`GET /i18n/{lang}`**: 获取国际化翻译文本。

## 7. 错误处理

API请求失败时，ComfyUI会返回相应的HTTP状态码和可能的JSON错误信息。

*   **4xx 客户端错误**: 通常表示请求本身有问题 (例如，无效的JSON，缺少必要的参数，认证失败)。
*   **5xx 服务器错误**: 表示服务器端在处理请求时发生了错误。

建议在客户端实现适当的错误处理和重试逻辑。
通过WebSocket连接，`execution_error` 类型的消息会提供关于工作流执行失败的详细信息。

## 8. 示例代码

### 8.1 Python 示例 (使用 `requests` 库)

```python
import requests
import json
import time
import uuid

COMFYUI_URL = "http://127.0.0.1:8188"
CLIENT_ID = str(uuid.uuid4())

# 工作流JSON (从ComfyUI导出或手动构建)
# 替换为您自己的工作流
prompt_workflow = {
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
    "_meta": {
      "title": "KSampler"
    }
  },
  "4": {
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly.safetensors" # 确保模型文件存在
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "6": {
    "inputs": {
      "text": "masterpiece, best quality, beautiful girl",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "Positive Prompt"
    }
  },
  "7": {
    "inputs": {
      "text": "bad, ugly, worst quality",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "Negative Prompt"
    }
  },
  "8": {
    "inputs": {
      "filename_prefix": "ComfyUI_API_Example",
      "images": ["3", 0]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  }
}

def queue_prompt(prompt_workflow_json):
    payload = {
        "prompt": prompt_workflow_json,
        "client_id": CLIENT_ID
        # 如果需要API Key:
        # "extra_data": {"api_key": "YOUR_API_KEY"}
    }
    try:
        response = requests.post(f"{COMFYUI_URL}/prompt", json=payload)
        response.raise_for_status() # 如果HTTP状态码是4xx或5xx，则抛出异常
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error queuing prompt: {e}")
        if e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

def get_history(prompt_id):
    try:
        response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting history: {e}")
        return None

def get_image(filename, subfolder, folder_type):
    try:
        response = requests.get(f"{COMFYUI_URL}/view", params={
            'filename': filename,
            'subfolder': subfolder,
            'type': folder_type
        })
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error getting image: {e}")
        return None

if __name__ == "__main__":
    # 1. 提交工作流
    queued_prompt_info = queue_prompt(prompt_workflow)
    if queued_prompt_info and 'prompt_id' in queued_prompt_info:
        prompt_id = queued_prompt_info['prompt_id']
        print(f"Queued prompt with ID: {prompt_id}")

        # 2. 轮询历史记录直到任务完成 (或者使用WebSocket进行实时更新)
        # 注意：在实际应用中，使用WebSocket会更高效
        output_images = {}
        while True:
            history = get_history(prompt_id)
            if history and prompt_id in history:
                prompt_history = history[prompt_id]
                if 'outputs' in prompt_history and prompt_history['outputs']:
                    # 检查是否有输出，并且任务是否完成 (通常SaveImage节点执行完代表完成)
                    # 这里的完成条件可能需要根据您的工作流调整
                    is_done = False
                    for node_id, node_output in prompt_history['outputs'].items():
                        if 'images' in node_output: # 假设输出节点是SaveImage或类似节点
                            is_done = True
                            for image_data in node_output['images']:
                                if image_data['type'] == 'output': # 确保是最终输出图像
                                    image_filename = image_data['filename']
                                    image_subfolder = image_data['subfolder']
                                    output_images[image_filename] = (image_subfolder, image_data['type'])
                    if is_done:
                        print("Prompt execution finished.")
                        break
            print("Waiting for prompt execution to complete...")
            time.sleep(2) # 等待2秒后重试

        # 3. 下载生成的图像
        for filename, (subfolder, folder_type) in output_images.items():
            print(f"Fetching image: {filename} from subfolder: {subfolder}")
            image_bytes = get_image(filename, subfolder, folder_type)
            if image_bytes:
                with open(filename, 'wb') as f:
                    f.write(image_bytes)
                print(f"Saved image {filename}")
    else:
        print("Failed to queue prompt.")

```

### 8.2 `curl` 示例

**提交Prompt:**

```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{
           "prompt": { /* 您的工作流JSON */ }, 
           "client_id": "my_curl_client"
         }' \
     http://127.0.0.1:8188/prompt
```

**获取队列状态:**

```bash
curl http://127.0.0.1:8188/queue
```

**获取特定Prompt历史:**

```bash
curl http://127.0.0.1:8188/history/YOUR_PROMPT_ID
```

## 9. 版本控制

ComfyUI的API可能会随着版本更新而发生变化。建议关注ComfyUI的更新日志和官方文档，以了解最新的API变更。

## 10. 安全注意事项

*   **网络暴露**: 如果将ComfyUI API暴露到公共网络，请务必采取适当的安全措施，例如使用反向代理、防火墙、HTTPS加密，并考虑启用API密钥认证或更强的认证机制。
*   **输入验证**: 提交到API的工作流和参数应进行验证，以防止潜在的恶意输入。
*   **资源限制**: 长时间运行或资源密集型的工作流可能会消耗大量服务器资源。考虑实施速率限制或队列管理策略。

## 11. 附录：API端点列表 (总结)

以下是根据代码库分析识别出的主要API端点分组：

*   **核心执行**:
    *   `POST /prompt`: 提交工作流执行
*   **队列管理**:
    *   `GET /queue`: 查看队列
    *   `POST /queue`: 修改队列 (删除, 清空)
    *   `POST /interrupt`: 中断当前任务
    *   `POST /free`: 释放资源，清空队列
*   **历史记录**:
    *   `GET /history`: 查看所有历史
    *   `GET /history/{prompt_id}`: 查看特定任务历史
    *   `POST /history`: 修改历史 (删除, 清空)
*   **文件操作**:
    *   `POST /upload/image`: 上传图片
    *   `POST /upload/mask`: 上传遮罩
    *   `GET /view`: 查看文件 (图片等)
    *   `GET /view_metadata/{folder_type}/{filename}`: 查看文件元数据
*   **WebSocket**:
    *   `GET /ws`: WebSocket连接，用于实时状态更新
*   **系统与节点信息**:
    *   `GET /system_stats`: 系统状态
    *   `GET /object_info`: 所有节点信息
    *   `GET /object_info/{node_class_type}`: 特定节点信息
    *   `GET /embeddings`: Lora/Embedding列表
    *   `GET /extensions`: JS扩展列表
    *   `GET /models`: (实验性) 模型列表
*   **用户与设置 (如果启用)**:
    *   `GET, POST, DELETE /users`: 用户管理
    *   `GET, POST /userdata`: 用户数据
    *   `GET, POST /settings`: 应用设置
    *   `GET /i18n/{lang}`: 国际化文本
*   **工作流模板 (如果启用)**:
    *   `GET, POST, PUT, DELETE /workflow_templates`: 管理工作流模板

请注意，某些端点（如用户管理、工作流模板）可能依赖于特定的配置或ComfyUI的扩展功能。

希望这份文档能帮助您成功接入ComfyUI API！