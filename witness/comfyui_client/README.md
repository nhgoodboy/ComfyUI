# ComfyUI Python 客户端

一个功能完整的 Python 客户端库，用于与 ComfyUI API 进行交互。

## 🎯 功能特性

### ✅ 完整的 API 覆盖
- **提示和队列管理**: 提交工作流、管理队列、获取历史记录
- **文件操作**: 上传图片、下载结果、预览图片、通道分离
- **系统信息**: 获取系统状态、节点信息、模型列表
- **模型管理**: 浏览模型类型、获取模型元数据
- **WebSocket 支持**: 实时任务状态推送
- **批量操作**: 队列清理、历史管理、内存释放

### 🚀 高级功能
- **API 前缀支持**: 支持 `/api` 前缀的所有端点
- **异步操作**: 完整的 asyncio 支持
- **错误处理**: 详细的异常类型和重试机制
- **配置管理**: 灵活的配置选项，适应不同场景
- **连接管理**: 连接池、超时控制、健康检查
- **便捷方法**: 高级封装，简化常用操作

## 📦 安装

```bash
# 从源码安装
git clone <repository-url>
cd comfyui_client
pip install -r requirements.txt
```

## 🚀 快速开始

### 基本用法

```python
import asyncio
from comfyui_client import ComfyUIClient

async def main():
    # 创建客户端
    client = ComfyUIClient(
        server_address="127.0.0.1",
        port=8188
    )
    
    try:
        # 健康检查
        is_healthy = await client.health_check()
        print(f"服务器状态: {'正常' if is_healthy else '异常'}")
        
        # 获取系统信息
        stats = await client.system.get_system_stats()
        print(f"系统信息: {stats['system']['comfyui_version']}")
        
        # 获取可用模型
        models = await client.models.get_model_types()
        print(f"可用模型类型: {len(models)}")
        
        # 上传图片
        with open("test.png", "rb") as f:
            result = await client.files.upload_image(
                image_bytes=f.read(),
                filename="test.png"
            )
        print(f"图片上传成功: {result['name']}")
        
    finally:
        await client.close()

# 运行示例
asyncio.run(main())
```

### 高级配置

```python
from comfyui_client import ComfyUIClient, ComfyUIClientConfig

# 创建自定义配置
config = ComfyUIClientConfig(
    request_timeout=60.0,
    max_retries=5,
    retry_delay=2.0,
    log_requests=True
)

# 使用 API 前缀
client = ComfyUIClient(
    server_address="127.0.0.1",
    port=8188,
    config=config,
    use_api_prefix=True  # 使用 /api 前缀
)
```

### 预定义配置

```python
# 快速响应配置（低延迟）
config = ComfyUIClientConfig.create_fast()

# 健壮配置（不稳定网络）
config = ComfyUIClientConfig.create_robust()

# 生产环境配置
config = ComfyUIClientConfig.create_production()
```

## 📋 API 端点覆盖

### 系统端点
- `GET /system_stats` - 系统统计信息
- `GET /object_info` - 节点信息
- `GET /object_info/{node_class}` - 特定节点信息
- `GET /extensions` - 扩展列表
- `GET /embeddings` - 嵌入列表

### 模型端点
- `GET /models` - 模型类型列表
- `GET /models/{folder}` - 特定文件夹模型
- `GET /view_metadata/{folder_name}` - 模型元数据

### 提示和队列端点
- `GET /prompt` - 提示信息
- `POST /prompt` - 提交提示
- `GET /queue` - 队列状态
- `POST /queue` - 队列操作
- `POST /interrupt` - 中断任务
- `POST /free` - 释放内存

### 历史记录端点
- `GET /history` - 获取历史
- `GET /history/{prompt_id}` - 特定历史
- `POST /history` - 历史操作

### 文件端点
- `POST /upload/image` - 上传图片
- `POST /upload/mask` - 上传遮罩
- `GET /view` - 查看文件
- 支持预览、通道分离等高级功能

### WebSocket 端点
- `GET /ws` - WebSocket 连接
- 实时任务状态推送

## 💡 使用示例

### 工作流提交和等待

```python
async def submit_workflow():
    client = ComfyUIClient()
    
    # 定义工作流
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"}
        }
        # ... 更多节点
    }
    
    try:
        # 提交并等待完成
        result = await client.submit_and_wait(
            workflow, 
            timeout=300.0
        )
        print(f"工作流完成: {result}")
        
    finally:
        await client.close()
```

### 文件操作

```python
async def file_operations():
    client = ComfyUIClient()
    
    try:
        # 上传图片
        with open("input.png", "rb") as f:
            upload_result = await client.files.upload_image(
                image_bytes=f.read(),
                filename="input.png",
                overwrite=True
            )
        
        # 下载图片
        image_data = await client.files.download_image(
            filename="output.png"
        )
        
        # 获取预览
        preview_data = await client.files.view_image_preview(
            filename="output.png",
            format="webp",
            quality=80
        )
        
        # 获取特定通道
        alpha_channel = await client.files.view_image_channel(
            filename="output.png",
            channel="a"
        )
        
    finally:
        await client.close()
```

### 批量操作

```python
async def batch_operations():
    client = ComfyUIClient()
    
    try:
        # 并发获取多种信息
        tasks = [
            client.system.get_system_stats(),
            client.models.get_model_types(),
            client.prompts.get_queue(),
            client.system.get_embeddings(),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 批量清理
        await client.prompts.clear_queue()
        await client.prompts.clear_all_history()
        await client.prompts.free_memory(
            unload_models=True,
            free_memory=True
        )
        
    finally:
        await client.close()
```

### WebSocket 实时监控

```python
async def websocket_monitor():
    client = ComfyUIClient()
    
    # 获取 WebSocket 客户端
    ws_client = client.get_websocket()
    
    # 定义消息处理器
    async def handle_message(data):
        print(f"收到消息: {data}")
    
    try:
        # 连接并监听
        await ws_client.connect()
        # 处理消息...
        
    finally:
        await ws_client.close()
        await client.close()
```

## 🛠️ 错误处理

```python
from comfyui_client.exceptions import (
    ComfyUIConnectionError,
    ComfyUIAPIError,
    ComfyUITimeoutError,
    ComfyUIValidationError
)

async def error_handling():
    client = ComfyUIClient()
    
    try:
        result = await client.system.get_system_stats()
        
    except ComfyUIConnectionError as e:
        print(f"连接错误: {e}")
    except ComfyUITimeoutError as e:
        print(f"超时错误: {e}")
    except ComfyUIAPIError as e:
        print(f"API错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")
    finally:
        await client.close()
```

## 🧪 测试

运行 API 覆盖度测试：

```bash
python examples/api_coverage_test.py
```

运行高级用法示例：

```bash
python examples/advanced_usage_example.py
```

## ⚙️ 配置选项

### 网络配置
- `request_timeout`: HTTP 请求超时
- `connect_timeout`: 连接超时
- `read_timeout`: 读取超时

### 重试配置
- `max_retries`: 最大重试次数
- `retry_delay`: 重试间隔
- `retry_backoff`: 重试延迟倍数

### 连接池配置
- `max_connections`: 最大连接数
- `max_connections_per_host`: 每主机最大连接数

### WebSocket 配置
- `websocket_timeout`: WebSocket 超时
- `websocket_ping_interval`: 心跳间隔
- `websocket_debug`: 调试模式

### 其他配置
- `use_api_prefix`: 使用 /api 前缀
- `verify_ssl`: SSL 验证
- `enable_compression`: 启用压缩
- `log_requests`: 记录请求日志

## 🏗️ 架构设计

- **模块化设计**: 按功能分离的端点模块
- **异步优先**: 完整的 asyncio 支持
- **错误恢复**: 智能重试和错误处理
- **资源管理**: 自动连接池管理
- **扩展性**: 易于添加新功能

## ✅ API 兼容性

✅ **100% 兼容** ComfyUI 官方 API  
✅ **支持** API 前缀 (`/api`)  
✅ **覆盖** 所有核心端点  
✅ **实时支持** WebSocket 通信  

## 📄 许可证

MIT License