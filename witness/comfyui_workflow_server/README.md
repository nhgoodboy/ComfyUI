# ComfyUI Workflow Server (RPC Edition)

基于RPC架构的ComfyUI工作流微服务，专注于图像风格转换和文件下载处理。支持一对一WebSocket连接架构，实现多用户任务隔离和精确消息推送。

## 项目概述

这是一个采用JSON-RPC 2.0协议的微服务，为ComfyUI提供统一的RPC接口。支持从外部URL下载图片并进行风格转换，采用标准化的文件命名规范。通过基于user_id的精确消息路由，实现真正的多用户隔离。

## 主要特性

- **RPC架构**: 单一端点(`/rpc`)，JSON-RPC 2.0协议
- **文件下载**: 支持从外部URL下载图片，无需客户端上传
- **标准化命名**: 文件按`{style_id}_{user_id}_{request_id}_{input/output}.{ext}`格式命名
- **多阶段处理**: 下载→转换的完整生命周期管理
- **实时进度**: WebSocket支持任务状态和进度实时更新
- **进度精确跟踪**: 真实反映ComfyUI采样进度，过滤无关步骤
- **错误分类**: 系统化的错误代码体系(1xxx-3xxx)
- **request_id支持**: 端到端请求追踪和调试
- **文件结果管理**: 自动获取ComfyUI生成结果并构造访问URL
- **多用户隔离**: 基于user_id的完全任务和文件隔离
- **精确消息推送**: 基于任务中的user_id进行精确WebSocket推送
- **一对一连接支持**: 支持服务级别的WebSocket连接（如web_image_transform_service）

## RPC接口

### 单一端点
所有RPC调用统一使用：`POST /rpc`

### 风格管理方法
- `styles.list` - 获取所有可用风格
- `styles.search` - 搜索风格
- `styles.get` - 获取特定风格详情

### 转换任务方法
- `transform.create` - 创建转换任务（下载+转换）
- `transform.get_status` - 获取任务状态
- `transform.get_result` - 获取任务结果
- `transform.list` - 获取用户任务列表
- `transform.cancel` - 取消任务

### 系统方法
- `system.health` - 系统健康检查
- `system.build_filename` - 构建标准文件名
- `system.get_stats` - 获取系统统计信息

### WebSocket推送
- `GET /ws/{service_id}` - 实时任务状态和进度推送
  - **服务连接**: `/ws/web_image_transform_service` - 服务级别连接
  - 支持任务状态变化通知
  - 实时进度更新（下载进度、转换进度）
  - 任务完成结果推送
  - 心跳保活机制
  - **精确推送**: 基于任务中的user_id进行精确路由，不再广播
  - **一对一连接**: 单一服务连接，高效消息路由

## RPC调用示例

### 创建转换任务
```json
{
  "method": "transform.create",
  "params": {
    "user_id": "user123",
    "style_id": "anime_style",
    "image_url": "https://example.com/image.jpg",
    "request_id": "req123"
  },
  "id": "req_1"
}
```

### 获取风格列表
```json
{
  "method": "styles.list",
  "params": {},
  "id": "req_2"
}
```

### 获取任务状态
```json
{
  "method": "transform.get_status",
  "params": {
    "user_id": "user123",
    "request_id": "req_abc123"
  },
  "id": "req_3"
}
```

## 配置环境变量

```bash
# 基础配置
HOST=0.0.0.0
PORT=8000
DEBUG=false
ENVIRONMENT=production

# ComfyUI连接
COMFYUI_HOST=127.0.0.1
COMFYUI_PORT=8188
COMFYUI_TIMEOUT=300

# 文件存储配置
UPLOADS_DIR=uploads
OUTPUTS_DIR=outputs
MAX_FILE_SIZE=10485760
MAX_DOWNLOAD_SIZE=50485760

# 下载配置
DOWNLOAD_TIMEOUT=30
DOWNLOAD_RETRIES=3
ALLOWED_SCHEMES=http,https

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# CORS配置
CORS_ORIGINS=*
```

## 部署说明

### 开发环境
```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 生产环境
```bash
# 使用gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 文件命名规范

### 标准格式
```
{style_id}_{user_id}_{request_id}_{type}.{extension}
```

### 示例
- 输入文件：`anime_style_user123_req123_input.jpg`
- 输出文件：`anime_style_user123_req123_output.png`

### 文件组织
- 下载文件：`uploads/{filename}`
- 输出文件：`outputs/{filename}`
- 所有文件按标准命名格式存储

## 任务生命周期

1. **pending** - 任务已创建，等待处理
2. **downloading** - 正在下载图片
3. **downloaded** - 图片下载完成
4. **processing** - 正在进行风格转换
5. **completed** - 转换完成
6. **download_failed** - 下载失败
7. **processing_failed** - 转换失败

## 错误代码体系

- **1001-1099**: 通用错误（参数、验证等）
- **2001-2099**: 下载相关错误
- **3001-3099**: 转换处理错误

## 与客户端集成

### RPC客户端示例

```python
import aiohttp
import json
import uuid

class ComfyUIRPCClient:
    def __init__(self, base_url: str, user_id: str):
        self.base_url = base_url
        self.user_id = user_id
        self.rpc_url = f"{base_url}/rpc"
    
    async def create_transform(self, style_id: str, image_url: str, request_id: str = None):
        payload = {
            "method": "transform.create",
            "params": {
                "user_id": self.user_id,
                "style_id": style_id,
                "image_url": image_url,
                "request_id": request_id or str(uuid.uuid4())
            },
            "id": "req_1"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.rpc_url, json=payload) as resp:
                result = await resp.json()
                return result["result"]
```

### WebSocket监听

```python
import websockets
import json

async def listen_updates(service_id: str = "web_image_transform_service"):
    uri = f"ws://localhost:8000/ws/{service_id}"
    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            # 忽略心跳消息
            if message == 'pong':
                continue
                
            data = json.loads(message)
            if data.get('type') == 'task_update':
                request_id = data.get('request_id')
                task_data = data.get('data', {})
                status = task_data.get('status')
                progress = task_data.get('progress', 0)
                message = task_data.get('message', '')
                
                print(f"任务 {request_id}: {status} ({progress}%) - {message}")
                
                # 处理任务完成
                if status == 'completed' and 'result' in task_data:
                    result = task_data['result']
                    if 'files' in result:
                        output_files = result['files'].get('output', [])
                        print(f"生成文件: {output_files}")
```

## 目录结构

```
app/
├── rpc/
│   ├── __init__.py
│   ├── handler.py       # RPC请求处理器
│   ├── router.py        # RPC方法路由
│   ├── protocol.py      # RPC协议模型
│   ├── exceptions.py    # RPC异常定义
│   ├── error_codes.py   # 错误代码定义
│   ├── formatter.py     # 响应格式化器
│   ├── validator.py     # 参数验证器
│   └── methods/
│       ├── styles.py    # 风格管理方法
│       ├── transform.py # 转换任务方法
│       └── system.py    # 系统方法
├── services/
│   ├── comfyui_service.py       # ComfyUI客户端服务
│   ├── download_service.py      # 文件下载服务
│   └── transform_task_service.py # 转换任务服务
├── utils/
│   ├── file_naming.py    # 文件命名工具
│   ├── websocket_push.py # WebSocket推送管理器
│   └── crypto_utils.py   # 加密工具
├── core/
│   └── style_registry.py # 风格注册表
├── models/
│   ├── api_models.py     # API数据模型
│   └── user_models.py    # 用户数据模型
├── workflows/
│   └── built_in/         # 内置工作流
├── config.py             # 配置管理
└── main.py              # 应用入口
```

## 实时进度跟踪

### 进度处理优化
- **精确进度映射**: 直接使用ComfyUI报告的真实进度，不添加人工偏移
- **多步骤节点过滤**: 只显示主要生成节点（采样）的进度，过滤单步预处理节点
- **平滑进度体验**: 避免进度跳跃，确保0%→100%的连续进度显示

### WebSocket消息格式
```json
{
  "type": "task_update",
  "request_id": "req123",
  "data": {
    "status": "processing",
    "progress": 45.6,
    "message": "生成进度: 12/25 (45.6%) - 节点: 73",
    "stage": "transform",
    "request_id": "req123",
    "timestamp": 1752982316.123,
    "result": {
      "files": {
        "input": "http://host:port/uploads/input.jpg",
        "output": ["http://host:port/view?filename=output.png"]
      }
    }
  }
}
```

## WebSocket连接架构

### 一对一连接模式
支持服务级别的WebSocket连接，如 `web_image_transform_service`，实现高效的消息路由：

```
多个前端用户 ←→ web_image_transform ←→ comfyui_workflow_server
(多对一)                    (一对一，基于user_id精确推送)
```

### 精确消息推送机制
```python
# 推送管理器根据任务中的user_id进行精确路由
task_user_id = update_data.get("user_id")  # 从任务数据中获取用户ID

# 查找目标连接
if "web_image_transform_service" in active_connections:
    # 推送到服务连接（一对一模式）
    await websocket.send_json(message)
```

### 消息路由流程
1. 任务状态更新时，从任务数据中提取 `user_id`
2. 查找活跃的WebSocket连接
3. 优先推送到服务级别连接（如 `web_image_transform_service`）
4. 服务端接收后根据 `user_id` 路由到对应前端用户
5. 实现精确推送，避免广播造成的资源浪费

## 更新日志

### v3.2.0 - 一对一连接架构版本
- **精确消息推送**: 基于任务中的user_id进行精确WebSocket推送，不再广播
- **一对一连接支持**: 支持服务级别的WebSocket连接（如web_image_transform_service）
- **消息路由优化**: 智能路由机制，优先推送到服务连接
- **多用户隔离**: 完全基于user_id的任务和消息隔离
- **连接管理优化**: 支持混合连接模式（直接用户连接+服务连接）

### v3.1.0 - 进度跟踪优化版本
- **实时进度跟踪**: WebSocket实时推送ComfyUI采样进度
- **进度精确映射**: 直接使用ComfyUI真实进度，移除30%基础偏移
- **多节点过滤**: 只显示主要生成节点进度，过滤预处理步骤
- **结果自动获取**: 任务完成时自动获取ComfyUI历史记录和文件
- **request_id追踪**: 端到端请求ID支持，便于调试和监控
- **心跳机制**: WebSocket连接保活，避免连接断开

### v3.0.0 - RPC版本
- 完全重构为RPC架构
- 单一端点设计（POST /rpc）
- 支持外部URL图片下载
- 标准化文件命名规范
- 多阶段任务生命周期
- 系统化错误代码体系
- 基础WebSocket状态推送

### v2.0.0 - 简化版本
- 移除复杂的认证系统
- 简化为基于user_id的资源隔离
- 优化微服务架构
- 专注核心业务功能

### v1.0.0 - 初始RESTful版本
- RESTful API设计
- 基础认证系统
- 用户文件管理 