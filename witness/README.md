# ComfyUI Witness 系统

该系统提供了一种模块化且可扩展的方式来与 ComfyUI API 进行交互。
它旨在涵盖 ComfyUI API 主文档中记录的所有可用 API 端点。

## 项目结构

```
witness/
├── config/               # 配置文件
│   ├── __init__.py
│   └── settings.py       # API URL、API 密钥（可选）、WebSocket URL、超时
├── core/                 # 核心逻辑、编排（目前最少）
│   └── __init__.py
├── api_clients/          # 不同 ComfyUI API 组的客户端
│   ├── __init__.py
│   ├── prompt_client.py    # 处理用于工作流执行的 /prompt 端点
│   ├── history_client.py   # 处理 /history 端点
│   ├── queue_client.py     # 处理 /queue、/interrupt、/free 端点
│   ├── file_client.py      # 处理 /upload/image、/upload/mask、/view、/view_metadata
│   ├── system_client.py    # 处理 /system_stats、/object_info、/embeddings 等
│   ├── websocket_client.py # 处理 /ws WebSocket 通信
│   └── user_client.py      # 处理 /users、/userdata、/settings、/i18n
├── utils/                # 工具函数
│   ├── __init__.py
│   └── http_client.py    # 'requests' 的包装器，用于 API 调用
├── main.py               # 所有客户端示例用法的主入口点
├── requirements.txt      # 项目依赖项
└── README.md
```

## 设置和运行

1.  **先决条件：**
    *   Python 3.7+
    *   正在运行的 ComfyUI 实例（可通过 HTTP/WebSocket 访问）。

2.  **安装：**
    ```bash
    git clone <repository_url> # 或下载文件
    cd witness
    pip install -r requirements.txt
    ```

3.  **配置：**
    *   编辑 `witness/config/settings.py` 以设置您的 ComfyUI API URL (`COMFYUI_API_URL`) 和 WebSocket URL (`COMFYUI_WS_URL`)。
    *   如果您的 ComfyUI 实例需要 API 密钥（例如，使用 `--api-key-required` 启动），请在 `settings.py` 中设置 `COMFYUI_API_KEY`。否则，可以将其保留为 `None`。

4.  **运行示例：**
    `main.py` 脚本演示了如何使用各种 API 客户端。
    ```bash
    python main.py
    ```
    此脚本将：
    *   连接到 ComfyUI WebSocket。
    *   获取系统统计信息和队列信息。
    *   对示例图像生成工作流进行排队（您可能需要根据可用的模型和自定义节点调整 `main.py` 中的工作流）。
    *   获取已排队提示的历史记录。
    *   演示其他客户端功能。
    *   观察 WebSocket 消息以获取来自 ComfyUI 的实时更新。

## API 客户端模块

*   **`HttpClient` (`utils/http_client.py`):** 一个实用程序类，它包装 `requests` 库以向 ComfyUI API 发出 HTTP GET、POST 和 multipart POST 请求。它处理基本 URL 连接、超时设置以及相关端点的 API 密钥注入。
*   **`PromptClient` (`api_clients/prompt_client.py`):** 管理与 `/prompt` 端点的交互，以对工作流进行排队以供执行。
*   **`HistoryClient` (`api_clients/history_client.py`):** 提供获取执行历史记录（所有提示或特定提示 ID）和清除历史记录的方法。
*   **`QueueClient` (`api_clients/queue_client.py`):** 处理队列管理操作，例如获取队列状态、清除队列、删除特定项目、中断任务和释放资源。
*   **`FileClient` (`api_clients/file_client.py`):** 便于从 ComfyUI 的输出/输入目录上传文件（图像、掩码）以及查看文件及其元数据。
*   **`SystemClient` (`api_clients/system_client.py`):** 与提供系统统计信息、节点/对象信息、可用嵌入/Loras、扩展和模型列表的端点进行交互。
*   **`UserClient` (`api_clients/user_client.py`):** （实验性）处理与用户管理、用户特定数据、设置和国际化 (i18n) 数据相关的端点。
*   **`WebSocketClient` (`api_clients/websocket_client.py`):** 建立并管理与 ComfyUI 的 `/ws` 端点的 WebSocket 连接，以接收有关提示执行、队列状态和其他事件的实时更新。它在单独的线程中运行。

## 可扩展性

*   **添加新的 API 端点：** 要支持新的 ComfyUI API 端点，您可以扩展 `api_clients/` 中的现有客户端类，或者如果新端点代表一组不同的功能，则可以创建新的客户端文件。
*   **自定义工作流：** `main.py` 脚本演示了如何对基本工作流进行排队。您可以用任何有效的 ComfyUI 工作流 JSON 替换 `sample_workflow` 字典。
*   **配置：** 可以根据需要扩展 `config/settings.py` 文件以包含更多配置选项。

该系统为通过 Python 以编程方式与 ComfyUI API 交互提供了一个基础库。