# ComfyUI 工作流服务器

基于 FastAPI 和 RPC 架构构建的高性能、安全的 ComfyUI 工作流微服务。提供统一的图像风格转换和工作流执行能力，具备企业级安全特性。

## 🚀 功能特性

- **RPC 架构**: 基于 JSON-RPC 2.0 协议的高效客户端-服务器通信
- **工作流管理**: 动态工作流注册和执行系统
- **图像处理**: 使用 ComfyUI 后端的高级图像风格转换
- **企业级安全**: 5层安全防护架构，包含JWT、IP白名单和API密钥认证
- **实时更新**: WebSocket 支持实时任务状态监控
- **高性能**: 异步处理，支持可配置的并发限制
- **Docker 就绪**: 生产就绪的容器化部署，内置健康检查

## 📋 系统要求

- **Python**: 3.11+
- **ComfyUI**: 运行中的实例 (默认: localhost:8188)
- **系统内存**: 推荐 4GB+
- **存储空间**: 工作流和临时文件需要 10GB+

## 🛠️ 安装部署

### 快速开始

```bash
# 克隆仓库
git clone <repository-url>
cd comfyui_workflow_server

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
cp env.template .env
# 编辑 .env 文件配置

# 启动服务器
python main.py
```

### Docker 部署

```bash
# 构建镜像
docker build -t comfyui-workflow-server .

# 运行容器
docker run -d \
  --name comfyui-server \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/logs:/app/logs \
  comfyui-workflow-server
```

## ⚙️ 配置说明

### 环境变量

`.env` 文件中的关键配置选项:

```bash
# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=false

# ComfyUI 后端
COMFYUI_HOST=127.0.0.1
COMFYUI_PORT=8188

# 安全配置 (生产环境)
SECURITY_ENABLED=true
API_SECRET_KEY=your-64-char-secret-key
JWT_SECRET_KEY=your-64-char-jwt-key
ALLOWED_IPS=127.0.0.1,::1,192.168.0.0/24

# 文件存储
UPLOADS_DIR=uploads
OUTPUTS_DIR=outputs
MAX_FILE_SIZE=10485760  # 10MB
```

### 配置文件

- `configs/rpc_config.yaml` - RPC 服务设置
- `configs/workflows.yaml` - 工作流定义
- `workflows/` - ComfyUI 工作流 JSON 文件

## 🔌 API 使用指南

### RPC 端点

**URL**: `POST /rpc`

**Content-Type**: `application/json`

### 可用方法

#### 工作流执行

```bash
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "workflow.execute",
    "params": {
      "request_id": "req_123",
      "workflow_id": "clay_style_transform",
      "params": {
        "input_image": "http://example.com/image.jpg",
        "prompt": "粘土风格，可爱",
        "guidance": 12
      }
    },
    "id": 1
  }'
```

#### 系统信息

```bash
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "system.health",
    "params": {},
    "id": 1
  }'
```

#### 文件管理

```bash
# 列出输出文件
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "files.list_output_images",
    "params": {
      "request_id": "req_123"
    },
    "id": 1
  }'
```

### WebSocket 连接

连接实时更新:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/req_123');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('状态更新:', data);
};
```

## 🏗️ 系统架构

### 目录结构

```
comfyui_workflow_server/
├── app/                          # 应用核心
│   ├── core/                     # 核心业务逻辑
│   │   ├── workflow_registry.py  # 工作流管理
│   │   └── parameter_mapper.py   # 参数映射
│   ├── rpc/                      # RPC 实现
│   │   ├── methods/              # RPC 方法处理器
│   │   ├── handler.py            # 请求处理器
│   │   └── router.py             # 方法路由器
│   ├── services/                 # 业务服务
│   │   ├── comfyui_service.py    # ComfyUI 客户端
│   │   └── transform_task_service.py # 任务管理
│   └── utils/                    # 工具类
├── comfyui_client/               # ComfyUI 客户端库
├── configs/                      # 配置文件
├── workflows/                    # 工作流定义
├── main.py                       # 应用入口点
└── requirements.txt              # 依赖项
```

### 安全架构

1. **IP 白名单** - 网络级访问控制
2. **API 密钥认证** - 请求级安全
3. **请求签名验证** - 消息完整性
4. **速率限制** - DDoS 防护
5. **JWT 令牌验证** - 用户会话管理

## 🔧 开发指南

### 添加新工作流

1. 在 `workflows/` 目录中创建工作流 JSON 文件
2. 在 `configs/workflows.yaml` 中注册:

```yaml
workflows:
  my_custom_workflow:
    name: "我的自定义工作流"
    description: "自定义图像处理"
    file: "my_workflow.json"
    parameters:
      input_image:
        type: "string"
        required: true
      strength:
        type: "float"
        default: 0.8
```

### 创建 RPC 方法

```python
from app.rpc.router import rpc_method

@rpc_method("my_namespace.my_method")
async def my_custom_method(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """自定义 RPC 方法实现"""
    # 您的逻辑代码
    return {"status": "success"}
```

### 测试

```bash
# 运行测试
pytest

# 运行带覆盖率的测试
pytest --cov=app tests/
```

## 🐳 生产环境部署

### Docker Compose

```yaml
version: '3.8'
services:
  comfyui-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SECURITY_ENABLED=true
      - DEBUG=false
    volumes:
      - ./data/uploads:/app/uploads
      - ./data/outputs:/app/outputs
      - ./logs:/app/logs
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - comfyui-server
```

### 安全检查清单

- [ ] 更改所有默认密钥
- [ ] 设置 `DEBUG=false`
- [ ] 配置正确的 IP 白名单
- [ ] 生产环境中启用 HTTPS
- [ ] 设置日志监控
- [ ] 配置备份策略
- [ ] 启用速率限制
- [ ] 检查文件权限

## 📊 监控运维

### 健康检查

```bash
curl http://localhost:8000/health
```

### 监控端点

- `/` - 服务概览
- `/health` - 详细健康状态
- `/rpc` - 主 API 端点
- `/outputs` - 静态文件服务

### 日志记录

应用中配置了结构化的 JSON 格式日志:

```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "INFO",
  "message": "请求完成",
  "request_id": "req_123",
  "duration": 1.234
}
```

## 🛠️ 故障排除

### 常见问题

**ComfyUI 连接失败**
```bash
# 检查 ComfyUI 状态
curl http://localhost:8188/system_stats

# 验证配置
grep COMFYUI_ .env
```

**文件上传错误**
```bash
# 检查文件权限
ls -la uploads/ outputs/

# 验证文件大小限制
grep MAX_FILE_SIZE .env
```

**内存问题**
```bash
# 监控资源使用
docker stats comfyui-server

# 检查 ComfyUI 内存使用
curl http://localhost:8188/system_stats
```

### 调试模式

启用详细日志:

```bash
# 在 .env 中设置
DEBUG=true
LOG_LEVEL=DEBUG

# 重启服务
python main.py
```

## 📝 API 参考

### 响应格式

所有 RPC 响应都遵循 JSON-RPC 2.0 规范:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "status": "success",
    "data": {}
  },
  "id": 1
}
```

### 错误代码

| 代码 | 描述 |
|------|------|
| 1001 | 无效的 JSON 格式 |
| 1002 | 未找到方法 |
| 1003 | 无效参数 |
| 1004 | 内部服务器错误 |
| 2001 | ComfyUI 连接错误 |
| 2002 | 工作流执行失败 |

## 🤝 贡献指南

1. Fork 仓库
2. 创建功能分支
3. 进行修改
4. 如适用，添加测试
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

## 📞 技术支持

- **文档**: 请查看本 README 和代码内注释
- **问题反馈**: 在项目仓库中创建 issue
- **社区讨论**: 加入我们的开发讨论

---

**版本**: 2.0.0  
**最后更新**: 2024-01-01  
**维护团队**: ComfyUI 工作流服务器团队