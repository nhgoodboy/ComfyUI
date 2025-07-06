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

**这种架构确保了敏感的API密钥永远不会暴露在前端代码中，提供了强大的安全性。**

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

在项目根目录下，复制环境配置模板文件：

```bash
cp .env.example .env
```

然后，编辑 `.env` 文件，填入你的配置。这是运行所必须的最简配置：

```env
# 主服务器的完整基础URL
COMFYUI_WORKFLOW_SERVER_URL="http://127.0.0.1:8000"

# 用于访问主服务器的API Key
API_KEY="your-main-server-api-key"

# 用于HMAC请求签名的API Secret Key
API_SECRET_KEY="your-main-server-api-secret-key"

# 用于保护Web应用自身会话(Session)的密钥
SESSION_SECRET_KEY="generate-a-random-secret-key-here"

# (可选) Web应用自身配置
APP_HOST="0.0.0.0"
APP_PORT=8080
LOG_LEVEL="INFO"
DEBUG=false
```
**重要**: 请务必生成一个随机的 `SESSION_SECRET_KEY` 以确保会话安全。

### 4. 运行

```bash
python run.py
```

`run.py` 脚本会自动加载 `.env` 文件中的配置，并启动Web服务器。服务器启动后，在浏览器中打开 `http://127.0.0.1:8080` (或您配置的地址)即可开始使用。

## 工作流程

1.  用户打开网页，浏览器与`web_image_transform`后端建立会话(Session)，并获得唯一的会话ID。
2.  前端通过WebSocket连接到后端，并向后端请求可用风格列表。
3.  后端为当前会话向主服务器请求该用户的JWT令牌。
4.  后端使用JWT令牌从主服务器获取风格列表，并返回给前端。
5.  用户上传图片并选择风格，点击"开始转换"。
6.  请求被发送到`web_image_transform`后端。
7.  后端执行完整的安全认证流程（签名、添加令牌），并将转换请求发送到主服务器。
8.  主服务器接受任务并返回任务ID。
9.  主服务器处理任务时，会通过`web_image_transform`后端的WebSocket连接，将任务进度实时推送给前端。
10. 任务完成后，结果图片URL被推送到前端并显示。

## 项目结构

```
witness/web_image_transform/
├── app/                        # 应用核心代码
│   ├── __init__.py
│   ├── main.py                 # FastAPI主应用
│   ├── config.py               # 配置管理
│   ├── api/                    # API路由
│   │   ├── __init__.py
│   │   └── transform_api.py    # 主路由和WebSocket处理
│   ├── client/                 # 与主服务器通信的客户端
│   │   └── comfyui_client.py   # 封装了请求签名和认证逻辑
│   ├── services/               # 业务服务
│   │   ├── __init__.py
│   │   └── transform_service.py# 图像变换核心服务
│   └── static/                 # 静态文件 (CSS, JS)
├── templates/                  # HTML模板
│   └── index.html              # 主页模板
├── .env.example                # 环境变量示例文件
├── requirements.txt            # Python依赖
├── run.py                      # 应用启动脚本
└── README.md                   # 项目说明
```

## API接口

### HTTP API

#### `GET /`
- **描述**: 渲染应用主页。
- **响应**: `HTMLResponse`

#### `GET /api/styles`
- **描述**: 获取所有可用的图像变换风格列表。此请求会触发后端为当前会e话获取JWT令牌。
- **响应**: `JSONResponse` - 包含风格列表的JSON数组。

#### `POST /api/transform`
- **描述**: 提交一个图像变换任务。
- **请求体**: `multipart/form-data`
    - `style_id: str`: 所选风格的ID。
    - `client_id: str`: 当前WebSocket客户端的唯一ID。
    - `image: UploadFile`: 用户上传的图像文件。
- **响应**: `JSONResponse` - 包含成功信息和任务ID。

### WebSocket API

#### `ws /ws/{client_id}`
- **描述**: 建立一个WebSocket连接以接收实时的任务进度更新。`client_id` 是由前端生成的一个唯一标识符。
- **通信流程**:
    1. 前端建立连接。
    2. 后端将此连接与`client_id`关联并管理。
    3. 当有对应`client_id`的任务更新时（例如，进度、成功、失败、结果URL），后端会主动向客户端推送消息。
    4. 客户端只需监听消息，无需主动发送。

## 部署说明

### Docker部署
```bash
# 构建镜像
docker build -t web-image-transform .

# 运行容器
docker run -p 8080:8080 --env-file .env web-image-transform
```

### 生产环境
1. 在 `.env` 文件中设置 `DEBUG=false`。
2. 使用Gunicorn等生产级服务器替换Uvicorn开发服务器。
3. 考虑使用Nginx等反向代理来处理SSL和静态文件。

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