# ComfyUI 图生图 Web 应用

这是一个基于Flask和ComfyUI API的图生图Web应用，用户可以上传图片并使用AI技术生成新的艺术作品。

## 功能特性

- 🖼️ **图片上传**: 支持拖拽上传和点击选择
- 🎨 **AI图像生成**: 基于ComfyUI的FLUX模型和ControlNet
- 📊 **实时进度**: WebSocket实时显示生成进度
- 💾 **结果下载**: 支持生成图片的下载
- 📱 **响应式设计**: 适配移动端和桌面端

## 技术栈

- **后端**: Flask + Flask-SocketIO
- **前端**: HTML5 + CSS3 + JavaScript
- **AI模型**: ComfyUI + FLUX.1-dev + ControlNet-Union-Pro
- **通信**: WebSocket + REST API

## 安装说明

### 1. 环境要求

- Python 3.8+
- ComfyUI已正确安装并运行
- 所需的AI模型文件

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 确保ComfyUI运行

确保ComfyUI在默认端口8188上运行：

```bash
cd /path/to/ComfyUI
python main.py --listen 0.0.0.0 --port 8188
```

### 4. 运行应用

```bash
python app.py
```

访问 `http://localhost:6002` 即可使用应用。

## 使用方法

### 1. 上传图片
- 点击上传区域选择图片
- 或直接拖拽图片到上传区域
- 支持JPG、PNG、GIF格式

### 2. 设置参数
- **正面提示词**: 描述希望生成的图像特征（可选）
- 系统会使用Florence2模型自动分析上传的图片

### 3. 生成图片
- 点击"开始生成"按钮
- 实时查看生成进度
- 完成后可预览和下载结果

## 工作流说明

本应用使用的工作流(`final.json`)包含以下组件：

- **LoadImage**: 加载用户上传的图片
- **Florence2Image2Prompt**: 自动分析图片并生成描述
- **ControlNet**: 使用FLUX.1-dev-ControlNet-Union-Pro进行图像控制
- **LineArtPreprocessor**: 线条艺术预处理
- **KSampler**: 使用Euler采样器进行图像生成
- **VAE**: 变分自编码器进行编码解码

## 配置选项

### 修改ComfyUI服务器地址

在`app.py`中修改：

```python
comfy_api = ComfyUIAPI("your-comfyui-server:8188")
```

### 自定义工作流

替换`myapp/final.json`文件为您自己的工作流JSON。

### 修改生成参数

在`modify_workflow`函数中可以调整：
- 采样步数
- CFG值
- 种子值
- 降噪强度等

## 目录结构

```
project/
├── app.py                 # 主应用文件
├── requirements.txt       # 依赖包
├── README.md             # 说明文档
├── templates/
│   └── index.html        # 前端页面
├── myapp/
│   └── final.json        # ComfyUI工作流
├── uploads/              # 上传文件目录
└── outputs/              # 生成结果目录
```

## 注意事项

1. **模型文件**: 确保ComfyUI中已安装所需的模型文件：
   - `flux1-dev.safetensors`
   - `FLUX.1-dev-ControlNet-Union-Pro-2.0.safetensors`
   - `ae.sft` (VAE模型)

2. **内存要求**: FLUX模型对显存要求较高，建议使用12GB+显存的GPU

3. **网络连接**: 确保Web应用能够访问ComfyUI服务器

4. **文件权限**: 确保应用有权限在uploads和outputs目录中读写文件

## 故障排除

### ComfyUI连接失败
- 检查ComfyUI是否在8188端口运行
- 确认防火墙设置允许连接

### 模型加载错误
- 确认模型文件路径正确
- 检查模型文件是否完整下载

### WebSocket连接问题
- 检查浏览器是否支持WebSocket
- 确认没有代理阻止WebSocket连接

## 许可证

本项目基于MIT许可证开源。

## 贡献

欢迎提交Issue和Pull Request来改进本项目。

---

*基于ComfyUI API开发的图生图Web应用*