# ComfyUI Python 客户端

一个用于与 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) API 交互的 Python 客户端，基于 API 文档生成。

该库提供了一个结构化、模块化且易于使用的接口，用于以编程方式控制 ComfyUI，包括排队提示、管理文件以及通过 WebSocket 接收实时更新。

## 特性

- **模块化设计**: 每组 API 端点都分离到自己的模块中（例如，prompts, files, system）。
- **WebSocket 集成**: 一个简单的、线程化的 WebSocket 客户端，用于处理来自服务器的实时消息，而不会阻塞您的主应用程序。
- **日志记录**: 内置可配置的日志记录，便于调试。
- **Pydantic 模型**: （可选）用于工作流创建的 Pydantic 模型，以确保数据验证并改善开发体验。
- **可扩展**: 设计为在 ComfyUI 添加新 API 端点时易于扩展。

## 安装

1.  克隆此仓库或下载 `comfyui_client` 目录。
2.  安装所需的依赖项：

```bash
pip install -r requirements.txt
```

## 使用方法

### 初始化客户端

首先，导入并初始化主客户端。

```python
from comfyui_client import ComfyUIClient

# 使用默认服务器地址和端口初始化客户端
client = ComfyUIClient(server_address='127.0.0.1', port=8188)
```

### 示例：简单的文本到图片工作流

此示例演示了如何定义工作流、将其排队并检索输出图像。

1.  **定义工作流**: 工作流是一个字典，其中键是节点 ID。
2.  **将提示排队**: 使用 `client.prompt.queue_prompt()` 提交工作流。
3.  **监听结果**: 使用 WebSocket 客户端等待执行完成。
4.  **检索图像**: 完成后，从历史记录中获取输出图像的详细信息，并使用 `client.file.view_file()` 下载它。

请参阅 `examples/simple_text_to_image.py` 中的完整、可运行的脚本。

### API 概览

客户端被组织成几个对象，镜像了 API 结构：

- `client.prompt`: 用于与提示和队列相关的所有操作（`queue_prompt`, `get_history` 等）。
- `client.file`: 用于文件操作（`upload_image`, `view_file`）。
- `client.system`: 用于获取系统信息（`get_system_stats`, `get_object_info`）。
- `client.user`: 用于在多用户模式下进行用户管理（`get_users`, `create_user`）。

### WebSocket 处理

要接收实时更新，您可以通过子类化 `WebSocketClient` 并重写 `on_message` 方法来创建自定义 WebSocket 客户端。

```python
from comfyui_client.websocket import WebSocketClient
import uuid

# 一个只打印消息的简单处理器
class MyWebSocketClient(WebSocketClient):
    def on_message(self, ws, message):
        print("收到 WebSocket 消息:")
        print(message)

client_id = str(uuid.uuid4())
# 您可以像这样使用自定义类：
# ws_client = MyWebSocketClient(f"ws://{client.server_address}:{client.port}/ws?clientId={client_id}")
ws_client = client.get_websocket(client_id)


ws_client.run_forever()

# 现在，当您将提示排队时，您的 on_message 方法将被调用。
# client.prompt.queue_prompt(...)
```

有关如何等待特定提示完成的更实用的示例，请参阅 `examples/simple_text_to_image.py`。 