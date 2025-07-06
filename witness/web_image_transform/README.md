# Web Image Transform - 安全代理客户端

这是一个为`ComfyUI工作流服务器`设计的安全代理Web客户端。它提供了一个现代化的用户界面，用于图像风格转换，同时确保了与主服务器通信的绝对安全。

## 核心架构：安全代理模式

此Web应用本身是一个**前后端分离**的项目，其后端充当一个**安全代理**：

- **前端 (HTML/JS/CSS)**: 用户与之交互的界面，负责上传图片和展示结果。
- **后端 (Python/FastAPI)**:
    - **安全屏障**: 唯一持有并使用`API_KEY`和`API_SECRET_KEY`的组件。
    - **请求签名**: 所有发往主服务器的请求都在此后端进行HMAC签名。
    - **会话管理**: 使用服务器端Session为每个浏览器会话创建唯一用户ID，并自动获取JWT令牌。
    - **实时通信**: 通过WebSocket将主服务器的任务状态实时推送到前端。

**这种架构确保了敏感的API密钥永远不会暴露在前端代码中，提供了银行级的安全性。**

## ✨ 特性

- **🔐 绝对安全**: 敏感密钥安全地存储在后端代理中。
- **👥 自动多用户支持**: 利用Session机制，天然适配主服务器的多用户架构。
- **⚡ 实时更新**: 使用WebSocket提供流畅的用户体验，实时显示任务进度和结果。
- **🎨 动态风格加载**: 自动从主服务器获取并显示所有可用的图像风格。
- **🖼️ 现代UI**: 简洁、直观、响应式的用户界面，支持拖拽上传。

## 🚀 快速开始

### 1. 前提条件

- [Python 3.8+](https://www.python.org/)
- 一个正在运行的 `ComfyUI工作流服务器` 实例。
- 从主服务器管理员处获取的 `API_KEY` 和 `API_SECRET_KEY`。

### 2. 安装

```bash
# 克隆项目
git clone <this-repository-url>
cd web_image_transform

# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

复制环境配置模板文件：

```bash
cp .env.example .env
```

然后，编辑 `.env` 文件，填入你的配置：

```env
# 主服务器的完整基础URL
COMFYUI_WORKFLOW_SERVER_URL=http://127.0.0.1:8000

# 用于访问主服务器的API Key
API_KEY=your-main-server-api-key

# 用于HMAC请求签名的API Secret Key
API_SECRET_KEY=your-main-server-api-secret-key

# Web应用自身配置 (保持默认或按需修改)
APP_HOST=0.0.0.0
APP_PORT=8080
SESSION_SECRET_KEY=generate-a-random-secret-key-here
LOG_LEVEL=INFO
DEBUG=true
```
**重要**: 请务必生成一个随机的 `SESSION_SECRET_KEY` 以确保会话安全。

### 4. 运行

```bash
python run.py
```

服务器启动后，在浏览器中打开 `http://127.0.0.1:8080` 即可开始使用。

## 工作流程

1.  用户打开网页，浏览器与`web_image_transform`后端建立会话(Session)。
2.  前端JS向后端请求可用风格列表。
3.  后端为当前会话生成一个唯一的`user_id`，并向主服务器请求该用户的JWT令牌。
4.  后端使用JWT令牌从主服务器获取风格列表，并返回给前端。
5.  用户上传图片并选择风格，点击"开始转换"。
6.  请求被发送到`web_image_transform`后端。
7.  后端执行完整的安全认证流程（签名、添加令牌），并将转换请求发送到主服务器。
8.  主服务器返回任务ID。
9.  后端启动一个后台任务，开始轮询主服务器的任务状态。
10. 前端通过WebSocket连接实时接收来自后端的任务状态更新，并刷新UI。
11. 任务完成后，结果图片URL被推送到前端并显示。

## 项目结构

```
witness/web_image_transform/
├── app/                        # 应用核心代码
│   ├── __init__.py
│   ├── main.py                 # FastAPI主应用
│   ├── config.py              # 配置管理
│   ├── api/                   # API路由
│   │   ├── __init__.py
│   │   ├── web_api.py         # Web API路由
│   │   └── websocket.py       # WebSocket处理
│   ├── services/              # 业务服务
│   │   ├── __init__.py
│   │   ├── transform_service.py # 图像变换服务
│   │   └── file_service.py    # 文件处理服务
│   ├── utils/                 # 工具模块
│   │   ├── __init__.py
│   │   └── logger.py          # 日志系统
│   └── static/                # 静态文件
│       ├── css/
│       │   └── style.css      # 样式文件
│       └── js/
│           └── app.js         # 前端逻辑
├── templates/                 # HTML模板
│   └── index.html            # 主页模板
├── uploads/                   # 上传文件目录
├── outputs/                   # 输出文件目录
├── logs/                      # 日志文件目录
├── requirements.txt           # Python依赖
├── docker-compose.yml         # Docker配置
└── README.md                  # 项目说明
```

## 快速开始

### 环境要求
- Python 3.8+
- ComfyUI工作流服务器（`comfyui_workflow_server`，需要先启动）

### 安装依赖
```bash
# 从项目根目录 (witness/) 运行
pip install -r ../requirements.txt
```

### 配置设置
创建 `.env` 文件（可选）：
```env
# 应用配置
APP_NAME=Web Image Transform
APP_VERSION=1.0.0
DEBUG=true

# 服务器配置
HOST=0.0.0.0
PORT=8080

# ComfyUI工作流服务器配置
STYLE_API_BASE_URL=http://localhost:8000

# 文件配置
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
MAX_FILE_SIZE=10485760

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/web_transform.log
```

### 启动服务
```bash
# 在 witness/ 根目录下运行
uvicorn web_image_transform.app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 访问应用
打开浏览器访问：http://localhost:8080

## API接口

### HTTP API

#### 健康检查
```http
GET /api/health
```

#### 文件上传
```http
POST /api/upload
Content-Type: multipart/form-data

file: <image_file>
```

#### 开始变换
```http
POST /api/transform
Content-Type: application/json

{
    "filename": "uploaded_file.jpg",
    "style_type": "clay",
    "custom_prompt": "optional custom prompt",
    "strength": 0.6
}
```

#### 查询任务状态
```http
GET /api/task/{task_id}
```

#### 获取系统统计
```http
GET /api/stats
```

### WebSocket API

连接地址：`ws://localhost:8080/ws`

#### 订阅任务更新
```json
{
    "type": "subscribe",
    "task_id": "task_uuid"
}
```

#### 接收进度更新
```json
{
    "type": "progress",
    "task_id": "task_uuid",
    "progress": 50.0,
    "message": "处理中...",
    "timestamp": 1640995200.0
}
```

## 使用说明

### 基本流程
1. **上传图片**：拖拽或点击上传图像文件
2. **配置参数**：选择风格类型，调整变换强度
3. **开始变换**：点击"开始变换"按钮
4. **查看进度**：实时显示处理进度
5. **查看结果**：对比原图和变换结果
6. **下载结果**：点击下载按钮保存结果

### 高级功能
- **自定义提示词**：输入自定义风格描述
- **历史记录**：查看之前的处理记录
- **系统监控**：查看系统状态和统计信息
- **日志查看**：实时查看系统日志

## 配置说明

### 主要配置项
- `STYLE_API_BASE_URL`：ComfyUI工作流服务器地址
- `MAX_FILE_SIZE`：最大文件上传大小
- `LOG_LEVEL`：日志级别（DEBUG/INFO/WARNING/ERROR）
- `CORS_ORIGINS`：跨域请求允许的源

### 文件存储
- 上传的文件存储在 `uploads/` 目录
- 变换结果存储在 `outputs/` 目录
- 系统会自动清理超过24小时的旧文件

## 开发指南

### 添加新的风格类型
1. 在前端 `templates/index.html` 中添加选项
2. 在后端确保API支持新的风格类型

### 扩展API功能
1. 在 `app/api/web_api.py` 中添加新的路由
2. 在 `app/services/` 中添加相应的服务逻辑

### 自定义前端界面
1. 修改 `app/static/css/style.css` 调整样式
2. 修改 `app/static/js/app.js` 添加新功能
3. 修改 `templates/index.html` 调整布局

## 故障排除

### 常见问题
1. **上传失败**：检查文件大小和格式
2. **变换失败**：确认ComfyUI工作流服务器正常运行
3. **WebSocket连接失败**：检查防火墙和代理设置

### 日志查看
- 控制台日志：实时显示在终端
- 文件日志：存储在 `logs/` 目录
- Web日志：通过界面底部"查看日志"链接

## 部署说明

### Docker部署
```bash
# 构建镜像
docker build -t web-image-transform .

# 运行容器
docker run -p 8080:8080 web-image-transform
```

### 生产环境
1. 设置 `DEBUG=false`
2. 配置适当的 `CORS_ORIGINS`
3. 使用反向代理（如Nginx）
4. 配置SSL证书

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 更新日志

### v1.0.0
- 初始版本发布
- 基本图像变换功能
- WebSocket实时通信
- 完善的日志系统
- 响应式Web界面 