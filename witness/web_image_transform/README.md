# Web Image Transform (RPC Edition)

基于RPC架构的Web图像转换应用，与ComfyUI Workflow Server (RPC Edition)集成。采用一对一WebSocket连接架构，支持多用户隔离。

## 特性

- 🎨 多种预设图像风格转换
- 📤 支持拖拽上传图片
- 🔗 支持外部URL图片下载
- ⚡ 多阶段实时进度监控（下载→转换）
- 📊 精确进度跟踪，直接反映ComfyUI采样进度
- 🔄 WebSocket实时通信，支持心跳保活
- 📱 响应式Web界面，原图vs结果对比展示
- 🚀 RPC单一端点架构
- 📋 标准化文件命名，支持request_id追踪
- 🖼️ 智能结果展示，自动获取生成文件
- 👥 多用户支持，基于user_id的任务隔离
- 🔗 一对一WebSocket连接，高效消息路由

## 系统架构

```
多个前端用户 ←→ web_image_transform ←→ comfyui_workflow_server
(多对一)                    (一对一，基于user_id精确推送)

┌─────────────────┐    WebSocket      ┌──────────────────────┐
│  Web Frontend   │ ◄────────────────► │  Web Image Transform │
│   (用户A/B/C)    │    HTTP/Upload     │      (FastAPI)       │
└─────────────────┘                    └──────────────────────┘
                                                   │
                                                   │ 单一WebSocket连接
                                                   │ 单一RPC客户端
                                                   │ 基于user_id路由
                                                   ▼
                                       ┌──────────────────────┐
                                       │ ComfyUI Workflow     │
                                       │   Server (RPC)       │
                                       │                      │
                                       │ • 多用户任务隔离      │
                                       │ • 精确消息推送       │
                                       │ • 基于user_id路由    │
                                       └──────────────────────┘
```

## 快速开始

### 1. 环境要求

- Python 3.8+
- ComfyUI Workflow Server (RPC Edition) 运行在 http://127.0.0.1:8000

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境

复制环境配置文件：
```bash
cp env.example .env
```

编辑 `.env` 文件：
```env
# ComfyUI工作流服务器连接配置（RPC版本）
COMFYUI_WORKFLOW_SERVER_URL=http://127.0.0.1:8000

# Web应用配置
APP_HOST=0.0.0.0
APP_PORT=8080
PUBLIC_HOST=127.0.0.1
SESSION_SECRET_KEY=your-random-secret-key-here

# RPC客户端配置
RPC_TIMEOUT=60
RPC_MAX_RETRIES=3

# 其他配置...
```

### 4. 启动应用

```bash
python -m app.main
```

或使用uvicorn：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 5. 访问应用

打开浏览器访问: http://localhost:8080

## API接口

### 获取风格列表
```http
GET /api/styles
```

### 上传并转换图片
```http
POST /api/transform
Content-Type: multipart/form-data

{
  "style_id": "anime_style",
  "file": <图片文件>
}
```

### 获取任务状态
```http
GET /api/tasks/{request_id}
```

### 获取任务结果
```http
GET /api/tasks/{request_id}/result
```

### WebSocket实时通信
```
ws://localhost:8080/api/ws/{user_id}
```

## RPC集成说明

### 一对一连接架构
- web_image_transform 与 comfyui_workflow_server 之间保持单一WebSocket连接
- 使用服务级别标识符：`web_image_transform_service`
- 基于消息中的 `user_id` 进行精确路由和推送

### 文件处理流程
1. 前端上传图片文件
2. 后端保存文件并生成标准URL
3. 调用RPC `transform.create` 方法，传递实际的 `user_id`
4. RPC服务下载图片并进行转换
5. 通过单一WebSocket连接推送实时状态
6. 根据消息中的 `user_id` 路由到对应前端用户

### 标准化文件命名
- 输入文件：`{style_id}_{user_id}_{request_id}_input.{ext}`
- 输出文件：`{style_id}_{user_id}_{request_id}_output.{ext}`
- 支持多种图片格式：jpg, png, webp等

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `COMFYUI_WORKFLOW_SERVER_URL` | ComfyUI工作流服务器地址 | `http://127.0.0.1:8000` |
| `APP_HOST` | Web应用监听地址 | `0.0.0.0` |
| `APP_PORT` | Web应用端口 | `8080` |
| `PUBLIC_HOST` | 公开访问地址 | `127.0.0.1` |
| `SESSION_SECRET_KEY` | 会话密钥（请更改） | - |
| `RPC_TIMEOUT` | RPC调用超时时间 | `60` |
| `RPC_MAX_RETRIES` | RPC重试次数 | `3` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `DEBUG` | 调试模式 | `false` |

## 项目结构

```
web_image_transform/
├── app/
│   ├── __init__.py
│   ├── main.py              # 主应用文件
│   ├── config.py            # 配置管理
│   ├── api/
│   │   └── transform_api.py # API路由（RPC包装）
│   ├── client/
│   │   └── rpc_client.py    # RPC客户端
│   ├── services/
│   │   └── transform_service.py # 业务逻辑（RPC调用）
│   └── static/
│       └── js/
│           └── app.js       # 前端JavaScript（多阶段监控）
├── templates/
│   └── index.html          # 主页模板
├── requirements.txt        # Python依赖（含aiohttp等）
├── .env                   # 环境配置（RPC版本）
└── README.md              # 项目文档
```

## 开发说明

### 用户管理
- 每个浏览器会话自动分配唯一的 `user_id`
- 格式：`user-{timestamp}-{random_string}`
- 确保不同用户的文件和任务完全隔离

### WebSocket通信架构
- **前端连接**: `/api/ws/{user_id}` - 每个用户独立的WebSocket连接
- **后端连接**: 单一WebSocket连接到 `comfyui_workflow_server`
- **消息路由**: 基于消息中的 `user_id` 进行精确推送
- **实时更新**: 多阶段任务状态和进度推送
- **心跳保活**: 支持断线自动重连和连接保活
- **精确进度**: 直接反映ComfyUI采样进度，过滤无关步骤

### 任务流程（RPC版本）
1. 用户上传图片并选择风格
2. 前端调用 `/api/transform` API
3. 后端保存文件并生成标准URL
4. 调用RPC `transform.create` 方法
5. RPC服务下载图片并进行转换
6. 通过WebSocket实时推送任务进度
7. 任务完成后显示结果

### 多阶段监控与进度跟踪
- **下载阶段**: 显示图片下载进度（0-100%）
- **转换阶段**: 
  - 精确显示ComfyUI采样进度
  - 过滤预处理节点，只显示主要生成步骤
  - 实时更新进度条和步数信息
- **完成状态**: 
  - 自动显示原图vs转换结果对比
  - 提供下载链接和查看原图功能
  - 支持多种输出格式（PNG、JPG等）
- **错误处理**: 分类显示下载和转换错误，提供详细错误信息

### 前端用户体验优化
- **智能进度显示**: 平滑的0-100%进度条，无跳跃
- **原图预览保存**: 使用base64预览URL，确保原图正确显示
- **结果对比展示**: 左侧原图，右侧转换结果，直观对比
- **实时状态更新**: 清晰的阶段标识（下载→转换→完成）
- **文件版本管理**: JavaScript版本控制，避免浏览器缓存问题

## 故障排除

### 连接问题
- 确保ComfyUI Workflow Server (RPC Edition)正在运行
- 检查RPC服务器地址配置是否正确
- 查看应用日志获取详细RPC错误信息
- 验证RPC端点 `/rpc` 是否可访问

### WebSocket问题
- 检查防火墙设置
- 确认浏览器支持WebSocket
- 查看浏览器控制台WebSocket错误信息
- 验证WebSocket连接路径是否正确

### RPC调用问题
- 检查RPC请求格式是否符合JSON-RPC 2.0规范
- 验证方法名和参数是否正确
- 查看RPC错误代码（1xxx-3xxx）
- 确认超时和重试配置是否合理

### 文件处理问题
- 检查上传目录权限
- 验证文件大小限制
- 确认图片格式支持
- 查看标准化文件命名是否正确

## 版本历史

- **v2.2.0 (一对一连接架构版)** - 多用户支持和精确消息推送
  - **一对一WebSocket连接**: web_image_transform与comfyui_workflow_server之间保持单一连接
  - **多用户隔离**: 基于user_id的完全任务和消息隔离
  - **精确消息推送**: 根据消息中的user_id进行精确路由，不再广播
  - **用户标识统一**: 将client_id概念升级为user_id，实现真正的多用户架构
  - **服务级别连接**: 使用web_image_transform_service标识符连接后端
  - **消息路由优化**: 智能消息路由机制，确保每个用户只收到自己的任务更新
  - **连接管理优化**: ConnectionManager支持基于user_id的连接和任务管理

- **v2.1.0 (进度跟踪优化版)** - 精确进度跟踪和用户体验优化
  - 精确ComfyUI采样进度跟踪，移除人工偏移
  - 多步骤节点过滤，只显示主要生成进度
  - 原图vs结果对比展示，正确的原图预览
  - WebSocket心跳保活机制
  - request_id端到端追踪支持
  - 自动结果获取，ComfyUI历史记录解析
  - JavaScript版本控制，避免缓存问题
  - 平滑进度体验，0-100%连续显示

- **v2.0.0 (RPC Edition)** - 完全改造为RPC架构
  - 单一RPC端点集成
  - 多阶段任务监控（下载+转换）
  - 标准化文件命名规范
  - 基础WebSocket状态推送
  - 外部URL图片下载支持
  - 系统化错误处理

- **v1.5.0** - 简化架构，移除复杂认证系统
- **v1.0.0** - 初始版本，包含完整认证功能

## 许可证

MIT License 