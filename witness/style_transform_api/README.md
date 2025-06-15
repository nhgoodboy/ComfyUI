# 图像风格变换API服务

基于ComfyUI的图像风格变换API服务，专为移动端APP后端设计，支持多用户并发处理。

## 功能特性

- 🎨 **多种风格变换**：支持Clay、Anime、Realistic、Cartoon、Oil Painting等风格
- 👥 **多用户支持**：基于user_id的用户隔离和任务管理
- 🚀 **异步处理**：后台异步处理，支持高并发
- 📊 **实时进度**：WebSocket实时进度反馈
- 🔄 **批量处理**：支持批量图像处理
- 📈 **任务管理**：完整的任务状态跟踪和历史记录
- 🐳 **容器化部署**：Docker和Docker Compose支持

## 系统架构

```
移动端APP → APP后端系统 → 图像风格变换API → ComfyUI服务
```

本服务作为中间层，提供：
- RESTful API接口
- 任务队列管理
- 图像下载/上传
- 工作流自定义
- 结果返回

## 快速开始

### 1. 环境要求

- Python 3.11+
- ComfyUI服务运行在 `http://localhost:8188`
- Docker（可选）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
DEBUG=true
LOG_LEVEL=INFO
COMFYUI_BASE_URL=http://localhost:8188
HOST=0.0.0.0
PORT=8000
```

### 4. 启动服务

```bash
python -m app.main
```

或使用Docker：

```bash
docker-compose up -d
```

### 5. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口

### 单张图像变换

```http
POST /api/v1/transform
Content-Type: application/json

{
    "user_id": "user_12345",
    "image_url": "https://example.com/input.jpg",
    "style_type": "clay",
    "custom_prompt": "Clay Style, lovely, 3d, cute",
    "strength": 0.6
}
```

### 批量图像变换

```http
POST /api/v1/transform/batch
Content-Type: application/json

{
    "user_id": "user_12345",
    "image_urls": [
        "https://example.com/input1.jpg",
        "https://example.com/input2.jpg"
    ],
    "style_type": "anime",
    "strength": 0.7
}
```

### 查询任务状态

```http
GET /api/v1/task/{task_id}
```

### 获取用户任务列表

```http
GET /api/v1/user/{user_id}/tasks?limit=50
```

## 风格类型

| 风格类型 | 描述 | 预设提示词 |
|---------|------|-----------|
| clay | 粘土风格 | Clay Style, lovely, 3d, cute |
| anime | 动漫风格 | Anime Style, beautiful, detailed |
| realistic | 写实风格 | Realistic Style, high quality, detailed |
| cartoon | 卡通风格 | Cartoon Style, colorful, fun |
| oil_painting | 油画风格 | Oil Painting Style, artistic, classical |

## 工作流配置

系统使用 `app/workflows/style_change.json` 作为基础工作流模板。如果您有自定义的ComfyUI工作流，请：

1. 将工作流JSON文件放置在 `app/workflows/` 目录
2. 修改 `app/services/comfyui_service.py` 中的 `customize_workflow` 方法
3. 确保工作流包含必要的节点：LoadImage、CLIPTextEncode、KSampler、SaveImage

## 部署配置

### Docker部署

```bash
# 构建镜像
docker build -t style-transform-api .

# 运行容器
docker run -d \
  --name style-transform-api \
  -p 8000:8000 \
  -e COMFYUI_BASE_URL=http://your-comfyui-server:8188 \
  style-transform-api
```

### Docker Compose部署

```bash
docker-compose up -d
```

### 环境变量配置

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| DEBUG | false | 调试模式 |
| LOG_LEVEL | INFO | 日志级别 |
| COMFYUI_BASE_URL | http://localhost:8188 | ComfyUI服务地址 |
| HOST | 0.0.0.0 | 服务器地址 |
| PORT | 8000 | 服务器端口 |
| MAX_CONCURRENT_TASKS | 10 | 最大并发任务数 |
| TASK_CLEANUP_HOURS | 24 | 任务清理时间（小时） |

## 监控和日志

### 健康检查

```http
GET /health
```

返回服务状态和ComfyUI连接状态。

### 系统统计

```http
GET /api/v1/stats
```

返回任务统计信息。

### 日志配置

日志级别可通过 `LOG_LEVEL` 环境变量配置：
- DEBUG: 详细调试信息
- INFO: 一般信息（推荐）
- WARNING: 警告信息
- ERROR: 错误信息

## 性能优化

### 并发处理

- 使用FastAPI的后台任务进行异步处理
- 支持多个ComfyUI实例负载均衡
- 内存任务管理，避免数据库开销

### 缓存策略

- 工作流模板缓存
- 图像下载缓存（可选）
- 结果URL缓存

### 资源管理

- 自动清理过期任务
- 内存使用监控
- 连接池管理

## 故障排除

### 常见问题

1. **ComfyUI连接失败**
   - 检查ComfyUI服务是否运行
   - 验证COMFYUI_BASE_URL配置
   - 检查网络连接

2. **图像下载失败**
   - 验证图像URL可访问性
   - 检查图像格式支持
   - 确认网络权限

3. **工作流执行失败**
   - 检查ComfyUI模型文件
   - 验证工作流JSON格式
   - 查看ComfyUI日志

### 日志分析

```bash
# 查看容器日志
docker logs style-transform-api

# 实时日志
docker logs -f style-transform-api
```

## 开发指南

### 项目结构

```
style_transform_api/
├── app/
│   ├── api/              # API路由
│   ├── schemas/          # Pydantic模型
│   ├── services/         # 业务逻辑
│   ├── utils/           # 工具函数
│   ├── workflows/       # 工作流模板
│   ├── config.py        # 配置管理
│   └── main.py          # 应用入口
├── comfyui_client/      # ComfyUI客户端库
├── requirements.txt     # 依赖文件
├── Dockerfile          # Docker配置
└── docker-compose.yml  # Docker Compose配置
```

### 扩展开发

1. **添加新风格**：在 `schemas/request.py` 中添加新的风格类型
2. **自定义工作流**：修改 `services/comfyui_service.py` 中的工作流处理逻辑
3. **添加新API**：在 `api/` 目录下创建新的路由模块

## 许可证

MIT License

## 支持

如有问题或建议，请提交Issue或联系开发团队。 