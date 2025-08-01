# ComfyUI工作流测试系统

这是一个用于测试ComfyUI工作流服务器的完整系统，包含前端和后端组件，实现RPC工作流请求和WebSocket推送功能。

## 系统特性

- **单一WebSocket连接**: 后端与ComfyUI服务器保持一个WebSocket连接
- **智能消息路由**: 基于request_id将消息分发到对应的前端会话
- **完整的RPC集成**: 支持所有ComfyUI工作流RPC方法
- **现代化前端**: 响应式设计的Web界面，实时状态更新
- **实时WebSocket**: 即时的工作流执行状态推送
- **会话管理**: 支持多个前端客户端同时连接
- **智能重连**: 网络中断后自动重连和错误恢复

## 快速启动

### 前置要求

- Python 3.8+
- ComfyUI工作流服务器 (默认运行在 http://localhost:8000)
- 现代化浏览器 (支持WebSocket)

### 安装和运行

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动系统**
   ```bash
   python run.py
   ```

3. **访问前端界面**
   
   打开浏览器访问: http://localhost:8001

### 环境变量配置

可以通过环境变量自定义配置：

```bash
export COMFYUI_WORKFLOW_SERVER_URL=http://localhost:8000
export TEST_SYSTEM_HOST=0.0.0.0
export TEST_SYSTEM_PORT=8001
export LOG_LEVEL=INFO
export DEBUG=False
```

## 项目结构

```
workflow_test_system/
├── app/                         # 应用核心
│   ├── main.py                 # FastAPI主应用
│   ├── config.py               # 配置管理
│   ├── models/                 # 数据模型
│   │   ├── requests.py         # 请求响应模型
│   │   └── tasks.py           # 任务状态模型
│   ├── services/               # 业务服务
│   │   ├── rpc_client.py       # RPC客户端
│   │   ├── websocket_manager.py # WebSocket管理
│   │   └── session_manager.py  # 会话管理
│   ├── routers/                # API路由
│   │   ├── workflow.py         # 工作流API
│   │   ├── files.py           # 文件管理API
│   │   └── system.py          # 系统管理API
│   └── static/                 # 静态文件
│       ├── index.html         # 主页面
│       ├── css/style.css      # 样式文件
│       └── js/app.js          # JavaScript逻辑
├── requirements.txt           # Python依赖
├── run.py                     # 启动脚本
└── README.md                  # 说明文档
```

## API文档

### 工作流管理

- `POST /api/workflow/execute` - 执行工作流
- `GET /api/workflow/status/{request_id}` - 获取任务状态
- `GET /api/workflow/result/{request_id}` - 获取任务结果
- `POST /api/workflow/cancel/{request_id}` - 取消任务
- `GET /api/workflow/list` - 列出工作流列表
- `GET /api/workflow/schema/{workflow_id}` - 获取工作流参数模式

### 文件管理

- `GET /api/files/output/{filename}` - 下载输出文件
- `GET /api/files/output/{filename}/info` - 获取文件信息
- `GET /api/files/output` - 列出输出文件

### 系统管理

- `GET /api/system/health` - 检查系统健康
- `GET /api/system/stats` - 获取系统统计
- `GET /api/system/sessions` - 获取会话列表

### WebSocket

- `ws://localhost:8001/ws/{session_id}` - WebSocket连接端点

## 使用指南

### 1. 系统初始化

启动后系统会自动:
- 生成会话ID
- 建立WebSocket连接
- 加载可用工作流
- 检查系统健康状态

### 2. 执行工作流

1. **选择工作流**: 从下拉列表中选择要执行的工作流
2. **配置参数**: 根据工作流要求填写参数
3. **执行任务**: 点击"执行工作流"按钮开始执行
4. **监控进度**: 观察实时进度条和状态更新
5. **查看结果**: 任务完成后查看生成的图像结果

### 3. 系统监控

- **状态面板**: 显示当前任务执行的详细进度
- **任务历史**: 查看所有已执行任务的状态
- **日志输出**: 实时查看系统运行日志
- **连接状态**: 监控与ComfyUI服务器的连接状态

## 开发扩展

### 添加新的RPC方法

```python
# 在 rpc_client.py 中添加方法
async def new_method(self, param1: str) -> Dict[str, Any]:
    return await self.call("new.method", {"param1": param1})

# 在对应路由中添加端点
@router.post("/new-endpoint")
async def new_endpoint(param1: str):
    async with rpc_client:
        result = await rpc_client.new_method(param1)
    return {"success": True, "data": result}
```

### 扩展WebSocket消息处理

```python
# 在 session_manager.py 中添加消息处理
async def handle_websocket_message(self, session_id: str, message: Dict[str, Any]):
    message_type = message.get("type")
    if message_type == "custom_message":
        # 处理自定义消息
        await self.handle_custom_message(session_id, message)
```

## 故障排除

### 常见问题

1. **无法连接ComfyUI服务器**
   - 确保ComfyUI工作流服务器正在运行在配置的地址
   - 检查RPC端点 `/rpc` 是否可访问
   - 验证防火墙设置

2. **WebSocket连接失败**
   - 确保WebSocket端点正常运行
   - 检查网络代理设置
   - 查看浏览器开发者工具中的网络错误

3. **任务状态更新延迟**
   - 检查WebSocket连接状态
   - 验证request_id是否正确对应到会话
   - 查看后端日志中的错误信息

## 许可证

本项目采用 MIT 许可证。