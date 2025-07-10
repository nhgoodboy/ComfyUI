# ComfyUI Workflow Server

简化的ComfyUI工作流微服务，专注于基于用户ID的资源隔离和图像风格转换功能。

## 项目概述

这是一个轻量级的微服务，为ComfyUI提供用户隔离的工作流API。已移除复杂的认证系统，专注于核心业务功能。

## 主要特性

- **用户隔离**: 基于user_id的文件和任务完全隔离
- **简化架构**: 移除认证复杂性，专注核心功能
- **微服务友好**: 适合与主服务集成，由主服务负责认证
- **RESTful API**: 清晰的路径结构和资源管理
- **实时反馈**: WebSocket支持任务进度推送

## API 端点

### 用户任务管理
- `POST /api/v1/users/{user_id}/tasks` - 创建新任务
- `GET /api/v1/users/{user_id}/tasks` - 获取用户任务列表
- `GET /api/v1/users/{user_id}/tasks/{task_id}` - 获取任务详情
- `GET /api/v1/users/{user_id}/tasks/{task_id}/result` - 获取任务结果
- `DELETE /api/v1/users/{user_id}/tasks/{task_id}` - 取消任务

### 用户文件管理
- `POST /api/v1/users/{user_id}/files/upload` - 上传文件
- `GET /api/v1/users/{user_id}/files` - 获取用户文件列表
- `GET /api/v1/users/{user_id}/files/{file_id}` - 获取文件信息
- `DELETE /api/v1/users/{user_id}/files/{file_id}` - 删除文件
- `GET /api/v1/users/{user_id}/files/stats` - 获取文件统计

### 全局风格管理
- `GET /api/v1/styles` - 获取所有可用风格
- `GET /api/v1/styles/search?q={keyword}` - 搜索风格
- `GET /api/v1/styles/{style_id}` - 获取风格详情

### 系统接口
- `GET /health` - 健康检查
- `GET /` - API概览

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

# 存储配置
UPLOADS_DIR=uploads
OUTPUTS_DIR=outputs
MAX_FILE_SIZE=10485760

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

## 用户隔离说明

### 文件隔离
- 上传文件：`uploads/{user_id}/`
- 输出文件：`outputs/{user_id}/`
- 每个用户只能访问自己的文件

### 任务隔离
- 任务数据按user_id完全隔离
- 任务ID在全局唯一，但用户只能访问自己的任务
- 任务结果与用户ID绑定

### API安全
- 通过路径参数传递user_id
- 主服务负责用户认证和权限验证
- 此微服务专注于业务逻辑处理

## 与主服务集成

此微服务设计为内部服务，建议：

1. **网络隔离**: 仅允许主服务访问
2. **用户验证**: 主服务验证user_id有效性
3. **请求代理**: 主服务代理所有用户请求
4. **监控日志**: 通过主服务统一监控和日志

## 目录结构

```
app/
├── api/v1/          # API路由
├── services/        # 业务服务
├── models/          # 数据模型
├── config.py        # 配置管理
└── main.py          # 应用入口
```

## 更新日志

### v2.0.0 - 简化版本
- 移除复杂的认证系统
- 简化为基于user_id的资源隔离
- 优化微服务架构
- 专注核心业务功能 