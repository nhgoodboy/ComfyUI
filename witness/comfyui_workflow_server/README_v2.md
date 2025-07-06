# ComfyUI工作流服务器 v2.0

基于ComfyUI的通用工作流执行服务器，支持多种AI图像处理工作流的统一管理和执行。

## 🌟 新架构特性

### 🔧 通用工作流系统
- **可扩展架构**: 支持无限扩展新的工作流类型
- **标准化接口**: 统一的工作流定义和执行框架
- **自动发现**: 动态加载和注册工作流
- **类型安全**: 完整的参数验证和类型检查

### 📦 内置工作流
- **风格变换** (`style_transform`): 图像风格转换
- **更多工作流**: 可轻松添加文本生成图像、图像放大、背景移除等

### 🚀 高级功能
- **异步任务执行**: 非阻塞的工作流处理
- **实时进度监控**: 任务状态和进度追踪
- **资源管理**: 智能的GPU和内存分配
- **错误处理**: 完善的异常处理和恢复机制
- **性能监控**: 详细的系统性能指标

## 📁 新架构目录结构

```
app/
├── core/                    # 核心业务逻辑
│   ├── workflow_registry.py    # 工作流注册中心
│   └── workflow_manager.py     # 工作流管理器
├── workflows/               # 工作流定义
│   ├── base/                   # 基础类和类型
│   │   ├── workflow_base.py    # 工作流基类
│   │   └── parameter_types.py  # 参数类型验证
│   ├── built_in/              # 内置工作流
│   │   └── style_transform.py  # 风格变换工作流
│   └── custom/                # 自定义工作流目录
├── api/                     # API层
│   └── v1/                    # 新版本API
│       └── workflows.py       # 通用工作流API
└── services/               # 服务层
    └── comfyui_service.py     # ComfyUI集成服务
```

## 🔌 API接口

### 工作流管理

```http
# 获取所有工作流
GET /api/v1/workflows/

# 获取工作流元数据
GET /api/v1/workflows/{workflow_id}

# 获取工作流参数Schema
GET /api/v1/workflows/{workflow_id}/schema

# 执行工作流
POST /api/v1/workflows/{workflow_id}/execute
```

### 任务管理

```http
# 获取任务状态
GET /api/v1/workflows/tasks/{task_id}

# 获取任务结果
GET /api/v1/workflows/tasks/{task_id}/result

# 取消任务
DELETE /api/v1/workflows/tasks/{task_id}

# 列出任务
GET /api/v1/workflows/tasks
```

### 系统监控

```http
# 获取统计信息
GET /api/v1/workflows/statistics

# 搜索工作流
POST /api/v1/workflows/search

# 健康检查
GET /health
```

## 💻 使用示例

### 执行风格变换工作流

```python
import aiohttp
import asyncio

async def transform_image():
    async with aiohttp.ClientSession() as session:
        # 1. 执行工作流
        payload = {
            "workflow_id": "style_transform",
            "parameters": {
                "image": "path/to/image.jpg",
                "style_prompt": "油画风格，印象派",
                "strength": 0.7,
                "steps": 25,
                "cfg_scale": 7.5
            }
        }
        
        async with session.post(
            "http://localhost:8000/api/v1/workflows/style_transform/execute",
            json=payload
        ) as response:
            result = await response.json()
            task_id = result["data"]
        
        # 2. 监控任务进度
        while True:
            async with session.get(
                f"http://localhost:8000/api/v1/workflows/tasks/{task_id}"
            ) as response:
                task_data = await response.json()
                status = task_data["data"]["status"]
                progress = task_data["data"]["progress"]
                
                print(f"状态: {status}, 进度: {progress:.1%}")
                
                if status == "completed":
                    # 3. 获取结果
                    async with session.get(
                        f"http://localhost:8000/api/v1/workflows/tasks/{task_id}/result"
                    ) as response:
                        result = await response.json()
                        return result["data"]
                elif status == "failed":
                    break
                
                await asyncio.sleep(2)

# 运行示例
result = asyncio.run(transform_image())
print(f"结果: {result}")
```

### 获取工作流信息

```python
async def explore_workflows():
    async with aiohttp.ClientSession() as session:
        # 获取所有工作流
        async with session.get("http://localhost:8000/api/v1/workflows/") as response:
            workflows = await response.json()
            print(f"可用工作流: {workflows['data']}")
        
        # 获取特定工作流的详细信息
        async with session.get("http://localhost:8000/api/v1/workflows/style_transform") as response:
            metadata = await response.json()
            workflow_info = metadata["data"]
            print(f"工作流名称: {workflow_info['name']}")
            print(f"描述: {workflow_info['description']}")
            print(f"参数: {workflow_info['parameter_schema']}")
```

## 🔧 自定义工作流

### 创建新工作流

1. **继承基类**:

```python
from app.workflows.base import BaseWorkflow, WorkflowMetadata, WorkflowParameter, WorkflowType

class MyCustomWorkflow(BaseWorkflow):
    def get_metadata(self) -> WorkflowMetadata:
        return WorkflowMetadata(
            id="my_custom_workflow",
            name="我的自定义工作流",
            description="这是一个自定义工作流示例",
            version="1.0.0",
            workflow_type=WorkflowType.IMAGE_TO_IMAGE,
            parameters=[
                WorkflowParameter(
                    name="input_image",
                    type="image",
                    required=True,
                    description="输入图像"
                ),
                # 更多参数...
            ]
        )
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # 参数验证逻辑
        return validated_parameters
    
    async def build_workflow(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        # 构建ComfyUI工作流JSON
        return comfyui_workflow
```

2. **放置文件**: 将文件放在 `app/workflows/custom/` 目录下

3. **自动注册**: 服务器启动时会自动发现并注册新工作流

### 工作流最佳实践

- **参数验证**: 使用内置的参数验证器确保输入安全
- **错误处理**: 实现适当的错误处理和恢复机制
- **资源估算**: 提供准确的时间和资源需求估算
- **文档完善**: 提供清晰的参数说明和使用示例

## 🚀 部署和运行

### 环境要求

- Python 3.8+
- ComfyUI 服务器
- GPU（推荐，用于AI模型推理）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

复制并编辑环境配置：

```bash
cp env.example .env
```

关键配置项：
- `COMFYUI_BASE_URL`: ComfyUI服务器地址
- `API_KEY`: API访问密钥
- `MAX_CONCURRENT_TASKS`: 最大并发任务数

### 启动服务

```bash
# 开发环境
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产环境
python start.py
```

### Docker部署

```bash
docker-compose up -d
```

## 📊 监控和管理

### 系统统计

访问 `/api/v1/workflows/statistics` 获取：
- 总任务数和状态分布
- 平均执行时间
- 系统资源使用情况
- 工作流使用统计

### 健康检查

访问 `/health` 获取：
- 服务状态
- ComfyUI连接状态
- 系统资源信息

### API文档

访问 `/docs` 查看完整的API文档和交互界面。

## 🔄 从v1迁移

### 主要变化

1. **API端点变更**:
   - 旧: `POST /transform`
   - 新: `POST /api/v1/workflows/style_transform/execute`

2. **请求格式变更**:
   ```python
   # 旧格式
   {
       "image_url": "...",
       "style_type": "clay",
       "strength": 0.6
   }
   
   # 新格式
   {
       "workflow_id": "style_transform",
       "parameters": {
           "image": "...",
           "style_prompt": "Clay Style, lovely, 3d, cute",
           "strength": 0.6
       }
   }
   ```

3. **响应格式标准化**:
   所有API现在返回统一的格式：
   ```json
   {
       "success": true,
       "data": "...",
       "error_message": null
   }
   ```

### 迁移步骤

1. **更新API端点**: 修改客户端代码使用新的端点
2. **调整请求格式**: 使用新的参数结构
3. **处理响应格式**: 适配新的统一响应格式
4. **测试验证**: 确保所有功能正常工作

## 🤝 贡献指南

1. **添加新工作流**: 在 `app/workflows/custom/` 下创建新文件
2. **改进现有功能**: 提交PR改进核心功能
3. **报告问题**: 使用GitHub Issues报告bug
4. **文档完善**: 帮助改进文档和示例

## 📄 许可证

MIT License

---

## 📞 支持

如有问题，请：
1. 查看文档和示例
2. 检查GitHub Issues
3. 提交新的Issue
4. 联系开发团队

## 🎯 路线图

- [ ] 更多内置工作流（文本生成图像、图像放大等）
- [ ] 工作流可视化编辑器
- [ ] 分布式任务执行
- [ ] 更多AI模型支持
- [ ] 实时WebSocket API
- [ ] 工作流版本管理 