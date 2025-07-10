# Web Image Transform

一个简化的Web应用，用于通过ComfyUI工作流服务器进行图像风格转换。

## 特性

- 🎨 多种预设图像风格转换
- 📤 支持拖拽上传图片
- ⚡ 实时任务进度推送
- 🔄 WebSocket实时通信
- 📱 响应式Web界面
- 🚀 简化的微服务架构

## 系统架构

```
┌─────────────────┐    HTTP/WebSocket    ┌──────────────────────┐
│  Web Frontend   │ ────────────────────► │  Web Image Transform │
│    (Browser)    │                      │      (FastAPI)       │
└─────────────────┘                      └──────────────────────┘
                                                     │
                                                     │ HTTP API
                                                     ▼
                                         ┌──────────────────────┐
                                         │ ComfyUI Workflow     │
                                         │     Server           │
                                         │   (Simplified)       │
                                         └──────────────────────┘
```

## 快速开始

### 1. 环境要求

- Python 3.8+
- 简化的ComfyUI Workflow Server 运行在 http://127.0.0.1:8000

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
# ComfyUI工作流服务器连接配置
COMFYUI_WORKFLOW_SERVER_URL=http://127.0.0.1:8000

# Web应用配置
APP_HOST=0.0.0.0
APP_PORT=8080
SESSION_SECRET_KEY=your-random-secret-key-here

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
GET /api/v1/styles
```

### 上传并转换图片
```http
POST /api/v1/transform
Content-Type: multipart/form-data

{
  "style_id": "anime_style",
  "file": <图片文件>
}
```

### WebSocket实时通信
```
ws://localhost:8080/api/v1/ws/{client_id}
```

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `COMFYUI_WORKFLOW_SERVER_URL` | ComfyUI工作流服务器地址 | `http://127.0.0.1:8000` |
| `APP_HOST` | Web应用监听地址 | `0.0.0.0` |
| `APP_PORT` | Web应用端口 | `8080` |
| `SESSION_SECRET_KEY` | 会话密钥（请更改） | - |
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
│   │   └── transform_api.py # API路由
│   ├── client/
│   │   └── comfyui_client.py # 简化的客户端
│   ├── services/
│   │   └── transform_service.py # 业务逻辑
│   └── static/
│       └── js/
│           └── app.js       # 前端JavaScript
├── templates/
│   └── index.html          # 主页模板
├── requirements.txt        # Python依赖
├── env.example            # 环境配置模板
└── README.md              # 项目文档
```

## 开发说明

### 会话管理
- 每个浏览器会话自动分配唯一的 `session_id`
- 使用 `session_id` 作为 `user_id` 与后端服务通信
- 确保不同用户的文件和任务隔离

### WebSocket通信
- 客户端连接: `/api/v1/ws/{client_id}`
- 服务器推送任务状态更新
- 支持断线自动重连

### 任务流程
1. 用户上传图片并选择风格
2. 前端调用 `/api/v1/transform` API
3. 服务器转发请求到ComfyUI Workflow Server
4. 通过WebSocket实时推送任务进度
5. 任务完成后显示结果

## 故障排除

### 连接问题
- 确保ComfyUI Workflow Server正在运行
- 检查服务器地址配置是否正确
- 查看应用日志获取详细错误信息

### WebSocket问题
- 检查防火墙设置
- 确认浏览器支持WebSocket
- 查看浏览器控制台错误信息

## 版本历史

- **v2.0.0** - 简化架构，移除复杂认证系统
- **v1.0.0** - 初始版本，包含完整认证功能

## 许可证

MIT License 