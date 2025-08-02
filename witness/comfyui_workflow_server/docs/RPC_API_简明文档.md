# ComfyUI 工作流服务器 - RPC API 文档

## 概述

ComfyUI 工作流服务器提供基于 JSON-RPC 2.0 协议的统一 API 接口，支持工作流执行、文件管理和系统监控。

**服务地址**: `http://localhost:8000/rpc`  
**协议版本**: JSON-RPC 2.0  
**当前版本**: v2.0.0

---

## 请求格式

```json
{
  "method": "方法名",
  "params": {参数对象},
  "id": "请求ID"
}
```

## 响应格式

**成功响应**:
```json
{
  "result": {返回数据},
  "id": "请求ID"
}
```

**错误响应**:
```json
{
  "error": {
    "code": 错误码(整数),
    "message": "错误描述",
    "data": {错误详情}
  },
  "id": "请求ID"
}
```

---

## API 方法列表

### 工作流管理 (7个方法)

#### 1. `workflow.execute` - 执行工作流

**功能**: 提交工作流执行任务

**输入参数**:
- `request_id` (string, 必需): 唯一请求标识符
- `workflow_id` (string, 必需): 工作流ID
- `params` (object, 必需): 工作流参数
  - `input_image` (string): 输入图像URL或本地路径
  - `[其他参数]` (any): 特定工作流参数，见 `workflow.get_schema`

**输出参数**:
- `request_id` (string): 请求ID
- `workflow_id` (string): 工作流ID
- `status` (string): 任务状态 (`pending`|`processing`|`completed`|`failed`|`cancelled`)
- `progress` (number): 进度 (0.0-1.0)
- `stage` (string): 执行阶段描述
- `message` (string): 状态消息
- `created_at` (integer): 创建时间戳 (秒)
- `estimated_remaining` (integer, 可选): 预计剩余时间 (秒)
- `workflow_info` (object, 可选): 工作流信息

---

#### 2. `workflow.get_status` - 获取任务状态

**功能**: 查询工作流任务状态

**输入参数**:
- `request_id` (string, 必需): 请求ID

**输出参数**:
- `request_id` (string): 请求ID
- `workflow_id` (string): 工作流ID
- `status` (string): 任务状态
- `progress` (number): 进度 (0.0-1.0)
- `stage` (string): 执行阶段
- `message` (string): 状态消息
- `created_at` (integer): 创建时间戳 (秒)
- `started_at` (integer, 可选): 开始时间戳 (秒)
- `completed_at` (integer, 可选): 完成时间戳 (秒)
- `estimated_remaining` (integer, 可选): 预计剩余时间 (秒)
- `workflow_params` (object, 可选): 工作流参数
- `error_message` (string, 可选): 错误消息

---

#### 3. `workflow.get_result` - 获取任务结果

**功能**: 获取已完成任务的结果

**输入参数**:
- `request_id` (string, 必需): 请求ID

**输出参数**:
- `request_id` (string): 请求ID
- `workflow_id` (string): 工作流ID
- `status` (string): 任务状态 (`completed`)
- `duration` (number): 执行耗时 (秒，保留2位小数)
- `completed_at` (integer): 完成时间戳 (秒)
- `workflow_params` (object): 工作流参数
- `output_images` (array): 输出图片列表
  - `filename` (string): 文件名
  - `url` (string): 访问URL
  - `size` (integer): 文件大小 (字节)

---

#### 4. `workflow.cancel` - 取消任务

**功能**: 取消正在执行的任务

**输入参数**:
- `request_id` (string, 必需): 请求ID

**输出参数**:
- `success` (boolean): 是否成功取消
- `request_id` (string): 请求ID
- `message` (string): 操作结果消息

---

#### 5. `workflow.list` - 获取工作流列表

**功能**: 获取所有可用工作流

**输入参数**: 无

**输出参数**:
- `workflows` (array): 工作流列表
  - `workflow_id` (string): 工作流ID
  - `name` (string): 工作流名称
  - `description` (string): 描述
  - `estimated_time` (integer): 预计执行时间 (秒)
  - `tags` (array): 标签列表
  - `version` (string): 版本号
  - `parameter_count` (integer): 参数数量
- `total_count` (integer): 总数量

---

#### 6. `workflow.get_schema` - 获取工作流参数模式

**功能**: 获取工作流参数定义

**输入参数**:
- `workflow_id` (string, 必需): 工作流ID

**输出参数**:
- `workflow_id` (string): 工作流ID
- `name` (string): 工作流名称
- `description` (string): 描述
- `parameters` (object): 参数定义
  - `[参数名]` (object): 参数信息
    - `type` (string): 参数类型 (`string`|`number`|`integer`|`boolean`|`file`)
    - `required` (boolean): 是否必需
    - `default` (any, 可选): 默认值
    - `description` (string, 可选): 参数描述
    - `enum` (array, 可选): 枚举值
    - `min` (number, 可选): 最小值
    - `max` (number, 可选): 最大值

---

#### 7. `workflow.search` - 搜索工作流

**功能**: 根据关键词搜索工作流

**输入参数**:
- `query` (string, 可选): 搜索关键词，为空时返回所有

**输出参数**:
- `workflows` (array): 搜索结果 (同 `workflow.list`)
- `total_count` (integer): 结果数量
- `query` (string): 搜索关键词

---

### 文件管理 (3个方法)

#### 8. `files.get_output_image` - 获取输出图片

**功能**: 获取生成的图片文件 (base64编码)

**支持格式**: .png, .jpg, .jpeg, .webp, .gif, .bmp

**输入参数**:
- `filename` (string, 必需): 图片文件名

**输出参数**:
- `filename` (string): 文件名
- `media_type` (string): MIME类型
- `size` (integer): 文件大小 (字节)
- `data` (string): base64编码的图片数据
- `url` (string): 相对访问URL
- `static_url` (string): 静态文件URL

---

#### 9. `files.get_output_image_info` - 获取图片信息

**功能**: 获取图片文件的元数据

**输入参数**:
- `filename` (string, 必需): 图片文件名

**输出参数**:
- `filename` (string): 文件名
- `size` (integer): 文件大小 (字节)
- `created_time` (integer): 创建时间戳 (秒)
- `modified_time` (integer): 修改时间戳 (秒)
- `extension` (string): 文件扩展名
- `media_type` (string): MIME类型
- `is_image` (boolean): 是否为图片
- `url` (string): 访问URL
- `static_url` (string): 静态文件URL

---

#### 10. `files.list_output_images` - 列出输出图片

**功能**: 获取输出目录中的图片文件列表

**输入参数**:
- `limit` (integer, 可选): 返回数量限制 (1-1000，默认100)
- `offset` (integer, 可选): 偏移量 (默认0)
- `pattern` (string, 可选): 文件名过滤模式 (glob语法，默认"*")

**输出参数**:
- `files` (array): 文件列表
  - `filename` (string): 文件名
  - `size` (integer): 文件大小 (字节)
  - `created_time` (integer): 创建时间戳 (秒)
  - `modified_time` (integer): 修改时间戳 (秒)
  - `extension` (string): 文件扩展名
  - `url` (string): 访问URL
  - `static_url` (string): 静态文件URL
- `total` (integer): 匹配的总文件数
- `limit` (integer): 实际使用的限制数
- `offset` (integer): 实际使用的偏移量
- `pattern` (string): 实际使用的过滤模式
- `has_more` (boolean): 是否还有更多文件

---

### 系统管理 (3个方法)

#### 11. `system.health` - 系统健康检查

**功能**: 检查系统各组件健康状态

**输入参数**: 无

**输出参数**:
- `status` (string): 系统状态 (`healthy`|`unhealthy`)
- `timestamp` (integer): 检查时间戳 (秒)
- `services` (object): 服务状态
  - `comfyui` (string): ComfyUI状态 (`healthy`|`unhealthy`)
  - `storage` (string): 存储状态 (`healthy`|`unhealthy`)
  - `workflows` (string): 工作流状态 (`healthy`|`unhealthy`)
- `details` (object): 详细信息
  - `comfyui_connected` (boolean): ComfyUI是否连接
  - `storage_healthy` (boolean): 存储是否健康
  - `workflows_count` (integer): 工作流数量
  - `environment` (string): 运行环境
  - `version` (string): 版本号

---

#### 12. `system.get_stats` - 获取系统统计

**功能**: 获取系统运行统计信息

**输入参数**: 无

**输出参数**:
- `timestamp` (integer): 统计时间戳 (秒)
- `uptime` (integer): 系统运行时间 (秒)
- `tasks` (object): 任务统计
  - `total` (integer): 总任务数
  - `by_status` (object): 按状态分组 `{status: count}`
  - `by_user` (object): 按用户分组 `{user: count}`
- `files` (object): 文件统计
  - `inputs` (integer): 输入文件数
  - `outputs` (integer): 输出文件数
  - `temp` (integer): 临时文件数
- `workflows` (object): 工作流统计
  - `total` (integer): 工作流总数
  - `available` (array): 可用工作流ID列表

---

#### 13. `system.parse_filename` - 解析文件名

**功能**: 解析标准格式的文件名

**文件名格式**: `{workflow_id}_{request_id}_{type}.{ext}`

**输入参数**:
- `filename` (string, 必需): 要解析的文件名

**输出参数** (成功时):
- `filename` (string): 原文件名
- `valid` (boolean): true
- `components` (object): 解析结果
  - `workflow_id` (string): 工作流ID
  - `request_id` (string): 请求ID
  - `type` (string): 文件类型 (`input`|`output`)
  - `extension` (string): 文件扩展名

**输出参数** (失败时):
- `filename` (string): 原文件名
- `valid` (boolean): false
- `error` (string): 错误描述
- `expected_pattern` (string): 预期格式
- `example` (string): 示例文件名

---

## WebSocket 实时推送

**连接地址**: `ws://localhost:8000/ws/{client_id}`

### 消息格式

```json
{
  "type": "消息类型",
  "request_id": "相关请求ID",
  "data": {消息数据},
  "timestamp": 时间戳
}
```

### 消息类型

#### `workflow_update` - 工作流状态更新
- `data`: 与 `workflow.get_status` 相同的数据结构

#### `task_completed` - 任务完成
- `data`: 与 `workflow.get_result` 相同的数据结构

#### `task_failed` - 任务失败
- `data`: 包含错误信息的任务状态

#### `task_cancelled` - 任务取消
- `data`: 包含取消信息的任务状态

---

## 错误码说明

| 错误码 | 分类 | 描述 |
|--------|------|------|
| 1001 | 参数错误 | 参数格式或类型错误 |
| 1002 | 参数错误 | 请求ID无效 |
| 1003 | 方法错误 | RPC方法不存在 |
| 1004 | 内部错误 | 服务器内部错误 |
| 2001-2007 | 文件错误 | 文件操作相关错误 |
| 3001-3007 | 工作流错误 | 工作流执行相关错误 |
| 9001-9003 | 系统错误 | 系统级错误 |

---

## 数据类型说明

- **string**: 字符串
- **integer**: 整数
- **number**: 数字 (整数或小数)
- **boolean**: 布尔值 (true/false)
- **array**: 数组
- **object**: 对象
- **时间戳**: Unix时间戳，精确到秒
- **进度**: 0.0-1.0 之间的小数
- **文件大小**: 字节为单位的整数
- **执行时间**: 秒为单位，保留2位小数

---

## 快速开始

1. **健康检查**:
   ```json
   {"method": "system.health", "params": {}, "id": "1"}
   ```

2. **获取工作流列表**:
   ```json
   {"method": "workflow.list", "params": {}, "id": "2"}
   ```

3. **执行工作流**:
   ```json
   {
     "method": "workflow.execute",
     "params": {
       "request_id": "req_123",
       "workflow_id": "anime_style_transform",
       "params": {"input_image": "https://example.com/image.jpg"}
     },
     "id": "3"
   }
   ```

4. **获取结果**:
   ```json
   {"method": "workflow.get_result", "params": {"request_id": "req_123"}, "id": "4"}
   ```