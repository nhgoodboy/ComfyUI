# ComfyUI Python 客户端

一个用于与 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) API 交互的 Python 客户端，基于 API 文档生成。

该库提供了一个结构化、模块化且易于使用的接口，用于以编程方式控制 ComfyUI，包括排队提示、管理文件以及通过 WebSocket 接收实时更新。
本客户端是对 ComfyUI 底层 API 的一层封装，详细的底层 API 技术规格可以参考文档：**[ComfyUI API 开发文档](../../docs/comfyui_api.md)**。

## 特性

- **模块化设计**: 每组 API 端点都分离到自己的模块中（例如，prompts, files, system）。
- **WebSocket 集成**: 一个简单的、线程化的 WebSocket 客户端，用于处理来自服务器的实时消息，而不会阻塞您的主应用程序。
- **日志记录**: 内置可配置的日志记录，便于调试。
- **Pydantic 模型**: （可选）用于工作流创建的 Pydantic 模型，以确保数据验证并改善开发体验。
- **可扩展**: 设计为在 ComfyUI 添加新 API 端点时易于扩展。

## 安装

1.  克隆此仓库。
2.  从项目根目录 (`witness/`) 安装所需的依赖项：

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

**核心API**：
- `client.prompts`: 用于与提示和队列相关的所有操作（`queue_prompt`, `get_history`, `interrupt`, `free_memory` 等）
- `client.files`: 用于文件操作（`upload_image`, `upload_mask`, `view_file`）
- `client.system`: 用于获取系统信息（`get_system_stats`, `get_object_info`, `get_embeddings`, `get_extensions`）
- `client.user`: 用于用户管理和设置（`get_users`, `create_user`, `get_settings`, `update_settings`）

**扩展API**：
- `client.models`: 用于模型管理（`get_model_types`, `get_models`, `get_model_metadata`）
- `client.userdata`: 用于用户数据文件管理（`list_userdata`, `upload_userdata_file`, `delete_userdata_file`）
- `client.internal`: 用于内部系统监控（`get_logs`, `get_raw_logs`, `get_folder_paths`）

**向后兼容**：
- `client.file`: `client.files` 的别名，保持向后兼容性

### WebSocket 处理

要接收实时更新，您可以通过子类化 `ComfyUIWebSocketClient` 并重写 `on_message` 方法来创建自定义 WebSocket 客户端。

```python
from comfyui_client.websocket import ComfyUIWebSocketClient
import uuid

# 一个只打印消息的简单处理器
class MyWebSocketClient(ComfyUIWebSocketClient):
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

## 完整API参考

### 提示和队列管理 (client.prompts)
| 方法 | 描述 | HTTP路径 |
|------|------|----------|
| `queue_prompt(prompt, client_id)` | 提交工作流到队列 | `POST /prompt` |
| `get_queue()` | 获取当前队列状态 | `GET /queue` |
| `get_history(prompt_id)` | 获取执行历史 | `GET /history[/{prompt_id}]` |
| `interrupt()` | 中断当前执行 | `POST /interrupt` |
| `delete_from_queue(prompt_ids)` | 从队列删除项目 | `POST /queue` |
| `get_prompt_info()` | 获取队列信息 | `GET /prompt` |
| `free_memory(unload_models, free_memory)` | 释放内存 | `POST /free` |
| `clear_history(clear, delete)` | 清理历史记录 | `POST /history` |

### 文件管理 (client.files)
| 方法 | 描述 | HTTP路径 |
|------|------|----------|
| `upload_image(image_bytes/path, filename, overwrite, subfolder)` | 上传图像 | `POST /upload/image` |
| `upload_mask(image_bytes/path, original_ref, ...)` | 上传遮罩 | `POST /upload/mask` |
| `view_file(filename, file_type, subfolder)` | 查看文件 | `GET /view` |

### 系统信息 (client.system)
| 方法 | 描述 | HTTP路径 |
|------|------|----------|
| `get_system_stats()` | 获取系统统计 | `GET /system_stats` |
| `get_object_info(node_class)` | 获取节点信息 | `GET /object_info[/{node_class}]` |
| `get_extensions()` | 获取扩展列表 | `GET /extensions` |
| `get_embeddings()` | 获取嵌入列表 | `GET /embeddings` |

### 用户管理 (client.user)
| 方法 | 描述 | HTTP路径 |
|------|------|----------|
| `get_users()` | 获取用户列表 | `GET /users` |
| `create_user(username)` | 创建用户 | `POST /users` |
| `get_settings()` | 获取用户设置 | `GET /settings` |
| `update_settings(new_settings)` | 更新用户设置 | `POST /settings` |
| `get_setting(setting_id)` | 获取特定设置 | `GET /settings/{id}` |
| `update_setting(setting_id, value)` | 更新特定设置 | `POST /settings/{id}` |

### 模型管理 (client.models)
| 方法 | 描述 | HTTP路径 |
|------|------|----------|
| `get_model_types()` | 获取模型类型列表 | `GET /models` |
| `get_models(folder)` | 获取模型文件列表 | `GET /models/{folder}` |
| `get_model_metadata(folder_name, filename)` | 获取模型元数据 | `GET /view_metadata/{folder_name}` |

### 用户数据管理 (client.userdata)
| 方法 | 描述 | HTTP路径 |
|------|------|----------|
| `list_userdata(dir, recurse, full_info, split)` | 列出用户数据 | `GET /userdata` |
| `list_userdata_v2(path)` | 列出用户数据v2 | `GET /v2/userdata` |
| `get_userdata_file(file)` | 获取用户数据文件 | `GET /userdata/{file}` |
| `upload_userdata_file(file, data, overwrite, full_info)` | 上传用户数据文件 | `POST /userdata/{file}` |
| `delete_userdata_file(file)` | 删除用户数据文件 | `DELETE /userdata/{file}` |
| `move_userdata_file(file, dest, overwrite, full_info)` | 移动用户数据文件 | `POST /userdata/{file}/move/{dest}` |

### 内部API (client.internal)
| 方法 | 描述 | HTTP路径 |
|------|------|----------|
| `get_logs()` | 获取系统日志 | `GET /internal/logs` |
| `get_raw_logs()` | 获取原始日志数据 | `GET /internal/logs/raw` |
| `subscribe_logs(client_id, enabled)` | 订阅日志更新 | `PATCH /internal/logs/subscribe` |
| `get_folder_paths()` | 获取文件夹路径配置 | `GET /internal/folder_paths` | 