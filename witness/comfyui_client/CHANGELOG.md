# ComfyUI 客户端更新日志

## [2.1.0] - 2024-01-XX - 稳定性与可靠性大幅提升

### 🔧 重大修复
- **用户数据上传功能修复**: 修复了`upload_userdata_file`方法中数据没有正确传递给HTTP请求的严重问题
- **类型安全修复**: 修复了所有类型提示问题，确保代码的类型安全性和IDE支持

### 🚀 新增功能

#### 📋 配置管理系统
- **ComfyUIClientConfig**: 新增全面的客户端配置类
  - 支持3种预设配置：`default`（默认）、`fast`（快速）、`robust`（健壮）
  - 网络配置：请求超时、连接超时、读取超时
  - 重试配置：最大重试次数、重试间隔、指数退避
  - 连接池配置：最大连接数、每主机连接数
  - WebSocket配置：连接超时、心跳间隔、调试模式
  - 文件配置：最大文件大小、上传块大小
  - 日志配置：日志级别、请求/响应日志

#### 🛡️ 自定义异常系统
- **ComfyUIClientError**: 基础异常类，提供详细的错误上下文
- **ComfyUIConnectionError**: 连接相关错误（服务器不可达、网络问题）
- **ComfyUIAPIError**: API请求相关错误（HTTP状态码、响应错误）
- **ComfyUIValidationError**: 参数验证错误（类型检查、值范围）
- **ComfyUITimeoutError**: 请求超时错误（连接超时、读取超时）
- **ComfyUIWebSocketError**: WebSocket相关错误（连接失败、消息错误）
- **ComfyUIFileError**: 文件操作相关错误（上传失败、文件不存在）

#### 🔄 智能重试机制
- **指数退避重试**: 支持可配置的重试策略
- **智能重试决策**: 只对适当的错误类型进行重试（如5xx服务器错误）
- **详细重试日志**: 记录重试过程和失败原因

#### ✅ 输入验证系统
- **字符串验证**: 必需/可选字符串的验证和清理
- **数字验证**: 正整数/非负整数的范围检查
- **字节数据验证**: 数据类型和大小限制检查
- **文件路径验证**: 路径格式和存在性检查
- **模型类型验证**: 支持的模型类型白名单验证
- **字典数据验证**: 必需键和数据结构检查
- **URL格式验证**: URL格式的正则表达式验证

### 🏎️ 性能优化

#### 🔗 连接管理优化
- **连接池管理**: 支持可配置的连接池大小和复用
- **超时控制**: 细粒度的超时控制（连接、读取、总超时）
- **资源清理**: 正确的连接器和会话清理，避免资源泄漏

#### 📊 WebSocket优化
- **可配置调试模式**: 避免生产环境中的性能影响
- **类型安全**: 完整的类型提示支持

### 📚 示例和文档

#### 💡 新增示例
- **robust_client_example.py**: 展示所有新功能的完整示例
  - 配置管理示例
  - 错误处理示例
  - 重试机制示例
  - 输入验证示例
  - 超时处理示例

#### 📖 配置示例
```python
# 创建健壮配置（适用于不稳定网络）
robust_config = ComfyUIClientConfig.create_robust()
client = ComfyUIClient(config=robust_config)

# 自定义配置
custom_config = ComfyUIClientConfig(
    request_timeout=45.0,
    max_retries=3,
    retry_delay=1.5,
    max_file_size=100 * 1024 * 1024,  # 100MB
    log_requests=True
)
```

### 🔄 向后兼容性
- **100% 向后兼容**: 所有现有代码无需修改即可使用新功能
- **默认配置**: 提供合理的默认配置，确保现有代码正常工作
- **渐进升级**: 可以逐步采用新功能，无需一次性重写

### 🐛 错误处理改进
- **详细错误信息**: 所有异常都包含详细的上下文信息
- **结构化错误数据**: 异常对象包含结构化的错误详情
- **调试友好**: 提供清晰的错误追踪和调试信息

---

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