# ComfyUI 工作流处理服务器

🚀 基于 JSON-RPC 2.0 协议的 ComfyUI 工作流微服务架构，提供统一的工作流执行和管理接口

## 📋 项目概述

ComfyUI 工作流处理服务器是一个企业级的微服务系统，专为 ComfyUI 工作流的远程调度和管理而设计。采用 JSON-RPC 2.0 协议，提供统一、标准化的工作流执行接口，支持任意类型的工作流处理和实时状态推送。

### 🌟 核心特性

- **🔗 标准RPC协议**: 基于 JSON-RPC 2.0 标准，提供统一的调用接口
- **⚡ 异步任务处理**: 支持长时间运行的工作流任务，异步结果获取
- **📡 实时状态推送**: WebSocket 连接提供任务进度和结果的实时通知
- **🎯 工作流管理**: 完整的工作流生命周期管理（执行、监控、取消）
- **📁 文件访问服务**: RPC方式的文件上传、下载和信息查询
- **🔧 参数验证**: 智能的工作流参数验证和映射系统
- **🐳 容器化部署**: 完整的 Docker 部署支持和配置
- **📊 系统监控**: 内置健康检查、统计信息和性能监控
- **🛡️ 企业级特性**: 完善的错误处理、日志记录和生产环境支持

### 🏗️ 系统架构

```
┌─────────────────┐   JSON-RPC 2.0     ┌─────────────────┐   WebSocket Push  ┌─────────────────┐
│   Web Client    │ ──────────────────► │  RPC API Server │ ◄──────────────── │ 实时状态推送    │
└─────────────────┘    /rpc 端点       └─────────┬───────┘      状态更新      └─────────────────┘
                                                 │
┌─────────────────┐                             │                     ┌─────────────────┐
│   Mobile App    │ ────────────────────────────┤                     │  工作流注册表   │
└─────────────────┘                             │                     │ (workflows.yaml)│
                                                 ▼                     └─────────────────┘
┌─────────────────┐                    ┌─────────────────┐                     ┌─────────────────┐
│ Test System UI  │                    │   ComfyUI       │                     │   文件存储      │
└─────────────────┘                    │   工作流引擎    │                     │ (uploads/outputs)│
                                       └─────────────────┘                     └─────────────────┘
```

## 🎯 适用场景

- **🎨 AI 图像生成服务**: 提供稳定的图像生成 API
- **🖼️ 批量图像处理**: 支持大规模图像转换和处理
- **🔄 工作流自动化**: 自动化复杂的 AI 处理流程
- **☁️ 云端 AI 服务**: 构建可扩展的云端 AI 处理平台
- **🏢 企业 AI 集成**: 为企业应用提供 AI 处理能力

## 🚀 快速开始

### 📋 环境要求

- **Python**: 3.11+
- **ComfyUI**: 运行中的 ComfyUI 实例
- **系统**: Linux/macOS/Windows
- **内存**: 最少 2GB，推荐 4GB+
- **存储**: 最少 5GB 可用空间

### 🔧 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd comfyui_workflow_server
```

#### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\\Scripts\\activate     # Windows
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置环境

```bash
# 复制配置模板
cp env.template .env

# 编辑配置文件
vim .env  # 或使用其他编辑器
```

**关键配置项**:
```bash
# ComfyUI 服务器地址（必须配置）
COMFYUI_HOST=localhost
COMFYUI_PORT=8188

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

#### 5. 启动服务

```bash
# 推荐使用 start.py（支持命令行参数和环境配置）
python start.py

# 或者使用默认配置运行
python start.py --host 0.0.0.0 --port 8000

# 使用自定义配置文件
python start.py --config .env.production

# 传统方式（不推荐，缺少配置验证）
python main.py
```

### 🌐 验证安装

访问以下地址验证服务状态：

- **服务概览**: http://localhost:8000/
- **健康检查**: http://localhost:8000/health  
- **RPC 端点**: http://localhost:8000/rpc
- **WebSocket**: ws://localhost:8000/ws/{client_id}
- **API 文档**: http://localhost:8000/docs（仅调试模式）

## 📚 API 使用指南

> **📖 详细API文档**: 完整的RPC API接入指南请查看 [`docs/RPC_API接入指南.md`](docs/RPC_API接入指南.md)，包含：
> - 完整的API方法列表和参数说明
> - WebSocket实时推送详细说明  
> - 错误处理和故障排除
> - 多语言SDK和代码示例
> - 性能优化建议

### 🔌 JSON-RPC 2.0 接口

所有 API 请求都通过 POST 方法发送到 `/rpc` 端点。请求必须符合 JSON-RPC 2.0 标准：

```bash
curl -X POST http://localhost:8000/rpc \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"jsonrpc\": \"2.0\",
    \"method\": \"workflow.execute\",
    \"params\": {
      \"request_id\": \"req_123456789\",
      \"workflow_id\": \"anime_style_transform\",
      \"params\": {
        \"input_image\": \"https://example.com/image.jpg\",
        \"prompt\": \"anime style, beautiful\",
        \"guidance\": 12
      }
    },
    \"id\": \"execute_001\"
  }'
```

### 🎯 核心 API 方法

#### 工作流管理

```javascript
// 获取可用工作流列表
{
  "jsonrpc": "2.0",
  "method": "workflow.list",
  "params": {},
  "id": "list_001"
}

// 获取工作流参数模式
{
  "jsonrpc": "2.0",
  "method": "workflow.get_schema", 
  "params": {
    "workflow_id": "clay_style_transform"
  },
  "id": "schema_001"
}

// 执行工作流
{
  "jsonrpc": "2.0",
  "method": "workflow.execute",
  "params": {
    "request_id": "req_123456789",
    "workflow_id": "clay_style_transform",
    "params": {
      "input_image": "https://example.com/input.jpg",
      "prompt": "Clay Style, lovely, cute",
      "guidance": 12
    }
  },
  "id": "execute_001"
}

// 获取工作流状态
{
  "jsonrpc": "2.0",
  "method": "workflow.get_status",
  "params": {
    "request_id": "req_123456789"
  },
  "id": "status_001"
}

// 获取执行结果
{
  "jsonrpc": "2.0",
  "method": "workflow.get_result",
  "params": {
    "request_id": "req_123456789"
  },
  "id": "result_001"
}

// 取消工作流
{
  "jsonrpc": "2.0",
  "method": "workflow.cancel",
  "params": {
    "request_id": "req_123456789"
  },
  "id": "cancel_001"
}

// 搜索工作流
{
  "jsonrpc": "2.0",
  "method": "workflow.search",
  "params": {
    "query": "anime style"
  },
  "id": "search_001"
}
```

#### 文件管理

```javascript
// 列出输出图片
{
  "jsonrpc": "2.0",
  "method": "files.list_output_images",
  "params": {
    "limit": 20,
    "offset": 0,
    "pattern": "*clay*"
  },
  "id": "list_files_001"
}

// 获取输出图片信息
{
  "jsonrpc": "2.0",
  "method": "files.get_output_image_info",
  "params": {
    "filename": "clay_style_req123_output.png"
  },
  "id": "file_info_001"
}

// 获取输出图片（base64编码）
{
  "jsonrpc": "2.0",
  "method": "files.get_output_image",
  "params": {
    "filename": "clay_style_req123_output.png"
  },
  "id": "get_image_001"
}
```

#### 系统管理

```javascript
// 健康检查
{
  "jsonrpc": "2.0",
  "method": "system.health",
  "params": {},
  "id": "health_001"
}

// 系统统计信息
{
  "jsonrpc": "2.0",
  "method": "system.get_stats",
  "params": {},
  "id": "stats_001"
}

// 解析文件名
{
  "jsonrpc": "2.0",
  "method": "system.parse_filename",
  "params": {
    "filename": "clay_style_req123_output.png"
  },
  "id": "parse_001"
}
```

### 📡 WebSocket 实时推送

连接 WebSocket 接收实时状态更新。支持按 `request_id` 或服务级别的连接：

```javascript
// 连接特定请求的状态推送
const ws = new WebSocket('ws://localhost:8000/ws/req_123456789');

// 或连接服务级别的推送（用于测试系统）
const wsService = new WebSocket('ws://localhost:8000/ws/workflow_test_system');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('状态更新:', data);
  
  // 处理不同类型的推送消息
  switch(data.type) {
    case 'workflow_status':
      // 工作流状态变化：pending, running, completed, failed, cancelled
      console.log('状态:', data.status, '进度:', data.progress);
      break;
    case 'workflow_result':
      // 工作流完成结果
      console.log('结果:', data.result);
      break;
    case 'workflow_error':
      // 工作流执行错误
      console.error('错误:', data.error);
      break;
  }
};

// 心跳保持连接
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send('ping');
  }
}, 30000);
```

## 🔧 配置说明

### 📁 目录结构

```
comfyui_workflow_server/
├── app/                    # 应用核心代码
│   ├── core/              # 核心组件
│   │   ├── workflow_registry.py    # 工作流注册表和管理
│   │   └── parameter_mapper.py     # 参数映射和验证
│   ├── models/            # 数据模型和API模型
│   ├── rpc/               # JSON-RPC 2.0 接口实现
│   │   ├── methods/       # RPC 方法实现
│   │   │   ├── workflow.py   # 工作流管理方法
│   │   │   ├── files.py      # 文件访问方法
│   │   │   └── system.py     # 系统管理方法
│   │   ├── router.py         # RPC 路由器
│   │   ├── handler.py        # RPC 请求处理器
│   │   ├── validator.py      # 参数验证器
│   │   ├── formatter.py      # 响应格式化器
│   │   └── exceptions.py     # RPC 异常定义
│   ├── services/          # 业务服务层
│   │   ├── comfyui_service.py      # ComfyUI 集成服务
│   │   ├── workflow_task_service.py # 工作流任务管理
│   │   └── download_service.py     # 文件下载服务
│   └── utils/            # 工具类和辅助函数
│       ├── websocket_push.py       # WebSocket 推送管理
│       └── file_naming.py          # 文件命名工具
├── comfyui_client/        # ComfyUI 客户端封装
│   ├── client.py         # 主客户端类
│   ├── endpoints/        # API 端点实现
│   └── websocket.py      # WebSocket 连接管理
├── workflows/             # 工作流模板和配置
│   ├── workflows.yaml     # 工作流配置文件
│   ├── anime_style_transform.json  # 动漫风格转换模板
│   ├── clay_style_transform.json   # 粘土风格转换模板
│   └── img2img_api.json           # 图像转换API模板
├── docs/                  # 项目文档
│   └── RPC_API接入指南.md  # RPC API 接入文档
├── logs/                  # 日志文件目录
├── uploads/               # 文件上传目录
├── outputs/               # 输出文件目录
├── .env                   # 环境配置文件
├── Dockerfile            # Docker 配置
├── requirements.txt      # Python 依赖列表
├── main.py              # FastAPI 应用主文件
├── start.py             # 启动脚本（推荐使用）
└── README.md            # 项目说明文档
```

### ⚙️ 工作流配置

在 `workflows/workflows.yaml` 中配置可用的工作流：

```yaml
workflows:
  clay_style_transform:
    name: "粘土风格转换"
    description: "将图片转换为可爱的粘土风格"
    template_file: "clay_style_transform.json"
    estimated_time: 45
    version: "1.0"
    tags: ["style", "clay", "3d"]
    parameters:
      input_image:
        type: "string"
        description: "输入图片URL或base64编码"
        required: true
      prompt:
        type: "string"
        description: "风格描述文本"
        default: "Clay Style, lovely, cute"
        required: true
      guidance:
        type: "float"
        description: "引导强度"
        default: 12.0
        min: 5.0
        max: 20.0
      
  anime_style_transform:
    name: "动漫风格转换"
    description: "将真实图片转换为动漫风格"
    template_file: "anime_style_transform.json"
    estimated_time: 30
    version: "1.0"
    tags: ["style", "anime", "2d"]
    parameters:
      input_image:
        type: "string"
        description: "输入图片URL"
        required: true
      prompt:
        type: "string"
        description: "风格描述"
        default: "anime style, beautiful"
        required: false
      guidance:
        type: "float"
        default: 10.0
        min: 5.0
        max: 15.0
```

### 🔧 高级配置

#### 性能调优配置

```bash
# .env 文件中的关键配置
# 服务器配置
HOST=0.0.0.0                   # 监听地址
PORT=8000                      # 监听端口
WORKERS=4                      # 工作进程数（建议为CPU核心数）
DEBUG=false                    # 生产环境关闭调试模式

# ComfyUI 连接配置
COMFYUI_HOST=localhost         # ComfyUI 服务器地址
COMFYUI_PORT=8188             # ComfyUI 服务器端口
COMFYUI_TIMEOUT=300           # ComfyUI 超时时间（秒）

# 工作流任务配置
MAX_CONCURRENT_WORKFLOWS=3     # 最大并发工作流数
WORKFLOW_TASK_TIMEOUT=300      # 工作流任务超时时间
WORKFLOW_STATUS_CHECK_INTERVAL=2  # 状态检查间隔

# WebSocket 配置
WEBSOCKET_CONNECTION_TIMEOUT=30    # WebSocket 连接超时
WEBSOCKET_PING_INTERVAL=30         # 心跳间隔
WEBSOCKET_MAX_CONNECTIONS=100      # 最大连接数

# 文件处理配置
MAX_FILE_SIZE=10485760         # 最大文件大小 (10MB)
ENABLE_AUTO_CLEANUP=true       # 启用自动文件清理
TEMP_FILE_RETENTION_HOURS=2    # 临时文件保留时间
OUTPUT_FILE_RETENTION_DAYS=30  # 输出文件保留时间

# 监控配置
ENABLE_DETAILED_STATS=true     # 启用详细统计
HEALTH_CHECK_INTERVAL=30       # 健康检查间隔
```

#### 日志配置

```bash
# 日志级别和格式
LOG_LEVEL=INFO                 # 日志级别：DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                # 日志格式：json 或 text
LOG_FILE_MAX_SIZE=10485760     # 日志文件最大大小
LOG_FILE_BACKUP_COUNT=5        # 日志文件保留数量

# 生产环境建议
ENVIRONMENT=production
CORS_ORIGINS=https://your-domain.com,https://admin.your-domain.com
```

## 🐳 Docker 部署

### 🏗️ 构建镜像

```bash
docker build -t comfyui-workflow-server .
```

### 🚀 运行容器

```bash
docker run -d \\
  --name comfyui-workflow \\
  -p 8000:8000 \\
  -v $(pwd)/outputs:/app/outputs \\
  -v $(pwd)/uploads:/app/uploads \\
  -v $(pwd)/logs:/app/logs \\
  -e COMFYUI_HOST=host.docker.internal \\
  comfyui-workflow-server
```

### 📝 Docker Compose

```yaml
version: '3.8'
services:
  comfyui-workflow:
    build: .
    ports:
      - \"8000:8000\"
    volumes:
      - ./outputs:/app/outputs
      - ./uploads:/app/uploads
      - ./logs:/app/logs
      - ./configs:/app/configs
    environment:
      - COMFYUI_HOST=comfyui
      - ENVIRONMENT=production
      - DEBUG=false
    depends_on:
      - comfyui
      
  comfyui:
    image: comfyui/comfyui:latest
    ports:
      - \"8188:8188\"
    volumes:
      - comfyui_models:/app/models
```

## 🔍 故障排除

### 🐛 常见问题

#### 1. ComfyUI 连接失败

**症状**: API 返回 ComfyUI 连接错误

**解决方案**:
```bash
# 检查 ComfyUI 是否运行
curl http://localhost:8188/system_stats

# 检查配置
grep COMFYUI_HOST .env

# 测试网络连接
telnet localhost 8188
```

#### 2. 工作流执行失败

**症状**: 工作流状态显示失败

**解决方案**:
```bash
# 检查工作流配置
cat workflows/workflows.yaml

# 检查 ComfyUI 日志
docker logs comfyui-container

# 检查服务器日志
tail -f logs/app.log
```

#### 3. 文件上传问题

**症状**: 文件上传失败或找不到文件

**解决方案**:
```bash
# 检查目录权限
ls -la uploads/ outputs/

# 检查磁盘空间
df -h

# 检查文件大小限制
grep MAX_FILE_SIZE .env
```

### 📋 健康检查

```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细系统状态
curl -X POST http://localhost:8000/rpc \\
  -H \"Content-Type: application/json\" \\
  -d '{\"jsonrpc\":\"2.0\",\"method\":\"system.health\",\"id\":1}'

# 系统统计信息
curl -X POST http://localhost:8000/rpc \\
  -H \"Content-Type: application/json\" \\
  -d '{\"jsonrpc\":\"2.0\",\"method\":\"system.get_stats\",\"id\":1}'
```

## 🤝 开发指南

### 🛠️ 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 启用调试模式
echo \"DEBUG=true\" >> .env

# 运行开发服务器
python start.py
```

### 🧪 添加新工作流

1. **创建工作流 JSON 文件**：
   ```bash
   # 在 workflows/ 目录下创建新的工作流文件
   cp workflows/anime_style_transform.json workflows/my_new_workflow.json
   ```

2. **配置工作流参数**：
   ```yaml
   # 在 workflows/workflows.yaml 中添加配置
   workflows:
     my_new_workflow:
       name: \"我的新工作流\"
       description: \"工作流描述\"
       template_file: \"my_new_workflow.json\"
       parameters:
         # 定义参数
   ```

3. **测试工作流**：
   ```bash
   curl -X POST http://localhost:8000/rpc \\
     -H \"Content-Type: application/json\" \\
     -d '{\"jsonrpc\":\"2.0\",\"method\":\"workflow.execute\",\"params\":{\"workflow_id\":\"my_new_workflow\"},\"id\":1}'
   ```

### 🔧 扩展 RPC 方法

1. **创建新的 RPC 方法**：
   ```python
   # 在 app/rpc/methods/ 下创建新文件
   from ..router import rpc_method
   
   @rpc_method(\"my_module.my_method\")
   async def my_custom_method(params, request):
       # 实现逻辑
       return {\"result\": \"success\"}
   ```

2. **注册方法**：
   ```python
   # 在 app/rpc/methods/__init__.py 中导入
   from .my_module import *
   ```

## 📈 性能优化

### ⚡ 性能建议

- **工作进程数**: 设置为 CPU 核心数，避免过多进程竞争
- **并发任务数**: 根据GPU内存和ComfyUI性能调整 `MAX_CONCURRENT_WORKFLOWS`
- **文件大小限制**: 根据实际需求和网络条件调整 `MAX_FILE_SIZE`
- **超时设置**: 根据工作流复杂度合理设置 `COMFYUI_TIMEOUT`
- **日志级别**: 生产环境使用 `INFO` 或 `WARNING`，避免 `DEBUG`

### 📊 监控指标

系统提供以下关键监控指标：

- **工作流执行统计**: 成功率、失败率、平均执行时间
- **文件存储统计**: 输入文件数量、输出文件数量和总大小  
- **系统资源监控**: 服务运行时间、内存使用情况
- **ComfyUI连接状态**: 实时健康检查和连接稳定性
- **WebSocket连接数**: 当前活跃连接和历史峰值

> **💡 提示**: 使用 `system.get_stats` API 获取详细的系统统计信息，便于性能分析和故障诊断。

## 🔒 安全建议

### 🛡️ 生产环境安全

1. **环境配置**:
   ```bash
   DEBUG=false
   ENVIRONMENT=production
   ```

2. **网络安全**:
   - 使用防火墙限制访问端口
   - 配置 HTTPS (建议使用反向代理)
   - 限制 CORS 源为具体域名

3. **文件安全**:
   - 定期清理临时文件
   - 设置合理的文件大小限制
   - 验证上传文件类型

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 📝 贡献流程

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📞 支持

- **问题反馈**: [GitHub Issues](https://github.com/your-repo/issues)
- **文档**: 查看项目 Wiki
- **讨论**: [GitHub Discussions](https://github.com/your-repo/discussions)

---

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！**