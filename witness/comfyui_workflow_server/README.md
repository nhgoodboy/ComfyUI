# ComfyUI 工作流处理服务器

🚀 基于 FastAPI 和 JSON-RPC 2.0 协议的 ComfyUI 工作流微服务架构

## 📋 项目概述

ComfyUI 工作流处理服务器是一个企业级的微服务系统，专为 ComfyUI 工作流的远程调度和管理而设计。采用 RPC 风格的架构，提供统一的工作流执行接口，支持多种工作流类型和实时状态推送。

### 🌟 核心特性

- **🔗 RPC 架构**: 基于 JSON-RPC 2.0 协议的统一接口
- **⚡ 异步处理**: 全异步架构，支持高并发工作流处理
- **📡 实时推送**: WebSocket 实时状态更新和结果通知
- **🔧 工作流管理**: 灵活的工作流注册和参数映射系统
- **📁 文件管理**: 完整的文件上传、下载和访问管理
- **🐳 容器化**: 完整的 Docker 部署支持
- **📊 健康监控**: 内置健康检查和系统监控接口
- **🛡️ 生产就绪**: 企业级错误处理和日志管理

### 🏗️ 系统架构

```
┌─────────────────┐    JSON-RPC 2.0    ┌─────────────────┐
│   Web Client    │◄──────────────────►│  Workflow API   │
└─────────────────┘                    │    Server       │
                                       └─────────┬───────┘
┌─────────────────┐                              │
│   Mobile App    │◄─────────────────────────────┤
└─────────────────┘                              │
                                                 │
┌─────────────────┐    WebSocket Push   ┌───────▼───────┐
│  Real-time UI   │◄──────────────────►│  ComfyUI       │
└─────────────────┘                    │  Integration   │
                                       └─────────────────┘
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
DEBUG=false
```

#### 5. 启动服务

```bash
python start.py
```

### 🌐 验证安装

访问以下地址验证服务状态：

- **健康检查**: http://localhost:8000/health
- **API 概览**: http://localhost:8000/
- **WebSocket**: ws://localhost:8000/ws/your-client-id

## 📚 API 使用指南

### 🔌 JSON-RPC 2.0 接口

所有 API 请求都通过 POST 方法发送到 `/rpc` 端点：

```bash
curl -X POST http://localhost:8000/rpc \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"jsonrpc\": \"2.0\",
    \"method\": \"workflow.execute\",
    \"params\": {
      \"workflow_id\": \"anime_style_transform\",
      \"request_id\": \"req_123\",
      \"image_url\": \"https://example.com/image.jpg\"
    },
    \"id\": 1
  }'
```

### 🎯 核心 API 方法

#### 工作流管理

```javascript
// 执行工作流
{
  \"method\": \"workflow.execute\",
  \"params\": {
    \"workflow_id\": \"anime_style_transform\",
    \"request_id\": \"unique_request_id\",
    \"image_url\": \"https://example.com/input.jpg\",
    \"parameters\": {
      \"strength\": 0.8,
      \"style\": \"anime\"
    }
  }
}

// 获取工作流状态
{
  \"method\": \"workflow.get_status\",
  \"params\": {
    \"request_id\": \"unique_request_id\"
  }
}

// 获取结果
{
  \"method\": \"workflow.get_result\",
  \"params\": {
    \"request_id\": \"unique_request_id\"
  }
}

// 取消工作流
{
  \"method\": \"workflow.cancel\",
  \"params\": {
    \"request_id\": \"unique_request_id\"
  }
}
```

#### 文件管理

```javascript
// 获取输出图片
{
  \"method\": \"files.get_output_image\",
  \"params\": {
    \"filename\": \"output_image.png\"
  }
}

// 列出输出文件
{
  \"method\": \"files.list_output_images\",
  \"params\": {
    \"limit\": 10,
    \"offset\": 0
  }
}
```

#### 系统管理

```javascript
// 健康检查
{
  \"method\": \"system.health\",
  \"params\": {}
}

// 系统统计
{
  \"method\": \"system.get_stats\",
  \"params\": {}
}
```

### 📡 WebSocket 实时推送

连接 WebSocket 接收实时状态更新：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/your-request-id');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('状态更新:', data);
  
  // 处理不同类型的推送消息
  switch(data.type) {
    case 'workflow_status':
      // 工作流状态变化
      break;
    case 'workflow_result':
      // 工作流完成结果
      break;
    case 'workflow_error':
      // 工作流执行错误
      break;
  }
};
```

## 🔧 配置说明

### 📁 目录结构

```
comfyui_workflow_server/
├── app/                    # 应用核心代码
│   ├── core/              # 核心组件
│   │   ├── workflow_registry.py    # 工作流注册表
│   │   └── parameter_mapper.py     # 参数映射器
│   ├── models/            # 数据模型
│   ├── rpc/               # RPC 接口实现
│   │   ├── methods/       # RPC 方法实现
│   │   └── ...
│   ├── services/          # 业务服务
│   └── utils/            # 工具类
├── configs/               # 配置文件
│   ├── workflows.yaml     # 工作流配置
│   └── rpc_config.yaml   # RPC 配置
├── workflows/             # 工作流模板
├── logs/                  # 日志文件
├── uploads/               # 上传文件
├── outputs/               # 输出文件
├── .env                   # 环境配置
├── env.template          # 配置模板
├── Dockerfile            # Docker 配置
├── requirements.txt      # Python 依赖
├── main.py              # 主应用
├── start.py             # 启动脚本
└── README.md            # 项目文档
```

### ⚙️ 工作流配置

在 `configs/workflows.yaml` 中配置可用的工作流：

```yaml
workflows:
  anime_style_transform:
    name: \"动漫风格转换\"
    description: \"将真实图片转换为动漫风格\"
    workflow_file: \"anime_style_transform.json\"
    parameters:
      strength:
        type: \"float\"
        default: 0.8
        min: 0.1
        max: 1.0
      style:
        type: \"string\"
        default: \"anime\"
        options: [\"anime\", \"manga\", \"realistic\"]
```

### 🔧 高级配置

#### 性能调优

```bash
# .env 文件中的性能相关配置
WORKERS=4                    # 工作进程数
COMFYUI_TIMEOUT=300         # ComfyUI 超时时间
MAX_FILE_SIZE=10485760      # 最大文件大小 (10MB)
```

#### 日志配置

```bash
LOG_LEVEL=INFO              # 日志级别
LOG_FORMAT=json             # 日志格式
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
cat configs/workflows.yaml

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
   # 在 configs/workflows.yaml 中添加配置
   workflows:
     my_new_workflow:
       name: \"我的新工作流\"
       description: \"工作流描述\"
       workflow_file: \"my_new_workflow.json\"
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

- **工作进程数**: 设置为 CPU 核心数的 1-2 倍
- **文件大小**: 根据实际需求调整 `MAX_FILE_SIZE`
- **超时设置**: 根据工作流复杂度调整 `COMFYUI_TIMEOUT`
- **日志级别**: 生产环境使用 `INFO` 或 `WARNING`

### 📊 监控指标

系统提供以下监控指标：

- **工作流执行统计**: 成功/失败率、平均执行时间
- **文件存储统计**: 上传/输出文件数量和大小
- **系统资源**: 内存、CPU 使用情况
- **连接状态**: ComfyUI 连接健康状态

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