# 图片下载和保存功能实现总结

## 实现目标

实现 `comfyui_workflow_server` 从 ComfyUI 服务器获取生成的图片，并以标准命名保存到自己的输出目录，然后提供访问接口。

## 实现的功能

### 1. 工作流后处理增强 (`universal_style_transform.py`)

**修改的方法：**
- `post_process()`: 增加了图片下载和保存逻辑

**新增的方法：**
- `_download_and_save_image()`: 从ComfyUI下载图片并保存到本地
- `_get_server_base_url()`: 获取当前服务器的基础URL

**实现逻辑：**
```python
# 1. 获取ComfyUI生成的临时文件名 (如: ComfyUI_temp_dtdkb_00002_.png)
comfyui_filename = image_info.get("filename", "")

# 2. 获取期望的标准文件名 (如: clay_style_alice_req123_output.png)
expected_filename = getattr(self, 'expected_output_filename', None)

# 3. 从ComfyUI下载图片
comfyui_url = f"{self.comfyui_service.client.base_url}/view?filename={comfyui_filename}&type=output"

# 4. 保存到本地outputs目录
target_path = output_dir / expected_filename

# 5. 生成本地访问URL
local_url = f"{self._get_server_base_url()}/outputs/{expected_filename}"
```

### 2. 转换任务服务增强 (`transform_task_service.py`)

**修改的方法：**
- 在工作流执行前设置 `expected_output_filename` 属性

**实现逻辑：**
```python
# 设置期望的输出文件名到工作流实例
workflow.expected_output_filename = task_data.output_filename
```

### 3. 静态文件服务 (`main.py`)

**新增功能：**
- 挂载 `/outputs` 目录为静态文件服务
- 注册文件访问API路由

**实现逻辑：**
```python
# 确保输出目录存在
outputs_dir = "outputs"
os.makedirs(outputs_dir, exist_ok=True)

# 挂载静态文件服务
app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")

# 注册API路由
app.include_router(files_router)
```

### 4. 文件访问API (`api/files.py`)

**新增端点：**
- `GET /api/files/output/{filename}`: 获取输出图片
- `GET /api/files/output/{filename}/info`: 获取图片信息

**功能特性：**
- 文件类型验证
- MIME类型自动识别
- 缓存控制头
- 错误处理

## 数据流程

### 原来的流程：
```
ComfyUI生成图片 → 返回ComfyUI URL → 前端直接访问ComfyUI
```

### 现在的流程：
```
1. ComfyUI生成图片: ComfyUI_temp_dtdkb_00002_.png
2. comfyui_workflow_server下载: 从 http://127.0.0.1:8188/view?filename=ComfyUI_temp_dtdkb_00002_.png
3. 保存到本地: outputs/clay_style_alice_req123_output.png
4. 返回本地URL: http://127.0.0.1:8000/outputs/clay_style_alice_req123_output.png
5. web_image_transform访问: http://127.0.0.1:8000/outputs/clay_style_alice_req123_output.png
```

## 文件命名规范

### 输入文件：
```
{style_id}_{user_id}_{request_id}_input.{ext}
例如: clay_style_alice_req123_input.jpg
```

### 输出文件：
```
{style_id}_{user_id}_{request_id}_output.{ext}
例如: clay_style_alice_req123_output.png
```

## 访问方式

### 1. 静态文件访问：
```
http://127.0.0.1:8000/outputs/clay_style_alice_req123_output.png
```

### 2. API访问：
```
http://127.0.0.1:8000/api/files/output/clay_style_alice_req123_output.png
```

### 3. 文件信息：
```
http://127.0.0.1:8000/api/files/output/clay_style_alice_req123_output.png/info
```

## 错误处理

### 1. 下载失败处理：
- 如果从ComfyUI下载失败，会回退到原始ComfyUI URL
- 记录详细的错误日志

### 2. 文件访问错误：
- 404: 文件不存在
- 400: 不支持的文件类型
- 500: 服务器内部错误

## 配置要求

### 1. 目录权限：
- `outputs/` 目录需要写权限

### 2. 依赖包：
- `aiofiles`: 异步文件操作
- `aiohttp`: HTTP客户端（已有）
- `fastapi.staticfiles`: 静态文件服务（已有）

## 测试验证

创建了 `test_image_download.py` 测试脚本，包含：
1. 图片下载和保存功能测试
2. URL生成功能测试

## 优势

1. **网络隔离**: web_image_transform 不需要直接访问 ComfyUI
2. **文件管理**: 统一的文件命名和存储
3. **访问控制**: 可以在文件访问层添加权限控制
4. **缓存优化**: 本地文件访问更快
5. **错误恢复**: 下载失败时有备用方案

## 注意事项

1. **存储空间**: 需要考虑本地存储空间的管理
2. **清理策略**: 可能需要定期清理旧文件
3. **并发处理**: 多个任务同时下载时的资源管理
4. **网络超时**: 从ComfyUI下载大文件时的超时处理

## 后续优化建议

1. **文件清理**: 添加定期清理旧文件的任务
2. **压缩优化**: 对大图片进行压缩
3. **缓存策略**: 添加更智能的缓存控制
4. **监控指标**: 添加下载成功率、文件大小等监控
5. **批量下载**: 支持批量下载多个文件