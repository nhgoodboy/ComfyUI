# ComfyUI 工作流服务器

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

**基于RPC协议的高性能ComfyUI工作流处理微服务**

专注于图像工作流处理，提供标准化API接口和实时状态推送

</div>

## 📋 目录

- [项目概述](#-项目概述)
- [核心特性](#-核心特性)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [环境配置](#-环境配置)
- [部署指南](#-部署指南)
- [API文档](#-api文档)
- [工作流管理](#-工作流管理)
- [开发指南](#-开发指南)
- [故障排除](#-故障排除)
- [贡献指南](#-贡献指南)

## 🚀 项目概述

ComfyUI工作流服务器是一个现代化的微服务应用，采用RPC架构设计，专门用于处理ComfyUI图像工作流。服务器提供标准化的JSON-RPC 2.0接口，支持实时WebSocket推送，具备完整的任务管理和文件处理能力。

### 设计理念

- **微服务架构**: 专注于工作流处理的核心功能
- **RPC优先**: 采用JSON-RPC 2.0协议，提供统一的API接口
- **实时推送**: WebSocket支持任务状态实时更新
- **高可用**: 异步处理、错误重试、优雅降级
- **易扩展**: 模块化设计，支持自定义工作流

## ✨ 核心特性

### 🔧 RPC协议支持
- **JSON-RPC 2.0**: 标准化的API协议
- **批量请求**: 支持一次处理multiple RPC调用
- **错误处理**: 完整的错误码体系和异常处理
- **参数验证**: 自动参数验证和类型检查

### 📡 实时通信
- **WebSocket推送**: 实时任务状态更新
- **双连接模式**: 请求级和服务级连接支持
- **心跳机制**: 自动连接保活和重连
- **消息分发**: 智能消息路由和推送

### 🎨 工作流管理
- **动态配置**: YAML配置文件支持热重载
- **参数化处理**: 灵活的参数映射和验证
- **多工作流**: 支持多种预定义工作流模板
- **版本管理**: 工作流版本控制和兼容性处理

### 📁 文件处理
- **安全上传**: 文件类型验证和大小限制
- **智能命名**: 自动文件命名和冲突处理
- **存储管理**: 分类存储和自动清理机制
- **URL访问**: 静态文件服务和外部访问支持

### 🔍 监控运维
- **健康检查**: 完整的系统健康状态监控
- **日志系统**: 结构化日志和多级别输出
- **性能统计**: 任务统计和系统资源监控
- **错误追踪**: 详细的错误信息和调用栈

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    ComfyUI 工作流服务器                        │
├─────────────────────────────────────────────────────────────┤
│  🌐 接口层 (FastAPI + RPC)                                   │
│  ├─ RPC Handler      ├─ WebSocket Manager  ├─ Static Files  │
│  ├─ 请求验证         ├─ 实时推送           ├─ 文件访问      │
│  └─ 错误处理         └─ 连接管理           └─ CORS支持      │
├─────────────────────────────────────────────────────────────┤
│  ⚙️ 业务层 (Services)                                        │
│  ├─ WorkflowTaskService  ├─ ComfyUIService  ├─ DownloadService │
│  ├─ 任务管理             ├─ ComfyUI通信     ├─ 文件下载        │
│  └─ 状态追踪             └─ WebSocket处理   └─ 文件处理        │
├─────────────────────────────────────────────────────────────┤
│  🔧 核心层 (Core)                                            │
│  ├─ WorkflowRegistry     ├─ ParameterMapper                  │
│  ├─ 工作流注册表         ├─ 参数映射器                       │
│  └─ 动态配置加载         └─ 类型转换和验证                   │
├─────────────────────────────────────────────────────────────┤
│  💾 存储层 (Storage)                                         │
│  ├─ uploads/            ├─ outputs/         ├─ workflows/    │
│  ├─ 用户上传文件        ├─ 生成结果文件     ├─ 工作流配置    │
│  └─ 临时文件存储        └─ 静态资源访问     └─ 模板管理      │
└─────────────────────────────────────────────────────────────┘
                                 ↕️
                     ┌─────────────────────────┐
                     │     ComfyUI 后端        │
                     │  ├─ WebSocket 连接      │
                     │  ├─ HTTP API 调用       │
                     │  └─ 工作流执行引擎      │
                     └─────────────────────────┘
```

### 核心组件说明

#### RPC层
- **RPCHandler**: 处理所有RPC请求的核心组件
- **RPCRouter**: 方法路由和注册管理
- **RPCValidator**: 请求参数验证和格式检查
- **RPCFormatter**: 响应格式化和错误处理

#### 服务层
- **WorkflowTaskService**: 工作流任务生命周期管理
- **ComfyUIService**: ComfyUI后端通信和WebSocket处理
- **DownloadService**: 文件下载和处理服务

#### 核心层
- **WorkflowRegistry**: 工作流注册表和配置管理
- **ParameterMapper**: 参数映射和节点路径处理

## 🚀 快速开始

### 系统要求

- **Python**: 3.11+ 
- **内存**: 最低2GB，推荐4GB+
- **存储**: 最低10GB可用空间
- **网络**: 需要访问ComfyUI服务器

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd comfyui_workflow_server

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置设置

```bash
# 复制环境配置模板
cp env.template .env

# 编辑配置文件
nano .env  # 或使用其他编辑器
```

**关键配置项**:
```env
# ComfyUI服务器地址
COMFYUI_HOST=localhost
COMFYUI_PORT=8188

# 服务器设置
HOST=0.0.0.0
PORT=8000
DEBUG=false

# 日志级别
LOG_LEVEL=INFO
```

### 3. 启动服务

```bash
# 开发模式启动
python start.py

# 指定配置文件启动
python start.py --config custom.env

# 指定端口启动
python start.py --port 8080
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 获取工作流列表
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.list",
    "params": {},
    "id": "test_001"
  }'
```

## ⚙️ 环境配置

### 开发环境配置

适用于本地开发和测试：

```env
# 开发环境设置
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# 本地ComfyUI
COMFYUI_HOST=localhost
COMFYUI_PORT=8188

# 允许所有跨域请求
CORS_ORIGINS=*

# 较小的文件限制
MAX_FILE_SIZE=10485760  # 10MB
```

### 生产环境配置

适用于生产部署：

```env
# 生产环境设置
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json

# 生产ComfyUI服务器
COMFYUI_HOST=comfyui-server.internal
COMFYUI_PORT=8188

# 限制跨域请求
CORS_ORIGINS=https://your-frontend.com,https://admin.your-company.com

# 工作进程数（根据CPU核心数调整）
WORKERS=4

# 更大的文件限制
MAX_FILE_SIZE=52428800  # 50MB

# 安全设置
ENABLE_RATE_LIMITING=true
MAX_REQUESTS_PER_MINUTE=120
```

### 高级配置选项

#### 工作流配置
```env
# 工作流任务配置
MAX_CONCURRENT_WORKFLOWS=5
WORKFLOW_TASK_TIMEOUT=600
WORKFLOW_STATUS_CHECK_INTERVAL=3
```

#### WebSocket配置
```env
# WebSocket连接配置
WEBSOCKET_CONNECTION_TIMEOUT=60
WEBSOCKET_PING_INTERVAL=30
WEBSOCKET_MAX_CONNECTIONS=200
WEBSOCKET_SERVICE_CLIENT_ID=workflow_admin_system
```

#### 文件清理配置
```env
# 自动清理配置
ENABLE_AUTO_CLEANUP=true
TEMP_FILE_RETENTION_HOURS=6
INPUT_FILE_RETENTION_DAYS=14
OUTPUT_FILE_RETENTION_DAYS=60
CLEANUP_INTERVAL_HOURS=12
```

## 🐳 部署指南

### Docker部署（推荐）

#### 1. 基础Docker部署

```bash
# 构建镜像
docker build -t comfyui-workflow-server .

# 运行容器
docker run -d \
  --name comfyui-workflow \
  -p 8000:8000 \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/workflows:/app/workflows \
  -v $(pwd)/logs:/app/logs \
  -e COMFYUI_HOST=host.docker.internal \
  -e COMFYUI_PORT=8188 \
  comfyui-workflow-server
```

#### 2. Docker Compose部署

创建`docker-compose.yml`:

```yaml
version: '3.8'

services:
  comfyui-workflow:
    build: .
    container_name: comfyui-workflow-server
    ports:
      - "8000:8000"
    volumes:
      - ./outputs:/app/outputs
      - ./uploads:/app/uploads
      - ./workflows:/app/workflows
      - ./logs:/app/logs
      - ./configs:/app/configs
    environment:
      - COMFYUI_HOST=comfyui
      - COMFYUI_PORT=8188
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=INFO
      - WORKERS=2
    restart: unless-stopped
    depends_on:
      - comfyui
    networks:
      - comfyui-network

  comfyui:
    image: comfyui/comfyui:latest  # 假设的ComfyUI镜像
    container_name: comfyui-backend
    ports:
      - "8188:8188"
    volumes:
      - comfyui-models:/app/models
      - comfyui-output:/app/output
    restart: unless-stopped
    networks:
      - comfyui-network

volumes:
  comfyui-models:
  comfyui-output:

networks:
  comfyui-network:
    driver: bridge
```

启动服务：

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f comfyui-workflow

# 停止服务
docker-compose down
```

### Kubernetes部署

#### 1. 配置文件部署

创建`k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: comfyui-workflow-server
  labels:
    app: comfyui-workflow
spec:
  replicas: 3
  selector:
    matchLabels:
      app: comfyui-workflow
  template:
    metadata:
      labels:
        app: comfyui-workflow
    spec:
      containers:
      - name: workflow-server
        image: comfyui-workflow-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: COMFYUI_HOST
          value: "comfyui-service"
        - name: COMFYUI_PORT
          value: "8188"
        - name: ENVIRONMENT
          value: "production"
        - name: WORKERS
          value: "1"
        volumeMounts:
        - name: outputs-volume
          mountPath: /app/outputs
        - name: uploads-volume
          mountPath: /app/uploads
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: outputs-volume
        persistentVolumeClaim:
          claimName: comfyui-outputs-pvc
      - name: uploads-volume
        persistentVolumeClaim:
          claimName: comfyui-uploads-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: comfyui-workflow-service
spec:
  selector:
    app: comfyui-workflow
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

部署到集群：

```bash
# 应用配置
kubectl apply -f k8s-deployment.yaml

# 查看部署状态
kubectl get pods -l app=comfyui-workflow

# 查看服务
kubectl get services comfyui-workflow-service

# 查看日志
kubectl logs -l app=comfyui-workflow -f
```

### 传统服务器部署

#### 1. Systemd服务配置

创建服务文件`/etc/systemd/system/comfyui-workflow.service`:

```ini
[Unit]
Description=ComfyUI Workflow Server
After=network.target
Wants=network.target

[Service]
Type=exec
User=comfyui
Group=comfyui
WorkingDirectory=/opt/comfyui-workflow-server
Environment=PATH=/opt/comfyui-workflow-server/venv/bin
ExecStart=/opt/comfyui-workflow-server/venv/bin/python start.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start comfyui-workflow

# 开机自启
sudo systemctl enable comfyui-workflow

# 查看状态
sudo systemctl status comfyui-workflow

# 查看日志
sudo journalctl -u comfyui-workflow -f
```

#### 2. Nginx反向代理配置

创建Nginx配置`/etc/nginx/sites-available/comfyui-workflow`:

```nginx
upstream comfyui_workflow {
    server 127.0.0.1:8000;
    # 如果有多个实例，可以添加负载均衡
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name your-domain.com;

    # 基础安全设置
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # 文件上传大小限制
    client_max_body_size 50M;

    # 代理设置
    location / {
        proxy_pass http://comfyui_workflow;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket支持
    location /ws/ {
        proxy_pass http://comfyui_workflow;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket专用超时设置
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # 静态文件直接服务
    location /outputs/ {
        alias /opt/comfyui-workflow-server/outputs/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # 健康检查
    location /health {
        proxy_pass http://comfyui_workflow;
        access_log off;
    }

    # 日志配置
    access_log /var/log/nginx/comfyui-workflow.access.log;
    error_log /var/log/nginx/comfyui-workflow.error.log;
}

# HTTPS配置（使用Let's Encrypt）
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # 重定向到HTTPS
    if ($scheme != "https") {
        return 301 https://$server_name$request_uri;
    }

    # 复用HTTP配置
    include /etc/nginx/sites-available/comfyui-workflow-common;
}
```

启用配置：

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/comfyui-workflow /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

## 📚 API文档

本项目提供完整的API接入文档，详细说明了所有RPC方法、WebSocket协议和Go语言集成示例。

👉 **[查看完整API文档](./API_接入文档.md)**

### 核心API方法概览

#### 工作流方法
- `workflow.execute` - 执行工作流任务
- `workflow.list` - 获取可用工作流列表
- `workflow.get_schema` - 获取工作流参数模式
- `workflow.get_status` - 查询任务状态
- `workflow.get_result` - 获取任务结果
- `workflow.cancel` - 取消任务
- `workflow.search` - 搜索工作流

#### 文件方法
- `files.get_output_image` - 获取输出图片（base64）
- `files.get_output_image_info` - 获取图片信息
- `files.list_output_images` - 列出输出图片

#### 系统方法
- `system.health` - 系统健康检查
- `system.get_stats` - 获取系统统计信息

### 快速API调用示例

```bash
# 获取工作流列表
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.list",
    "params": {},
    "id": "list_workflows"
  }'

# 执行工作流
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.execute",
    "params": {
      "request_id": "test_20250803_001",
      "workflow_id": "clay_style_transform",
      "params": {
        "input_image": "https://example.com/image.jpg"
      }
    },
    "id": "execute_workflow"
  }'

# 查询任务状态
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.get_status",
    "params": {
      "request_id": "test_20250803_001"
    },
    "id": "get_status"
  }'
```

## 🎨 工作流管理

### 工作流配置文件

工作流通过YAML配置文件定义，支持参数化和动态配置。配置文件位于`workflows/workflows.yaml`。

#### 配置文件结构

```yaml
workflows:
  clay_style_transform:
    name: "黏土风格转换"
    description: "将输入图像转换为黏土风格的图像"
    template_file: "clay_style_transform.json"
    estimated_time: 45
    tags: ["风格转换", "黏土风格", "3D效果"]
    version: "1.0.0"
    
    parameters:
      input_image:
        type: "file"
        description: "输入图像文件"
        node_path: "1.inputs.image"
        required: true
        validation:
          accept: ["jpg", "jpeg", "png", "webp"]
```

### 内置工作流

#### 1. 黏土风格转换 (clay_style_transform)
- **功能**: 将普通图片转换为黏土质感的3D风格
- **预估时间**: 45秒
- **参数**: 输入图片

#### 2. 动漫风格转换 (anime_style_transform)
- **功能**: 将照片转换为动漫/漫画风格
- **预估时间**: 45秒
- **参数**: 输入图片

#### 3. 人物场景融合 (person_scene_merge)
- **功能**: 将人物图片与场景图片进行智能融合
- **预估时间**: 60秒
- **参数**: 人物图片、场景图片、融合描述（可选）

### 自定义工作流

#### 1. 创建工作流模板

在`workflows/`目录下创建ComfyUI工作流JSON文件：

```json
{
  "1": {
    "inputs": {
      "image": "input_image_placeholder",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "Load Image"
    }
  },
  "2": {
    "inputs": {
      "text": "Clay Style, 3D render, cute",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  }
  // ... 更多节点
}
```

#### 2. 更新配置文件

在`workflows/workflows.yaml`中添加工作流定义：

```yaml
workflows:
  custom_workflow:
    name: "自定义工作流"
    description: "工作流描述"
    template_file: "custom_workflow.json"
    estimated_time: 30
    tags: ["自定义", "测试"]
    version: "1.0.0"
    
    parameters:
      input_param:
        type: "string"
        description: "参数描述"
        node_path: "2.inputs.text"
        required: true
        default: "默认值"
```

#### 3. 重启服务

修改配置后需要重启服务以加载新的工作流：

```bash
# 如果使用systemd
sudo systemctl restart comfyui-workflow

# 如果使用Docker
docker-compose restart comfyui-workflow

# 如果直接运行
# 停止服务后重新启动
python start.py
```

### 工作流参数类型

支持的参数类型及其配置：

#### 文件类型 (file)
```yaml
input_image:
  type: "file"
  description: "输入图像文件"
  node_path: "1.inputs.image"
  required: true
  validation:
    accept: ["jpg", "jpeg", "png", "webp"]
    max_size: 10485760  # 10MB
```

#### 字符串类型 (string)
```yaml
prompt:
  type: "string"
  description: "提示词"
  node_path: "2.inputs.text"
  required: false
  default: "默认提示词"
  validation:
    min_length: 1
    max_length: 500
```

#### 数值类型 (number)
```yaml
strength:
  type: "number"
  description: "强度"
  node_path: "3.inputs.strength"
  required: false
  default: 0.8
  validation:
    min: 0.0
    max: 1.0
```

#### 布尔类型 (boolean)
```yaml
enabled:
  type: "boolean"
  description: "是否启用"
  node_path: "4.inputs.enabled"
  required: false
  default: true
```

## 💻 开发指南

### 项目结构

```
comfyui_workflow_server/
├── app/                          # 应用主目录
│   ├── core/                     # 核心模块
│   │   ├── parameter_mapper.py   # 参数映射器
│   │   └── workflow_registry.py  # 工作流注册表
│   ├── models/                   # 数据模型
│   │   ├── api_models.py         # API模型定义
│   │   └── workflow_models.py    # 工作流模型
│   ├── rpc/                      # RPC协议层
│   │   ├── methods/              # RPC方法实现
│   │   │   ├── workflow.py       # 工作流方法
│   │   │   ├── files.py          # 文件方法
│   │   │   └── system.py         # 系统方法
│   │   ├── handler.py            # RPC请求处理器
│   │   ├── router.py             # 方法路由器
│   │   ├── protocol.py           # 协议模型
│   │   ├── validator.py          # 参数验证器
│   │   ├── formatter.py          # 响应格式化器
│   │   ├── exceptions.py         # 异常定义
│   │   └── error_codes.py        # 错误码定义
│   ├── services/                 # 业务服务层
│   │   ├── comfyui_service.py    # ComfyUI服务
│   │   ├── workflow_task_service.py # 工作流任务服务
│   │   └── download_service.py   # 下载服务
│   ├── utils/                    # 工具模块
│   │   ├── websocket_push.py     # WebSocket推送管理
│   │   ├── file_naming.py        # 文件命名工具
│   │   └── monitoring.py         # 监控工具
│   ├── workflows/                # 工作流实现
│   │   ├── base/                 # 基础工作流类
│   │   └── universal_workflow.py # 通用工作流处理器
│   └── config.py                 # 配置管理
├── comfyui_client/               # ComfyUI客户端库
│   ├── endpoints/                # API端点
│   ├── models/                   # 客户端模型
│   ├── utils/                    # 客户端工具
│   ├── client.py                 # 主客户端类
│   ├── websocket.py              # WebSocket客户端
│   └── exceptions.py             # 客户端异常
├── workflows/                    # 工作流配置和模板
│   ├── workflows.yaml            # 工作流配置文件
│   └── *.json                    # ComfyUI工作流模板
├── main.py                       # FastAPI应用入口
├── start.py                      # 启动脚本
├── requirements.txt              # Python依赖
├── Dockerfile                    # Docker构建文件
└── env.template                  # 环境配置模板
```

### 开发环境设置

#### 1. 代码规范

使用以下工具确保代码质量：

```bash
# 安装开发依赖
pip install black isort flake8 mypy pytest

# 代码格式化
black app/ comfyui_client/
isort app/ comfyui_client/

# 代码检查
flake8 app/ comfyui_client/
mypy app/ comfyui_client/

# 运行测试
pytest tests/
```

#### 2. 预提交钩子

创建`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

安装钩子：

```bash
pip install pre-commit
pre-commit install
```

### 添加新的RPC方法

#### 1. 定义方法

在相应的方法文件中（如`app/rpc/methods/workflow.py`）添加新方法：

```python
from ..router import rpc_method
from ..validator import RPCValidator
from ..exceptions import RPCError
from ..error_codes import ErrorCodes

@rpc_method("workflow.new_method")
async def new_workflow_method(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """新的工作流方法
    
    Args:
        params: {
            "param1": "必需参数",
            "param2": "可选参数"
        }
    """
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["param1"])
        
        param1 = params["param1"]
        param2 = params.get("param2", "default_value")
        
        # 业务逻辑处理
        result = await process_business_logic(param1, param2)
        
        return result
        
    except Exception as e:
        logger.error(f"新方法执行失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="方法执行失败",
            data={"error": str(e)}
        )
```

#### 2. 更新文档

在`main.py`的根端点中添加新方法到`available_methods`列表：

```python
"available_methods": [
    # ... 现有方法
    "workflow.new_method",
]
```

#### 3. 添加测试

创建测试文件`tests/test_new_method.py`:

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_new_workflow_method():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/rpc", json={
            "method": "workflow.new_method",
            "params": {
                "param1": "test_value"
            },
            "id": "test_001"
        })
    
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert data["id"] == "test_001"
```

### 扩展工作流处理

#### 1. 创建自定义工作流处理器

```python
from app.workflows.base.workflow_base import WorkflowBase
from typing import Dict, Any, List

class CustomWorkflow(WorkflowBase):
    """自定义工作流处理器"""
    
    def __init__(self, workflow_id: str, config: Dict[str, Any]):
        super().__init__(workflow_id, config)
    
    async def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """自定义参数验证"""
        validated = await super().validate_parameters(parameters)
        
        # 添加自定义验证逻辑
        if "custom_param" in validated:
            if not self._validate_custom_param(validated["custom_param"]):
                raise ValueError("自定义参数验证失败")
        
        return validated
    
    def _validate_custom_param(self, value: Any) -> bool:
        """自定义参数验证逻辑"""
        # 实现验证逻辑
        return True
    
    async def process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """自定义结果处理"""
        processed = await super().process_result(result)
        
        # 添加自定义处理逻辑
        processed["custom_metadata"] = self._generate_metadata()
        
        return processed
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """生成自定义元数据"""
        return {
            "processor": "CustomWorkflow",
            "version": "1.0.0"
        }
```

#### 2. 注册自定义处理器

在`app/core/workflow_registry.py`中注册：

```python
def _create_workflow_instance(self, workflow_id: str, config: Dict[str, Any]) -> WorkflowBase:
    """创建工作流实例"""
    if workflow_id == "custom_workflow":
        return CustomWorkflow(workflow_id, config)
    else:
        return UniversalWorkflow(workflow_id, config)
```

### 监控和日志

#### 1. 添加自定义监控指标

```python
from app.utils.monitoring import monitor_execution_time, monitor_error

@monitor_execution_time("custom_operation")
async def custom_operation():
    """带监控的自定义操作"""
    try:
        result = await some_operation()
        return result
    except Exception as e:
        monitor_error("custom_operation", str(e))
        raise
```

#### 2. 结构化日志

```python
import logging
import json

logger = logging.getLogger(__name__)

def log_structured(level: str, message: str, **kwargs):
    """结构化日志记录"""
    log_data = {
        "message": message,
        "timestamp": time.time(),
        **kwargs
    }
    
    if level == "info":
        logger.info(json.dumps(log_data))
    elif level == "error":
        logger.error(json.dumps(log_data))
    elif level == "warning":
        logger.warning(json.dumps(log_data))

# 使用示例
log_structured("info", "工作流执行开始", 
               workflow_id="clay_style_transform", 
               request_id="req_001",
               user_id="user_123")
```

## 🔧 故障排除

### 常见问题

#### 1. ComfyUI连接失败

**症状**: 服务启动时显示ComfyUI连接失败

**解决方案**:
```bash
# 检查ComfyUI是否运行
curl http://localhost:8188/system_stats

# 检查配置文件中的地址设置
grep COMFYUI_HOST .env
grep COMFYUI_PORT .env

# 检查网络连通性
telnet localhost 8188

# 查看详细日志
tail -f logs/app.log | grep -i comfyui
```

#### 2. 工作流执行超时

**症状**: 工作流任务长时间处于"running"状态

**解决方案**:
```bash
# 检查ComfyUI队列状态
curl http://localhost:8188/queue

# 增加超时时间
echo "WORKFLOW_TASK_TIMEOUT=600" >> .env

# 检查ComfyUI模型是否正确加载
curl http://localhost:8188/object_info
```

#### 3. 文件上传失败

**症状**: 文件上传时返回错误

**解决方案**:
```bash
# 检查文件大小限制
grep MAX_FILE_SIZE .env

# 检查文件格式支持
grep ALLOWED_EXTENSIONS .env

# 检查上传目录权限
ls -la uploads/
chmod 755 uploads/

# 检查磁盘空间
df -h
```

#### 4. WebSocket连接断开

**症状**: 实时状态更新中断

**解决方案**:
```bash
# 检查WebSocket配置
grep WEBSOCKET .env

# 增加连接超时时间
echo "WEBSOCKET_CONNECTION_TIMEOUT=120" >> .env

# 检查网络代理设置（如Nginx）
# 确保WebSocket升级头正确配置

# 查看连接日志
grep -i websocket logs/app.log
```

#### 5. 内存不足错误

**症状**: 服务崩溃或响应缓慢

**解决方案**:
```bash
# 检查内存使用
free -h
ps aux | grep python

# 减少并发任务数
echo "MAX_CONCURRENT_WORKFLOWS=2" >> .env

# 启用自动清理
echo "ENABLE_AUTO_CLEANUP=true" >> .env
echo "TEMP_FILE_RETENTION_HOURS=1" >> .env

# 如果使用Docker，增加内存限制
docker run --memory=4g comfyui-workflow-server
```

### 日志分析

#### 1. 日志级别和位置

```bash
# 应用日志
tail -f logs/app.log

# 错误日志
grep -i error logs/app.log

# 特定请求日志
grep "req_20250803_001" logs/app.log

# 性能日志
grep "execution_time" logs/app.log
```

#### 2. 常见日志模式

```bash
# ComfyUI连接问题
grep "ComfyUI.*failed\|ComfyUI.*error" logs/app.log

# 工作流执行问题
grep "workflow.*failed\|workflow.*error" logs/app.log

# 文件处理问题
grep "file.*error\|download.*failed" logs/app.log

# WebSocket连接问题
grep "websocket.*disconnect\|websocket.*error" logs/app.log
```

### 性能优化

#### 1. 数据库优化（如果使用）

```bash
# 清理旧任务数据
# 通过系统管理接口或直接调用服务方法
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "system.cleanup_tasks",
    "params": {"max_age_hours": 24},
    "id": "cleanup_001"
  }'
```

#### 2. 文件系统优化

```bash
# 启用自动清理
echo "ENABLE_AUTO_CLEANUP=true" >> .env
echo "CLEANUP_INTERVAL_HOURS=6" >> .env

# 手动清理临时文件
find uploads/temp -type f -mtime +1 -delete

# 清理旧的输出文件
find outputs -name "*.png" -mtime +30 -delete
```

#### 3. 网络优化

```bash
# 调整超时设置
echo "COMFYUI_TIMEOUT=180" >> .env
echo "COMFYUI_RETRY_DELAY=3" >> .env

# 启用连接池
echo "CONNECTION_POOL_SIZE=10" >> .env

# 优化WebSocket设置
echo "WEBSOCKET_PING_INTERVAL=20" >> .env
```

### 监控检查

#### 1. 健康检查

```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细系统状态
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "system.get_stats",
    "params": {},
    "id": "stats_001"
  }'

# 工作流可用性检查
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.list",
    "params": {},
    "id": "list_001"
  }'
```

#### 2. 性能监控

```bash
# CPU和内存使用率
top -p $(pgrep -f "start.py")

# 网络连接状态
netstat -an | grep :8000

# 磁盘使用情况
du -sh uploads/ outputs/ logs/
```

## 🤝 贡献指南

我们欢迎社区贡献！请遵循以下指南：

### 贡献流程

1. **Fork仓库**并创建功能分支
2. **编写代码**并添加测试
3. **确保所有测试通过**
4. **提交Pull Request**

### 代码规范

- 使用Python 3.11+语法特性
- 遵循PEP 8代码风格
- 添加适当的类型注解
- 编写清晰的文档字符串
- 保持100%测试覆盖率

### 提交信息规范

使用约定式提交格式：

```
type(scope): description

[optional body]

[optional footer]
```

示例：
```
feat(workflow): 添加新的图像风格转换工作流

添加油画风格转换功能，支持多种画笔效果配置

Closes #123
```

类型说明：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具链相关

### 开发环境

```bash
# 设置开发环境
git clone <your-fork>
cd comfyui_workflow_server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 安装预提交钩子
pre-commit install

# 运行测试
pytest tests/ -v --cov=app

# 运行代码检查
black app/ comfyui_client/
isort app/ comfyui_client/
flake8 app/ comfyui_client/
mypy app/ comfyui_client/
```

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

- **GitHub Issues**: [提交问题](https://github.com/your-org/comfyui_workflow_server/issues)
- **讨论区**: [GitHub Discussions](https://github.com/your-org/comfyui_workflow_server/discussions)
- **文档**: [完整API文档](./API_接入文档.md)

---

<div align="center">

**[⬆ 返回顶部](#comfyui-工作流服务器)**

Made with ❤️ by the ComfyUI Workflow Server Team

</div>