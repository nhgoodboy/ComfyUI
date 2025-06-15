# 网页版图像风格变换测试平台

一个基于FastAPI和现代Web技术构建的图像风格变换测试平台，提供简洁的用户界面和完善的API接口。

## 功能特性

### 🎨 核心功能
- **图像上传**：支持拖拽上传，多种图像格式（JPG、PNG、WebP）
- **风格变换**：多种预设风格（粘土、动漫、写实、卡通、油画）
- **自定义提示词**：支持用户自定义风格描述
- **实时进度**：WebSocket实时显示处理进度
- **结果对比**：原图与变换结果并排显示
- **历史记录**：本地存储处理历史

### 🛠️ 技术特性
- **模块化架构**：清晰的代码结构，易于扩展
- **完善日志系统**：多级日志记录，支持文件轮转
- **异步处理**：高性能异步I/O操作
- **WebSocket通信**：实时双向通信
- **响应式设计**：适配各种屏幕尺寸
- **错误处理**：完善的异常处理机制

### 📊 管理功能
- **系统监控**：实时系统状态和统计信息
- **文件管理**：自动文件清理和存储管理
- **API健康检查**：监控后端API服务状态
- **日志查看**：Web界面查看系统日志

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
- 图像风格变换API服务（需要先启动）

### 安装依赖
```bash
cd witness/web_image_transform
pip install -r requirements.txt
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

# 风格变换API配置
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
# 开发模式
python -m app.main

# 或使用uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
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
- `STYLE_API_BASE_URL`：风格变换API服务地址
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
2. **变换失败**：确认风格变换API服务正常运行
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