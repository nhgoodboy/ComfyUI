# ComfyUI API 开发文档

## 简介

ComfyUI 提供了一个强大的后端 API，允许开发者通过 HTTP 请求和 WebSocket 与其进行编程交互。该 API 旨在实现对 ComfyUI 核心功能的完全控制，包括工作流（提示）的排队、系统状态的监控、模型的管理等。

本文档详细介绍了可用的 API 端点、数据格式和通信协议。

**核心原则:**

*   **HTTP API**: 主要用于无状态的请求-响应交互，例如提交工作流或获取信息。
*   **WebSocket API**: 用于从服务器接收实时的、事件驱动的更新，例如执行状态、进度和新产出的图像。
*   **工作流为核心**: ComfyUI 的核心操作围绕"提示"或"工作流"展开。这些是以 JSON 格式定义和提交的节点图。

## 认证

API 的认证行为取决于服务器的启动模式。

### 单用户模式 (默认)

在默认的单用户模式下，API 没有明确的用户认证机制。然而，为了防止跨站请求伪造（CSRF）攻击，服务器会检查 HTTP 请求的 `Host` 和 `Origin` 头部。在大多数情况下，从浏览器外部（例如，从 Python 脚本）直接调用 API 时，这不会成为问题。

### 多用户模式

当使用 `--multi-user` 命令行参数启动 ComfyUI 时，服务器会启用多用户模式。在这种模式下，每个 API 请求都必须包含一个 `comfy-user` HTTP 头部来标识发出请求的用户。

*   **Header**: `comfy-user: <user_id>`

`<user_id>` 是通过 `/users` 端点创建或检索到的用户唯一标识符。

## WebSocket API

WebSocket API 是接收来自 ComfyUI 服务器实时事件更新的主要方式。这对于监控排队的提示执行进度至关重要。

**连接:**

*   **URL**: `ws://<server_address>/ws?clientId=<client_id>`
*   `client_id`: 一个唯一的标识符，通常是一个 UUID。如果连接断开，使用相同的 `clientId` 重新连接可以恢复会话。

**服务器发送的消息:**

连接后，服务器将以 JSON 格式发送事件。每个事件对象都包含 `type` 和 `data` 字段。

| 事件类型 | 数据 | 描述 |
| :--- | :--- | :--- |
| `status` | `{"status": {"exec_info": ...}, "sid": "..."}` | 连接成功后发送的初始状态，包含当前队列信息和会话ID (`sid`)。 |
| `executing` | `{"node": "...", "prompt_id": "..."}` | 当工作流中的某个节点开始执行时发送。`node` 是正在执行的节点ID。 |
| `progress` | `{"value": ..., "max": ..., "node": "..."}` | 表示长时间运行的操作（如 KSampler）的进度。 |
| `executed` | `{"node": "...", "output": {...}, "prompt_id": "..."}` | 当一个节点执行完成时发送。`output` 字段包含该节点的输出数据。 |
| `execution_cached` | `{"nodes": [...], "prompt_id": "..."}` | 当一个或多个节点的输出从缓存中加载时发送。 |
| `execution_interrupted`| `{"prompt_id": "...", "execution_id": "...", "node_id": "..."}` | 当执行被用户中断时发送。 |
| `execution_error` | `{"prompt_id": "...", "node_id": "...", "exception_message": "..."}` | 当执行过程中发生错误时发送。 |

## HTTP API 端点

### 提示和队列管理

这是与 ComfyUI 交互的核心部分，用于执行工作流。

#### `POST /prompt`

将一个工作流（提示）添加到队列中等待执行。

*   **请求体 (Body)**: 一个包含 `prompt` 和 `client_id` 的 JSON 对象。
    *   `prompt`: 工作流的 JSON 表示。这是一个以节点ID为键，节点对象为值的字典。每个节点对象定义了其类别、输入和元数据。
    *   `client_id`: 发出请求的客户端的唯一ID。

*   **示例请求体**:
    ```json
    {
      "prompt": {
        "3": {
          "inputs": {
            "seed": 156684628608846,
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
          "class_type": "KSampler"
        },
        "4": { "inputs": { "ckpt_name": "v1-5-pruned-emaonly.ckpt" }, "class_type": "CheckpointLoaderSimple" },
        "5": { "inputs": { "width": 512, "height": 512, "batch_size": 1 }, "class_type": "EmptyLatentImage" },
        "6": { "inputs": { "text": "masterpiece, best quality, a beautiful girl", "clip": ["4", 1] }, "class_type": "CLIPTextEncode" },
        "7": { "inputs": { "text": "bad hands", "clip": ["4", 1] }, "class_type": "CLIPTextEncode" },
        "8": { "inputs": { "samples": ["3", 0], "vae": ["4", 2] }, "class_type": "VAEDecode" },
        "9": { "inputs": { "filename_prefix": "ComfyUI", "images": ["8", 0] }, "class_type": "SaveImage" }
      },
      "client_id": "your_client_id_here"
    }
    ```

*   **响应**:
    *   `200 OK`: 成功提交。响应体包含 `prompt_id` 和 `number`。
    ```json
    {
      "prompt_id": "a1d3...e8f2",
      "number": 1,
      "node_errors": {}
    }
    ```

#### `GET /queue`

获取当前队列中的项目。

*   **响应**:
    *   `queue_running`: 当前正在运行的提示列表。
    *   `queue_pending`: 等待执行的提示列表。
    ```json
    {
      "queue_running": [
        ["a1d3...e8f2", 6, { ...prompt... }, "client_id"]
      ],
      "queue_pending": []
    }
    ```

#### `GET /history`

获取已执行的提示历史。

*   **响应**: 一个以 `prompt_id` 为键的对象，包含了每个已执行提示的详细信息，包括其状态、输入、输出和时间。

#### `GET /history/{prompt_id}`

获取特定已执行提示的详细信息。

*   **URL 参数**:
    *   `prompt_id`: 要查询的提示ID。
*   **响应**: 与 `/history` 中单个条目相同的对象。

#### `POST /interrupt`

中断当前正在执行的提示。

*   **响应**: `200 OK`

#### `POST /queue`

修改队列，例如删除一个项目。

*   **请求体**:
    ```json
    {
      "delete": ["a1d3...e8f2"]
    }
    ```

### 文件和数据管理

#### `POST /upload/image`

上传一张图片到 ComfyUI 的输入目录。

*   **请求**: `multipart/form-data`
*   **表单字段**:
    *   `image`: 图像文件。
    *   `overwrite` (可选): 如果为 `true`，将覆盖同名文件。
    *   `subfolder` (可选): 指定要上传到的子文件夹。
*   **响应**:
    ```json
    {
      "name": "example.png",
      "subfolder": "my_uploads",
      "type": "input"
    }
    ```

#### `GET /view`

获取输出图像或其他文件。

*   **查询参数**:
    *   `filename`: 文件名。
    *   `subfolder`: 文件所在的子文件夹。
    *   `type`: 目录类型，通常是 `output`。
*   **响应**: 图像文件本身。

### 系统和节点信息

#### `GET /system_stats`

获取系统统计信息，包括内存和 GPU 使用情况。

#### `GET /object_info`

获取所有可用节点的详细信息，包括其名称、输入、输出和属性。这是动态构建工作流的关键。

#### `GET /object_info/{node_class}`

获取特定节点类别的详细信息。

### 用户和设置 (多用户模式)

#### `GET /users`

获取用户列表。

#### `POST /users`

创建一个新用户。

#### `/settings` Endpoints

*   `GET /settings`: 获取当前用户的设置。
*   `POST /settings`: 更新设置。

### 实验性 API

#### 模型管理

*   `GET /experiment/models`: 获取模型文件夹列表。
*   `GET /experiment/models/{folder}`: 获取指定文件夹中的模型列表。

### 自定义节点 API

#### `GET /workflow_templates`

获取一个包含自定义节点名称及其关联工作流模板的映射。

#### `GET /api/workflow_templates/{module_name}`

为给定的自定义节点模块提供静态工作流模板文件。

#### `GET /i18n`

从所有自定义节点的 `locales` 文件夹中获取翻译。

## 完整工作流示例 (Python)

下面是一个使用 Python 与 ComfyUI API 交互的完整示例。

```python
import websocket
import uuid
import json
import urllib.request
import urllib.parse
import random

server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request(f"http://{server_address}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{server_address}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done
        else:
            continue #previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
                output_images[node_id] = images_output

    return output_images

# 创建一个简单的文本到图像工作流
prompt_text = """
{
  "3": {
    "inputs": {
      "seed": 123,
      "steps": 20,
      "cfg": 8.0,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0,
      "model": [ "4", 0 ],
      "positive": [ "6", 0 ],
      "negative": [ "7", 0 ],
      "latent_image": [ "5", 0 ]
    },
    "class_type": "KSampler"
  },
  "4": {
    "inputs": { "ckpt_name": "v1-5-pruned-emaonly.ckpt" },
    "class_type": "CheckpointLoaderSimple"
  },
  "5": {
    "inputs": { "width": 512, "height": 512, "batch_size": 1 },
    "class_type": "EmptyLatentImage"
  },
  "6": {
    "inputs": {
      "text": "beautiful scenery nature glass bottle landscape, purple galaxy bottle,",
      "clip": [ "4", 1 ]
    },
    "class_type": "CLIPTextEncode"
  },
  "7": {
    "inputs": { "text": "text, watermark", "clip": [ "4", 1 ] },
    "class_type": "CLIPTextEncode"
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI_API_Example",
      "images": [ "3", 0 ]
    },
    "class_type": "SaveImage"
  }
}
"""

prompt = json.loads(prompt_text)
# 为种子设置一个随机数
prompt["3"]["inputs"]["seed"] = random.randint(0, 9999999999)


ws = websocket.WebSocket()
ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
images = get_images(ws, prompt)

# 将接收到的图像保存到文件
for node_id in images:
    for i, image_data in enumerate(images[node_id]):
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(image_data))
        image.save(f"output_{node_id}_{i}.png")
``` 