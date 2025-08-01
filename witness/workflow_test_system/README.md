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

## 系统架构

```
┌─────────────────┐    HTTP/WebSocket    ┌─────────────────┐    RPC/WebSocket    ┌───────────────────┐
│   前端浏览器      │ ────────────────────→ │   测试系统API    │ ────────────────────→ │ ComfyUI工作流服务器 │
│   (Browser)     │                     │   (FastAPI)      │                     │   (RPC Protocol)    │
└─────────────────┘                     └─────────────────┘                     └───────────────────┘
      │                                          │                                          │
      │                 WebSocket消息路由        │        WebSocket状态同步              │
      └──────────────────────────────────────────┴──────────────────────────────────────┘
```

### 组件说明

- **前端API层** (FastAPI): 提供RESTful API和WebSocket服务
- **RPC客户端**: 负责与ComfyUI工作流服务器的RPC通信
- **WebSocket管理器**: 维护与ComfyUI服务器的单一WebSocket连接
- **会话管理器**: 管理多个前端会话和消息分发
- **前端界面**: 提供用户友好的Web界面进行工作流测试

## 项目目录结构

```
workflow_test_system/
├── backend/                     # 后端服务
│   ├── app/
│   │   ├── main.py             # FastAPI主应用
│   │   ├── config.py           # 配置管理
│   │   ├── models/             # 数据模型
│   │   │   ├── requests.py     # 请求响应模型
│   │   │   └── tasks.py        # 任务状态模型
│   │   ├── services/           # 业务服务
│   │   │   ├── rpc_client.py   # RPC客户端
│   │   │   ├── websocket_manager.py  # WebSocket管理
│   │   │   └── session_manager.py    # 会话管理
│   │   └── routers/            # API路由
│   │       ├── workflow.py     # 工作流API
│   │       ├── files.py        # 文件管理API
│   │       └── system.py       # 系统管理API
│   ├── requirements.txt        # Python依赖
│   └── run.py                  # 启动脚本
├── frontend/                   # 前端界面
│   ├── index.html             # 主页面
│   ├── css/style.css          # 样式文件
│   └── js/app.js              # JavaScript主逻辑
└── README.md                  # 说明文档
```

## 安装和部署

### 前置要求

- Python 3.8+
- ComfyUI工作流服务器 (默认运行在 http://localhost:8000)
- 现代化浏览器 (支持WebSocket)

### 安装步骤

1. **克隆项目到本地**
   ```bash
   cd /mnt/d/workspace/ComfyUI/witness/workflow_test_system
   ```

2. **安装后端依赖**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **配置环境变量** (可选)
   ```bash
   export COMFYUI_WORKFLOW_SERVER_URL=http://localhost:8000
   export TEST_SYSTEM_HOST=0.0.0.0
   export TEST_SYSTEM_PORT=8001
   export LOG_LEVEL=INFO
   ```

4. **启动后端服务**
   ```bash
   python run.py
   ```

5. **访问前端界面**
   
   直接在浏览器中打开:
   ```bash
   # 或使用简单HTTP服务器
   cd ../frontend
   python -m http.server 8080
   
   # 然后访问 http://localhost:8080
   ```

### Docker部署 (可选)

创建 `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY frontend/ ./static/

CMD ["python", "run.py"]
```

构建和运行:
```bash
docker build -t workflow-test-system .
docker run -p 8001:8001 -e COMFYUI_WORKFLOW_SERVER_URL=http://host.docker.internal:8000 workflow-test-system
```

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

### 4. 文件管理

- **输出文件**: 查看ComfyUI服务器生成的文件
- **文件信息**: 获取文件大小和创建时间信息
- **文件下载**: 直接从ComfyUI服务器下载文件

## 快捷键操作

- `Ctrl + Enter`: 执行工作流
- `Ctrl + K`: 清空日志
- `F5`: 刷新工作流列表

## 完整API文档

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

## 故障排除指南

### 常见问题

1. **无法连接ComfyUI服务器**
   - 确保ComfyUI工作流服务器正在运行在 `http://localhost:8000`
   - 检查RPC端点 `/rpc` 是否可访问
   - 验证防火墙设置

2. **WebSocket连接失败**
   - 确保WebSocket端点 `/ws/workflow_test_system` 正常运行
   - 检查网络代理设置对WebSocket连接的影响
   - 查看浏览器开发者工具中的网络错误

3. **任务状态更新延迟**
   - 检查WebSocket连接状态
   - 验证request_id是否正确对应到会话
   - 查看后端日志中的错误信息

4. **工作流列表为空**
   - 检查ComfyUI服务器中的配置工作流
   - 调用 `workflow.list` RPC方法测试连接
   - 查看后端日志中的RPC通信错误

### 日志管理

后端配置说明:
- 所有请求和响应都会记录到后端日志
- 前端操作会显示在浏览器控制台中

日志级别设置:
- `INFO`: 正常运行信息
- `WARNING`: 警告信息和连接重试
- `ERROR`: 错误信息和异常情况
- `DEBUG`: 详细调试信息

## 性能优化建议

1. **连接池管理**
   - 生产环境中启用HTTPS和WSS
   - 配置适当的CORS策略
   - 限制并发连接数量

2. **会话管理**
   - 会话自动过期时间设置为30分钟
   - 会话数据限制为100条记录
   - 定期清理过期会话

3. **错误处理**
   - 网络错误自动重连
   - 异常情况日志记录
   - 用户友好的错误信息显示

## 安全考虑

1. **连接安全**
   - 生产环境使用HTTPS和WSS
   - HTTP连接池超时设置
   - API接口访问控制

2. **会话安全**
   - 会话ID随机生成和验证
   - 会话数据隔离保护
   - 恶意请求检测

3. **数据安全**
   - 输入参数验证和清理
   - 文件访问权限控制
   - 敏感信息过滤

## 开发扩展指南

### 添加新功能

1. **添加新的RPC方法**
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

2. **扩展WebSocket消息处理**
   ```python
   # 在 session_manager.py 中添加消息处理
   async def handle_websocket_message(self, session_id: str, message: Dict[str, Any]):
       message_type = message.get("type")
       if message_type == "custom_message":
           # 处理自定义消息
           await self.handle_custom_message(session_id, message)
   ```

3. **前端添加新功能**
   ```javascript
   // 在 app.js 中添加处理逻辑
   handleWebSocketMessage(message) {
       switch (message.type) {
           case 'custom_message':
               this.handleCustomMessage(message);
               break;
           // 其他消息处理...
       }
   }
   ```

### 测试

1. **后端测试**
   ```bash
   # 单元测试
   python -m pytest tests/
   
   # 集成测试
   python -m pytest tests/integration/
   ```

2. **前端测试**
   ```bash
   # 在浏览器开发者工具中
   # 测试WebSocket连接
   # 查看网络请求和响应
   ```

## 系统监控

### 监控指标

1. **实时监控**
   - WebSocket连接状态
   - 活跃会话数量
   - 当前执行任务数
   - 输出文件统计

2. **警告通知**
   - ComfyUI服务器连接中断
   - 会话数量超过限制
   - 任务执行失败率高
   - 磁盘空间不足

### 性能指标

1. **系统性能**
   - 平均响应时间监控
   - 内存使用情况跟踪
   - 系统负载统计

2. **优化建议**
   - 定期清理历史数据
   - 优化数据库查询性能
   - 监控资源使用情况

## 许可证

本项目采用 MIT 许可证，详细信息请查看 LICENSE 文件。

## 贡献指南

欢迎提交Issue和Pull Request来改进本项目。

---

**这是一个功能完整的ComfyUI工作流测试系统，为开发和测试工作流提供了强大的工具集合**