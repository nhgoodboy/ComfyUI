# ComfyUI 客户端更新日志

## [2.0.0] - 2024-12-20

### 新增功能

#### 🎯 模型管理 API
- **ModelAPI** 类新增，提供完整的模型管理功能
  - `get_model_types()` - 获取所有可用模型类型
  - `get_models(folder)` - 获取特定文件夹的模型列表
  - `get_model_metadata(folder_name, filename)` - 获取模型元数据（支持.safetensors文件）

#### 📁 用户数据管理 API
- **UserDataAPI** 类新增，支持完整的用户文件管理
  - `list_userdata()` - 列出用户数据文件（支持递归、详细信息）
  - `list_userdata_v2()` - 新版本的用户数据列表API
  - `get_userdata_file()` - 下载用户数据文件
  - `upload_userdata_file()` - 上传用户数据文件
  - `delete_userdata_file()` - 删除用户数据文件
  - `move_userdata_file()` - 移动/重命名用户数据文件

#### 🔧 内部系统监控 API
- **InternalAPI** 类新增，用于系统调试和监控
  - `get_logs()` - 获取系统日志（文本格式）
  - `get_raw_logs()` - 获取原始日志数据
  - `subscribe_logs()` - 订阅日志更新
  - `get_folder_paths()` - 获取系统文件夹路径配置

### 功能扩展

#### 📋 队列管理增强 (PromptAPI)
- `get_prompt_info()` - 获取当前队列详细信息
- `free_memory()` - 内存管理，支持卸载模型和释放内存
- `clear_history()` - 历史记录清理，支持清空或删除特定记录

#### 📤 文件管理增强 (FileAPI)
- `upload_mask()` - 上传遮罩图像，支持与原图的关联

#### 👤 用户设置增强 (UserAPI)
- `get_setting()` - 获取特定设置项的值
- `update_setting()` - 更新特定设置项的值

### 架构改进

#### 🏗️ 模块化设计
- 所有API按功能分组到独立的模块中
- 统一的基类 `BaseAPI` 确保一致的接口设计
- 完整的类型提示支持

#### 📚 文档和示例
- 新增完整的API参考表格
- 新增 `api_usage_example.py` 展示所有功能
- 更新README文档，包含所有新功能的说明

#### 🔄 向后兼容性
- 保持现有API的完全兼容
- `client.file` 作为 `client.files` 的别名继续支持
- 所有现有代码无需修改即可升级

### API 端点覆盖率

#### ✅ 已实现 (100% 覆盖)
- **队列和工作流**: `/prompt`, `/queue`, `/history`, `/interrupt`, `/free`
- **文件管理**: `/upload/image`, `/upload/mask`, `/view`
- **系统信息**: `/system_stats`, `/object_info`, `/embeddings`, `/extensions`
- **用户管理**: `/users`, `/settings`
- **模型管理**: `/models`, `/view_metadata`
- **用户数据**: `/userdata`, `/v2/userdata`
- **内部API**: `/internal/logs`, `/internal/folder_paths`

### 使用示例

```python
from comfyui_client import ComfyUIClient

async def main():
    client = ComfyUIClient()
    
    # 模型管理
    model_types = await client.models.get_model_types()
    models = await client.models.get_models("checkpoints")
    
    # 用户数据管理
    files = await client.userdata.list_userdata_v2("workflows")
    
    # 内存管理
    await client.prompts.free_memory(unload_models=True)
    
    # 系统监控
    logs = await client.internal.get_raw_logs()
    
    await client.close()
```

### 破坏性变更
- 无破坏性变更，完全向后兼容

### 修复
- 修复了WebSocket客户端的类型提示问题
- 优化了错误处理机制
- 改进了文件上传的稳定性

---

## [1.0.0] - 2024-12-01

### 初始版本
- 基础的ComfyUI API客户端实现
- 支持提示提交、队列管理、文件操作
- WebSocket集成用于实时通信
- 基础的用户和系统API支持 