# ComfyUI 工作流服务器 - RPC API 接入文档

## 📋 目录

- [1. 概述](#1-概述)
- [2. 快速开始](#2-快速开始)
- [3. JSON-RPC 2.0 协议](#3-json-rpc-20-协议)
- [4. 认证与安全](#4-认证与安全)
- [5. API 方法详解](#5-api-方法详解)
- [6. WebSocket 实时推送](#6-websocket-实时推送)
- [7. 错误处理](#7-错误处理)
- [8. SDK 和示例](#8-sdk-和示例)
- [9. 最佳实践](#9-最佳实践)
- [10. 故障排除](#10-故障排除)

## 1. 概述

ComfyUI 工作流服务器提供基于 JSON-RPC 2.0 协议的统一 API 接口，支持：

- 🔗 **统一协议**: 基于 JSON-RPC 2.0 标准
- ⚡ **异步执行**: 支持长时间运行的工作流任务
- 📡 **实时推送**: WebSocket 状态更新和结果通知
- 🎯 **工作流管理**: 执行、监控、取消工作流任务
- 📁 **文件操作**: 上传、下载、管理生成的图片
- 🛡️ **错误处理**: 详细的错误码和异常信息

### 系统架构

```
┌─────────────┐   HTTP POST    ┌──────────────────┐   WebSocket   ┌─────────────┐
│   客户端    │ ──────────────► │   RPC API 服务   │ ◄──────────── │ 实时推送    │
│ (Web/App)   │   /rpc 端点    │   (FastAPI)      │    状态更新    │  监听器     │
└─────────────┘                └────────┬─────────┘                └─────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │   ComfyUI       │
                               │   工作流引擎    │
                               └─────────────────┘
```

## 2. 快速开始

### 2.1 基础连接测试

```bash
# 健康检查
curl -X POST http://localhost:8000/rpc \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"method\": \"system.health\",
    \"params\": {},
    \"id\": \"health_check\"
  }'
```

### 2.2 获取可用工作流

```bash
curl -X POST http://localhost:8000/rpc \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"method\": \"workflow.list\",
    \"params\": {},
    \"id\": \"list_workflows\"
  }'
```

### 2.3 执行简单工作流

```bash
curl -X POST http://localhost:8000/rpc \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"method\": \"workflow.execute\",
    \"params\": {
      \"request_id\": \"demo_001\",
      \"workflow_id\": \"anime_style_transform\",
      \"params\": {
        \"input_image\": \"https://example.com/input.jpg\"
      }
    },
    \"id\": \"execute_demo\"
  }'
```

## 3. JSON-RPC 2.0 协议

### 3.1 请求格式

```typescript
interface RPCRequest {
  method: string;           // RPC 方法名
  params?: object;          // 方法参数 (可选)
  id: string | number;      // 请求唯一标识
}
```

**示例：**
```json
{
  \"method\": \"workflow.execute\",
  \"params\": {
    \"request_id\": \"req_123456789\",
    \"workflow_id\": \"clay_style_transform\",
    \"params\": {
      \"input_image\": \"https://example.com/input.jpg\",
      \"prompt\": \"Clay Style, lovely, cute\",
      \"guidance\": 12
    }
  },
  \"id\": \"unique_request_id\"
}
```

### 3.2 响应格式

**成功响应：**
```typescript
interface RPCResponse {
  result: any;             // 方法返回结果
  id: string | number;     // 对应请求的ID
}
```

**错误响应：**
```typescript
interface RPCError {
  error: {
    code: number;          // 错误码
    message: string;       // 错误消息
    data?: any;           // 错误详细信息
  };
  id: string | number;     // 对应请求的ID
}
```

### 3.3 批量请求

支持在单个 HTTP 请求中发送多个 RPC 调用：

```json
{
  \"requests\": [
    {
      \"method\": \"workflow.get_status\",
      \"params\": {\"request_id\": \"req_001\"},
      \"id\": \"status_1\"
    },
    {
      \"method\": \"workflow.get_status\",
      \"params\": {\"request_id\": \"req_002\"},
      \"id\": \"status_2\"
    }
  ]
}
```

## 4. 认证与安全

### 4.1 请求头设置

```http
POST /rpc HTTP/1.1
Host: localhost:8000
Content-Type: application/json
User-Agent: YourApp/1.0
```

### 4.2 CORS 支持

服务器支持跨域请求，但建议生产环境配置具体的允许域名：

```bash
# 在 .env 文件中配置
CORS_ORIGINS=https://your-frontend.com,https://admin.your-company.com
```

### 4.3 安全建议

- ✅ 使用 HTTPS 协议（生产环境）
- ✅ 实施请求频率限制
- ✅ 验证文件 URL 的合法性
- ✅ 设置合理的文件大小限制

## 5. API 方法详解

### 5.1 工作流管理 API

#### `workflow.execute` - 执行工作流

**功能**: 提交工作流执行任务

**参数**:
```typescript
{
  request_id: string;        // 请求唯一标识符 (必需)
  workflow_id: string;       // 工作流ID (必需)
  params: {                  // 工作流参数 (必需)
    input_image: string;     // 输入图像URL
    prompt?: string;         // 提示词
    guidance?: number;       // 引导强度
    [key: string]: any;      // 其他工作流特定参数
  }
}
```

**返回值**:
```typescript
{
  request_id: string;
  workflow_id: string;
  status: \"pending\" | \"processing\" | \"completed\" | \"failed\" | \"cancelled\";
  progress: number;          // 0.0-1.0
  stage: string;            // 执行阶段
  message: string;
  created_at: number;       // 创建时间戳
  estimated_remaining?: number;  // 预计剩余时间(秒)
  workflow_info?: {
    workflow_id: string;
    name: string;
    description: string;
    estimated_time: number;
  }
}
```

**示例**:
```javascript
// JavaScript 调用示例
const response = await fetch('http://localhost:8000/rpc', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    method: 'workflow.execute',
    params: {
      request_id: 'my_transform_001',
      workflow_id: 'anime_style_transform',
      params: {
        input_image: 'https://example.com/input.jpg',
        prompt: 'anime style, beautiful girl',
        guidance: 7.5
      }
    },
    id: 'exec_001'
  })
});

const result = await response.json();
console.log('任务已创建:', result.result.request_id);
```

---

#### `workflow.get_status` - 获取任务状态

**功能**: 查询工作流任务的当前状态

**参数**:
```typescript
{
  request_id: string;        // 请求唯一标识符
}
```

**返回值**:
```typescript
{
  request_id: string;
  workflow_id: string;
  status: \"pending\" | \"processing\" | \"completed\" | \"failed\" | \"cancelled\";
  progress: number;          // 0.0-1.0
  stage: string;
  message: string;
  created_at: number;
  started_at?: number;
  completed_at?: number;
  estimated_remaining?: number;
  workflow_params?: object;
  error_message?: string;
}
```

**示例**:
```python
# Python 调用示例
import requests

def get_task_status(request_id):
    response = requests.post('http://localhost:8000/rpc', json={
        'method': 'workflow.get_status',
        'params': {'request_id': request_id},
        'id': 'status_check'
    })
    
    result = response.json()
    if 'error' in result:
        print(f\"错误: {result['error']['message']}\")
        return None
    
    return result['result']

status = get_task_status('my_transform_001')
print(f\"状态: {status['status']}, 进度: {status['progress']:.1%}\")
```

---

#### `workflow.get_result` - 获取任务结果

**功能**: 获取已完成任务的结果和输出文件

**参数**:
```typescript
{
  request_id: string;
}
```

**返回值**:
```typescript
{
  request_id: string;
  workflow_id: string;
  status: \"completed\";
  duration: number;          // 执行耗时(秒)
  completed_at: number;
  workflow_params: object;
  output_images: Array<{
    filename: string;
    url: string;            // 可访问的图片URL
    size: number;           // 文件大小(字节)
  }>;
}
```

---

#### `workflow.cancel` - 取消任务

**功能**: 取消正在执行或等待中的任务

**参数**:
```typescript
{
  request_id: string;
}
```

**返回值**:
```typescript
{
  success: boolean;
  request_id: string;
  message: string;
}
```

---

#### `workflow.list` - 获取工作流列表

**功能**: 获取所有可用的工作流及其信息

**参数**: 无

**返回值**:
```typescript
{
  workflows: Array<{
    workflow_id: string;
    name: string;
    description: string;
    estimated_time: number;  // 预计执行时间(秒)
    tags: string[];
    version: string;
    parameter_count: number;
  }>;
  total_count: number;
}
```

---

#### `workflow.get_schema` - 获取工作流参数模式

**功能**: 获取指定工作流的参数定义和验证规则

**参数**:
```typescript
{
  workflow_id: string;
}
```

**返回值**:
```typescript
{
  workflow_id: string;
  name: string;
  description: string;
  parameters: {
    [param_name: string]: {
      type: string;          // 参数类型
      required: boolean;     // 是否必需
      default?: any;         // 默认值
      description?: string;  // 参数描述
      enum?: any[];         // 枚举值
      min?: number;         // 最小值
      max?: number;         // 最大值
    }
  }
}
```

**示例**:
```javascript
// 获取工作流参数模式
const schemaResponse = await fetch('http://localhost:8000/rpc', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    method: 'workflow.get_schema',
    params: { workflow_id: 'anime_style_transform' },
    id: 'get_schema'
  })
});

const schema = await schemaResponse.json();
const parameters = schema.result.parameters;

// 动态生成表单
Object.keys(parameters).forEach(paramName => {
  const param = parameters[paramName];
  console.log(`${paramName}: ${param.type} (required: ${param.required})`);
  if (param.description) {
    console.log(`  描述: ${param.description}`);
  }
  if (param.default !== undefined) {
    console.log(`  默认值: ${param.default}`);
  }
});
```

---

#### `workflow.search` - 搜索工作流

**功能**: 根据关键词搜索可用的工作流

**参数**:
```typescript
{
  query?: string;           // 搜索关键词 (可选)
}
```

**返回值**:
```typescript
{
  workflows: Array<{
    workflow_id: string;
    name: string;
    description: string;
    estimated_time: number;
    tags: string[];
    version: string;
  }>;
  total_count: number;
  query: string;
}
```

### 5.2 文件管理 API

#### `files.get_output_image` - 获取输出图片

**功能**: 获取生成的图片文件（base64编码）

**参数**:
```typescript
{
  filename: string;         // 图片文件名
}
```

**返回值**:
```typescript
{
  filename: string;
  media_type: string;       // MIME类型
  size: number;             // 文件大小
  data: string;             // base64编码的图片数据
  url: string;              // 直接访问URL
  static_url: string;       // 静态文件URL
}
```

**示例**:
```python
import base64
import requests

def download_image(filename, save_path):
    response = requests.post('http://localhost:8000/rpc', json={
        'method': 'files.get_output_image',
        'params': {'filename': filename},
        'id': 'download_img'
    })
    
    result = response.json()
    if 'error' in result:
        print(f\"下载失败: {result['error']['message']}\")
        return False
    
    # 解码并保存图片
    img_data = base64.b64decode(result['result']['data'])
    with open(save_path, 'wb') as f:
        f.write(img_data)
    
    print(f\"图片已保存至: {save_path}\")
    return True

# 使用示例
download_image('anime_style_transform_001_output.png', './output.png')
```

---

#### `files.get_output_image_info` - 获取图片信息

**功能**: 获取图片文件的元数据信息

**参数**:
```typescript
{
  filename: string;
}
```

**返回值**:
```typescript
{
  filename: string;
  size: number;
  created_time: number;     // 创建时间戳
  modified_time: number;    // 修改时间戳
  extension: string;        // 文件扩展名
  media_type: string;
  is_image: boolean;
  url: string;
  static_url: string;
}
```

---

#### `files.list_output_images` - 列出输出图片

**功能**: 获取输出目录中的图片文件列表

**参数**:
```typescript
{
  limit?: number;           // 返回数量限制 (1-1000, 默认100)
  offset?: number;          // 偏移量 (默认0)
  pattern?: string;         // 文件名过滤模式 (默认\"*\")
}
```

**返回值**:
```typescript
{
  files: Array<{
    filename: string;
    size: number;
    created_time: number;
    modified_time: number;
    extension: string;
    url: string;
    static_url: string;
  }>;
  total: number;            // 总文件数
  limit: number;
  offset: number;
  pattern: string;
  has_more: boolean;        // 是否还有更多文件
}
```

**示例**:
```javascript
// 分页获取输出图片列表
async function getOutputImages(page = 0, pageSize = 10) {
  const response = await fetch('http://localhost:8000/rpc', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      method: 'files.list_output_images',
      params: {
        limit: pageSize,
        offset: page * pageSize,
        pattern: '*.png'  // 只获取PNG文件
      },
      id: 'list_images'
    })
  });
  
  const result = await response.json();
  return result.result;
}

// 使用示例
const images = await getOutputImages(0, 20);
console.log(`找到 ${images.total} 个图片，当前显示 ${images.files.length} 个`);

images.files.forEach(file => {
  console.log(`${file.filename} - ${(file.size / 1024).toFixed(1)}KB`);
});
```

### 5.3 系统管理 API

#### `system.health` - 系统健康检查

**功能**: 检查系统各组件的健康状态

**参数**: 无

**返回值**:
```typescript
{
  status: \"healthy\" | \"unhealthy\";
  timestamp: number;
  services: {
    comfyui: \"healthy\" | \"unhealthy\";
    storage: \"healthy\" | \"unhealthy\";
    workflows: \"healthy\" | \"unhealthy\";
  };
  details: {
    comfyui_connected: boolean;
    storage_healthy: boolean;
    workflows_count: number;
    environment: string;
    version: string;
  }
}
```

---

#### `system.get_stats` - 获取系统统计

**功能**: 获取系统运行统计信息

**参数**: 无

**返回值**:
```typescript
{
  timestamp: number;
  uptime: number;           // 系统运行时间(秒)
  tasks: {
    total: number;
    by_status: {[status: string]: number};
    by_user: {[user: string]: number};
  };
  files: {
    inputs: number;         // 输入文件数
    outputs: number;        // 输出文件数
    temp: number;          // 临时文件数
  };
  workflows: {
    total: number;
    available: string[];
  }
}
```

---

#### `system.parse_filename` - 解析文件名

**功能**: 解析标准格式的文件名

**参数**:
```typescript
{
  filename: string;
}
```

**返回值**:
```typescript
{
  filename: string;
  valid: boolean;           // 是否符合标准格式
  components?: {            // 文件名组件 (valid=true时)
    workflow_id: string;
    request_id: string;
    type: \"input\" | \"output\";
    extension: string;
  };
  error?: string;           // 错误信息 (valid=false时)
  expected_pattern?: string;
  example?: string;
}
```

**文件名格式**: `{workflow_id}_{request_id}_{type}.{ext}`

**示例**: `anime_style_transform_req123456_output.png`

## 6. WebSocket 实时推送

### 6.1 连接建立

WebSocket 端点: `ws://host:port/ws/{client_id}`

**连接模式**:
- **请求级连接**: 使用 `request_id` 作为 `client_id`，只接收特定任务的更新
- **服务级连接**: 使用固定服务ID（如 `workflow_test_system`），接收所有任务更新

### 6.2 消息格式

所有 WebSocket 消息都采用以下格式：

```typescript
interface WebSocketMessage {
  type: string;             // 消息类型
  request_id?: string;      // 相关的请求ID
  data: any;               // 消息数据
  timestamp?: number;       // 时间戳
}
```

### 6.3 消息类型

#### `workflow_update` - 工作流状态更新

```json
{
  \"type\": \"workflow_update\",
  \"request_id\": \"req_123456789\",
  \"data\": {
    \"request_id\": \"req_123456789\",
    \"workflow_id\": \"anime_style_transform\",
    \"status\": \"processing\",
    \"progress\": 0.35,
    \"stage\": \"workflow_execution\",
    \"message\": \"正在处理图像变换...\",
    \"estimated_remaining\": 45
  }
}
```

#### `task_completed` - 任务完成通知

```json
{
  \"type\": \"task_completed\",
  \"request_id\": \"req_123456789\",
  \"data\": {
    \"request_id\": \"req_123456789\",
    \"workflow_id\": \"anime_style_transform\",
    \"status\": \"completed\",
    \"duration\": 120,
    \"output_images\": [
      {
        \"filename\": \"anime_style_transform_req123456789_output.png\",
        \"url\": \"/outputs/anime_style_transform_req123456789_output.png\",
        \"size\": 2048576
      }
    ]
  }
}
```

#### `task_failed` - 任务失败通知

```json
{
  \"type\": \"task_failed\",
  \"request_id\": \"req_123456789\",
  \"data\": {
    \"request_id\": \"req_123456789\",
    \"workflow_id\": \"anime_style_transform\",
    \"status\": \"failed\",
    \"error_message\": \"ComfyUI连接超时\",
    \"error_code\": 3002
  }
}
```

### 6.4 客户端实现示例

#### JavaScript/Browser

```javascript
class WorkflowWebSocketClient {
  constructor(baseUrl, clientId) {
    this.baseUrl = baseUrl.replace('http', 'ws');
    this.clientId = clientId;
    this.ws = null;
    this.listeners = {};
  }
  
  connect() {
    const wsUrl = `${this.baseUrl}/ws/${this.clientId}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket连接已建立');
      this.emit('connected');
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket连接已关闭');
      this.emit('disconnected');
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      this.emit('error', error);
    };
  }
  
  handleMessage(message) {
    console.log('收到消息:', message);
    
    switch (message.type) {
      case 'workflow_update':
        this.emit('statusUpdate', message.request_id, message.data);
        break;
      case 'task_completed':
        this.emit('taskCompleted', message.request_id, message.data);
        break;
      case 'task_failed':
        this.emit('taskFailed', message.request_id, message.data);
        break;
      case 'task_cancelled': 
        this.emit('taskCancelled', message.request_id, message.data);
        break;
    }
  }
  
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }
  
  emit(event, ...args) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(...args));
    }
  }
  
  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// 使用示例
const wsClient = new WorkflowWebSocketClient('ws://localhost:8000', 'web_client_01');

wsClient.on('statusUpdate', (requestId, data) => {
  console.log(`任务 ${requestId} 状态更新:`, data);
  updateProgressBar(requestId, data.progress);
  updateStatusText(requestId, data.message);
});

wsClient.on('taskCompleted', (requestId, data) => {
  console.log(`任务 ${requestId} 已完成:`, data);
  displayResults(requestId, data.output_images);
});

wsClient.on('taskFailed', (requestId, data) => {
  console.error(`任务 ${requestId} 失败:`, data.error_message);
  showErrorMessage(requestId, data.error_message);
});

wsClient.connect();
```

#### Python

```python
import asyncio
import websockets
import json

class WorkflowWebSocketClient:
    def __init__(self, base_url, client_id):
        self.base_url = base_url.replace('http', 'ws')
        self.client_id = client_id
        self.ws = None
        self.listeners = {}
    
    async def connect(self):
        ws_url = f\"{self.base_url}/ws/{self.client_id}\"
        print(f\"连接到: {ws_url}\")
        
        try:
            self.ws = await websockets.connect(ws_url)
            print(\"WebSocket连接已建立\")
            
            # 启动消息监听
            await self.listen()
            
        except Exception as e:
            print(f\"连接失败: {e}\")
    
    async def listen(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print(\"WebSocket连接已关闭\")
        except Exception as e:
            print(f\"监听错误: {e}\")
    
    async def handle_message(self, message):
        message_type = message.get('type')
        request_id = message.get('request_id')
        data = message.get('data', {})
        
        print(f\"收到消息: {message_type} - {request_id}\")
        
        if message_type == 'workflow_update':
            await self.emit('status_update', request_id, data)
        elif message_type == 'task_completed':
            await self.emit('task_completed', request_id, data)
        elif message_type == 'task_failed':
            await self.emit('task_failed', request_id, data)
    
    def on(self, event, callback):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)
    
    async def emit(self, event, *args):
        if event in self.listeners:
            for callback in self.listeners[event]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)

# 使用示例
async def on_status_update(request_id, data):
    print(f\"任务 {request_id} 进度: {data['progress']:.1%}\")

async def on_task_completed(request_id, data):
    print(f\"任务 {request_id} 已完成，输出文件: {len(data['output_images'])} 个\")

async def main():
    client = WorkflowWebSocketClient('ws://localhost:8000', 'python_client')
    
    client.on('status_update', on_status_update)
    client.on('task_completed', on_task_completed)
    
    await client.connect()

# 运行客户端
asyncio.run(main())
```

### 6.5 心跳和连接管理

WebSocket 连接支持心跳机制：

```javascript
// 发送心跳
ws.send('ping');

// 接收心跳响应  
ws.onmessage = (event) => {
  if (event.data === 'pong') {
    console.log('心跳响应正常');
    return;
  }
  
  // 处理其他消息
  const message = JSON.parse(event.data);
  handleMessage(message);
};

// 定期发送心跳
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send('ping');
  }
}, 30000); // 每30秒发送一次
```

## 7. 错误处理

### 7.1 错误码定义

#### 通用错误 (1001-1099)

| 错误码 | 常量名 | 描述 | 解决方案 |
|--------|--------|------|----------|
| 1001 | INVALID_PARAMS | 参数错误 | 检查参数类型和格式 |
| 1002 | INVALID_REQUEST_ID | 请求ID无效 | 使用有效的请求ID |
| 1003 | METHOD_NOT_FOUND | 方法不存在 | 检查方法名拼写 |
| 1004 | INTERNAL_ERROR | 内部服务器错误 | 联系管理员或查看日志 |

#### 文件相关错误 (2001-2099)

| 错误码 | 常量名 | 描述 | 解决方案 |
|--------|--------|------|----------|
| 2001 | INVALID_FILE_URL | 文件URL无效 | 检查URL格式和可访问性 |
| 2002 | DOWNLOAD_FAILED | 文件下载失败 | 确认文件存在且可下载 |
| 2003 | INVALID_FILE_FORMAT | 文件格式不支持 | 使用支持的图片格式 |
| 2004 | FILE_TOO_LARGE | 文件过大 | 减小文件大小或调整限制 |
| 2005 | DOWNLOAD_TIMEOUT | 下载超时 | 检查网络连接或减小文件大小 |
| 2006 | INVALID_FILENAME_FORMAT | 文件名格式不符合规范 | 使用标准文件名格式 |
| 2007 | NETWORK_ERROR | 网络连接错误 | 检查网络连接 |

#### 工作流相关错误 (3001-3099)

| 错误码 | 常量名 | 描述 | 解决方案 |
|--------|--------|------|----------|
| 3001 | WORKFLOW_NOT_FOUND | 工作流不存在 | 使用 `workflow.list` 获取可用工作流 |
| 3002 | COMFYUI_UNAVAILABLE | ComfyUI服务不可用 | 检查ComfyUI服务状态 |
| 3003 | WORKFLOW_EXECUTION_FAILED | 工作流执行失败 | 检查参数和ComfyUI日志 |
| 3004 | TASK_NOT_FOUND | 任务不存在 | 确认请求ID正确 |
| 3005 | TASK_CANCELLED | 任务已取消 | 任务被用户或系统取消 |
| 3006 | WORKFLOW_ERROR | 工作流执行错误 | 检查工作流配置和参数 |
| 3007 | WORKFLOW_VALIDATION_FAILED | 工作流参数验证失败 | 使用 `workflow.get_schema` 检查参数要求 |

#### 系统错误 (9001-9099)

| 错误码 | 常量名 | 描述 | 解决方案 |
|--------|--------|------|----------|
| 9001 | STORAGE_ERROR | 存储空间错误 | 检查磁盘空间 |
| 9002 | SERVICE_UNAVAILABLE | 服务暂时不可用 | 稍后重试 |
| 9003 | RATE_LIMIT_EXCEEDED | 请求频率限制 | 减少请求频率 |

### 7.2 错误处理最佳实践

#### 统一错误处理函数

```javascript
function handleRPCError(error) {
  const { code, message, data } = error;
  
  switch (code) {
    // 参数错误
    case 1001:
      console.error(`参数错误: ${message}`);
      if (data.field) {
        console.error(`问题字段: ${data.field}, 值: ${data.value}`);
      }
      return { type: 'validation', message, field: data.field };
    
    // 工作流不存在
    case 3001:
      console.error(`工作流不存在: ${data.workflow_id}`);
      return { type: 'not_found', message, workflow_id: data.workflow_id };
    
    // ComfyUI不可用
    case 3002:
      console.error('ComfyUI服务不可用，请稍后重试');
      return { type: 'service_unavailable', message };
    
    // 任务不存在
    case 3004:
      console.error(`任务不存在: ${data.request_id}`);
      return { type: 'not_found', message, request_id: data.request_id };
    
    // 默认处理
    default:
      console.error(`未知错误 (${code}): ${message}`);
      return { type: 'unknown', code, message };
  }
}

// 使用示例
async function callRPC(method, params) {
  try {
    const response = await fetch('http://localhost:8000/rpc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method, params, id: Date.now() })
    });
    
    const result = await response.json();
    
    if (result.error) {
      const errorInfo = handleRPCError(result.error);
      throw new Error(errorInfo.message);
    }
    
    return result.result;
    
  } catch (error) {
    console.error('RPC调用失败:', error);
    throw error;
  }
}
```

#### 重试机制

```python
import time
import random

class RPCClient:
    def __init__(self, base_url, max_retries=3):
        self.base_url = base_url
        self.max_retries = max_retries
    
    def call_with_retry(self, method, params=None):
        \"\"\"带重试机制的RPC调用\"\"\"
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return self.call(method, params)
                
            except Exception as e:
                last_error = e
                
                # 判断是否应该重试
                if not self.should_retry(e):
                    break
                
                if attempt < self.max_retries:
                    # 指数退避
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f\"第 {attempt + 1} 次尝试失败，{delay:.1f}秒后重试...\")
                    time.sleep(delay)
        
        raise last_error
    
    def should_retry(self, error):
        \"\"\"判断错误是否应该重试\"\"\"
        # 解析错误码
        error_code = getattr(error, 'code', None)
        
        # 可重试的错误码
        retryable_codes = [
            1004,  # 内部服务器错误
            3002,  # ComfyUI不可用
            9002,  # 服务暂时不可用
        ]
        
        return error_code in retryable_codes
    
    def call(self, method, params=None):
        # 实际的RPC调用实现
        pass
```

## 8. SDK 和示例

### 8.1 Python SDK

```python
import requests
import websockets
import asyncio
import json
import time
from typing import Dict, Any, Optional, Callable

class ComfyUIWorkflowClient:
    \"\"\"ComfyUI工作流客户端SDK\"\"\"
    
    def __init__(self, base_url: str = \"http://localhost:8000\"):
        self.base_url = base_url.rstrip('/')
        self.rpc_url = f\"{self.base_url}/rpc\"
        self.ws_url = self.base_url.replace('http', 'ws')
        
    def call(self, method: str, params: Optional[Dict] = None, 
             request_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"调用RPC方法\"\"\"
        if request_id is None:
            request_id = f\"req_{int(time.time() * 1000)}\"
        
        payload = {
            \"method\": method,
            \"params\": params or {},
            \"id\": request_id
        }
        
        response = requests.post(self.rpc_url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if \"error\" in result:
            raise WorkflowAPIError(
                result[\"error\"][\"code\"],
                result[\"error\"][\"message\"],
                result[\"error\"].get(\"data\")
            )
        
        return result[\"result\"]
    
    # 工作流方法
    def execute_workflow(self, request_id: str, workflow_id: str, 
                        params: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"执行工作流\"\"\"
        return self.call(\"workflow.execute\", {
            \"request_id\": request_id,
            \"workflow_id\": workflow_id,
            \"params\": params
        })
    
    def get_workflow_status(self, request_id: str) -> Dict[str, Any]:
        \"\"\"获取工作流状态\"\"\"
        return self.call(\"workflow.get_status\", {\"request_id\": request_id})
    
    def get_workflow_result(self, request_id: str) -> Dict[str, Any]:
        \"\"\"获取工作流结果\"\"\"
        return self.call(\"workflow.get_result\", {\"request_id\": request_id})
    
    def cancel_workflow(self, request_id: str) -> Dict[str, Any]:
        \"\"\"取消工作流\"\"\"
        return self.call(\"workflow.cancel\", {\"request_id\": request_id})
    
    def list_workflows(self) -> Dict[str, Any]:
        \"\"\"列出可用工作流\"\"\"
        return self.call(\"workflow.list\")
    
    def get_workflow_schema(self, workflow_id: str) -> Dict[str, Any]:
        \"\"\"获取工作流参数模式\"\"\"
        return self.call(\"workflow.get_schema\", {\"workflow_id\": workflow_id})
    
    # 文件方法
    def get_output_image(self, filename: str) -> Dict[str, Any]:
        \"\"\"获取输出图片\"\"\"
        return self.call(\"files.get_output_image\", {\"filename\": filename})
    
    def list_output_images(self, limit: int = 100, offset: int = 0,
                          pattern: str = \"*\") -> Dict[str, Any]:
        \"\"\"列出输出图片\"\"\"
        return self.call(\"files.list_output_images\", {
            \"limit\": limit,
            \"offset\": offset,
            \"pattern\": pattern
        })
    
    # 系统方法
    def health_check(self) -> Dict[str, Any]:
        \"\"\"健康检查\"\"\"
        return self.call(\"system.health\")
    
    def get_system_stats(self) -> Dict[str, Any]:
        \"\"\"获取系统统计\"\"\"
        return self.call(\"system.get_stats\")
    
    # 高级方法
    def wait_for_completion(self, request_id: str, 
                           callback: Optional[Callable] = None,
                           timeout: int = 300) -> Dict[str, Any]:
        \"\"\"等待任务完成\"\"\"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_workflow_status(request_id)
            
            if callback:
                callback(status)
            
            if status[\"status\"] == \"completed\":
                return self.get_workflow_result(request_id)
            elif status[\"status\"] in [\"failed\", \"cancelled\"]:
                raise WorkflowAPIError(
                    status.get(\"error_code\", 3006),
                    status.get(\"error_message\", f\"任务{status['status']}\")
                )
            
            time.sleep(2)
        
        raise TimeoutError(f\"任务 {request_id} 在 {timeout} 秒内未完成\")
    
    async def listen_updates(self, client_id: str, 
                           message_handler: Callable[[Dict], None]):
        \"\"\"监听WebSocket更新\"\"\"
        ws_url = f\"{self.ws_url}/ws/{client_id}\"
        
        async with websockets.connect(ws_url) as websocket:
            print(f\"WebSocket已连接: {client_id}\")
            
            try:
                async for message in websocket:
                    if message == \"pong\":
                        continue
                    
                    data = json.loads(message)
                    await message_handler(data)
                    
            except websockets.exceptions.ConnectionClosed:
                print(\"WebSocket连接已关闭\")

class WorkflowAPIError(Exception):
    \"\"\"工作流API异常\"\"\"
    
    def __init__(self, code: int, message: str, data: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.data = data or {}
        super().__init__(f\"[{code}] {message}\")

# 使用示例
async def main():
    client = ComfyUIWorkflowClient(\"http://localhost:8000\")
    
    # 健康检查
    health = client.health_check()
    print(f\"系统状态: {health['status']}\")
    
    # 获取可用工作流
    workflows = client.list_workflows()
    print(f\"可用工作流: {len(workflows['workflows'])} 个\")
    
    # 执行工作流
    request_id = \"demo_transform_001\"
    
    try:
        # 启动任务
        task = client.execute_workflow(
            request_id=request_id,
            workflow_id=\"anime_style_transform\",
            params={
                \"input_image\": \"https://example.com/input.jpg\",
                \"prompt\": \"anime style, beautiful girl\"
            }
        )
        
        print(f\"任务已创建: {task['request_id']}\")
        
        # 等待完成（带进度回调）
        def progress_callback(status):
            print(f\"进度: {status['progress']:.1%} - {status['message']}\")
        
        result = client.wait_for_completion(request_id, progress_callback)
        
        print(f\"任务完成! 输出文件: {len(result['output_images'])} 个\")
        for img in result['output_images']:
            print(f\"  - {img['filename']} ({img['size']} bytes)\")
    
    except WorkflowAPIError as e:
        print(f\"工作流执行失败: {e}\")
    except TimeoutError as e:
        print(f\"任务超时: {e}\")

if __name__ == \"__main__\":
    asyncio.run(main())
```

### 8.2 JavaScript/TypeScript SDK

```typescript
// types.ts
export interface RPCRequest {
  method: string;
  params?: Record<string, any>;
  id: string | number;
}

export interface RPCResponse<T = any> {
  result?: T;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
  id: string | number;
}

export interface WorkflowTask {
  request_id: string;
  workflow_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  stage: string;
  message: string;
  created_at: number;
  started_at?: number;
  completed_at?: number;
  estimated_remaining?: number;
  workflow_params?: Record<string, any>;
  error_message?: string;
}

export interface WebSocketMessage {
  type: string;
  request_id?: string;
  data: any;
  timestamp?: number;
}

// client.ts
export class ComfyUIWorkflowClient {
  private baseUrl: string;
  private rpcUrl: string;
  private wsUrl: string;
  
  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl.replace(/\\/$/, '');
    this.rpcUrl = `${this.baseUrl}/rpc`;
    this.wsUrl = this.baseUrl.replace('http', 'ws');
  }
  
  async call<T = any>(
    method: string,
    params?: Record<string, any>,
    requestId?: string
  ): Promise<T> {
    const id = requestId || `req_${Date.now()}`;
    
    const request: RPCRequest = {
      method,
      params: params || {},
      id
    };
    
    const response = await fetch(this.rpcUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result: RPCResponse<T> = await response.json();
    
    if (result.error) {
      throw new WorkflowAPIError(
        result.error.code,
        result.error.message,
        result.error.data
      );
    }
    
    return result.result!;
  }
  
  // 工作流方法
  async executeWorkflow(
    requestId: string,
    workflowId: string,
    params: Record<string, any>
  ): Promise<WorkflowTask> {
    return this.call('workflow.execute', {
      request_id: requestId,
      workflow_id: workflowId,
      params
    });
  }
  
  async getWorkflowStatus(requestId: string): Promise<WorkflowTask> {
    return this.call('workflow.get_status', { request_id: requestId });
  }
  
  async getWorkflowResult(requestId: string): Promise<any> {
    return this.call('workflow.get_result', { request_id: requestId });
  }
  
  async cancelWorkflow(requestId: string): Promise<{ success: boolean; message: string }> {
    return this.call('workflow.cancel', { request_id: requestId });
  }
  
  async listWorkflows(): Promise<any> {
    return this.call('workflow.list');
  }
  
  async getWorkflowSchema(workflowId: string): Promise<any> {
    return this.call('workflow.get_schema', { workflow_id: workflowId });
  }
  
  // 文件方法
  async getOutputImage(filename: string): Promise<any> {
    return this.call('files.get_output_image', { filename });
  }
  
  async listOutputImages(
    limit: number = 100,
    offset: number = 0,
    pattern: string = '*'
  ): Promise<any> {
    return this.call('files.list_output_images', { limit, offset, pattern });
  }
  
  // 系统方法
  async healthCheck(): Promise<any> {
    return this.call('system.health');
  }
  
  async getSystemStats(): Promise<any> {
    return this.call('system.get_stats');
  }
  
  // 高级方法
  async waitForCompletion(
    requestId: string,
    onProgress?: (task: WorkflowTask) => void,
    timeout: number = 300000
  ): Promise<any> {
    const startTime = Date.now();
    
    return new Promise(async (resolve, reject) => {
      const poll = async () => {
        try {
          if (Date.now() - startTime > timeout) {
            reject(new Error(`任务 ${requestId} 在 ${timeout}ms 内未完成`));
            return;
          }
          
          const status = await this.getWorkflowStatus(requestId);
          
          if (onProgress) {
            onProgress(status);
          }
          
          switch (status.status) {
            case 'completed':
              const result = await this.getWorkflowResult(requestId);
              resolve(result);
              return;
            
            case 'failed':
            case 'cancelled':
              reject(new Error(status.error_message || `任务${status.status}`));
              return;
            
            default:
              setTimeout(poll, 2000);
              break;
          }
        } catch (error) {
          reject(error);
        }
      };
      
      poll();
    });
  }
  
  createWebSocketClient(clientId: string): WorkflowWebSocketClient {
    return new WorkflowWebSocketClient(this.wsUrl, clientId);
  }
}

export class WorkflowWebSocketClient {
  private wsUrl: string;
  private clientId: string;
  private ws: WebSocket | null = null;
  private listeners: Record<string, Function[]> = {};
  
  constructor(baseWsUrl: string, clientId: string) {
    this.wsUrl = `${baseWsUrl}/ws/${clientId}`;
    this.clientId = clientId;
  }
  
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.wsUrl);
        
        this.ws.onopen = () => {
          console.log('WebSocket连接已建立');
          this.emit('connected');
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          if (event.data === 'pong') {
            return;
          }
          
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('解析WebSocket消息失败:', error);
          }
        };
        
        this.ws.onclose = () => {
          console.log('WebSocket连接已关闭');
          this.emit('disconnected');
        };
        
        this.ws.onerror = (error) => {
          console.error('WebSocket错误:', error);
          this.emit('error', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }
  
  private handleMessage(message: WebSocketMessage): void {
    console.log('收到WebSocket消息:', message);
    
    const { type, request_id, data } = message;
    
    switch (type) {
      case 'workflow_update':
        this.emit('statusUpdate', request_id, data);
        break;
      case 'task_completed':
        this.emit('taskCompleted', request_id, data);
        break;
      case 'task_failed':
        this.emit('taskFailed', request_id, data);
        break;
      case 'task_cancelled':
        this.emit('taskCancelled', request_id, data);
        break;
      default:
        this.emit('message', message);
        break;
    }
  }
  
  on(event: string, callback: Function): void {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }
  
  off(event: string, callback?: Function): void {
    if (!this.listeners[event]) return;
    
    if (callback) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    } else {
      this.listeners[event] = [];
    }
  }
  
  private emit(event: string, ...args: any[]): void {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(...args));
    }
  }
  
  close(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
  
  sendHeartbeat(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send('ping');
    }
  }
}

export class WorkflowAPIError extends Error {
  public code: number;
  public data?: any;
  
  constructor(code: number, message: string, data?: any) {
    super(`[${code}] ${message}`);
    this.name = 'WorkflowAPIError';
    this.code = code;
    this.data = data;
  }
}

// 使用示例
async function example() {
  const client = new ComfyUIWorkflowClient('http://localhost:8000');
  
  try {
    // 健康检查
    const health = await client.healthCheck();
    console.log('系统状态:', health.status);
    
    // 创建WebSocket连接
    const wsClient = client.createWebSocketClient('web_client_01');
    
    wsClient.on('statusUpdate', (requestId: string, data: any) => {
      console.log(`任务 ${requestId} 进度: ${(data.progress * 100).toFixed(1)}%`);
    });
    
    wsClient.on('taskCompleted', (requestId: string, data: any) => {
      console.log(`任务 ${requestId} 已完成:`, data.output_images);
    });
    
    await wsClient.connect();
    
    // 执行工作流
    const requestId = 'web_demo_001';
    
    const task = await client.executeWorkflow(requestId, 'anime_style_transform', {
      input_image: 'https://example.com/input.jpg',
      prompt: 'anime style, beautiful girl'
    });
    
    console.log('任务已创建:', task.request_id);
    
    // 等待完成
    const result = await client.waitForCompletion(
      requestId,
      (task) => console.log(`进度: ${(task.progress * 100).toFixed(1)}%`)
    );
    
    console.log('任务完成!', result);
    
  } catch (error) {
    if (error instanceof WorkflowAPIError) {
      console.error(`API错误 [${error.code}]:`, error.message);
    } else {
      console.error('未知错误:', error);
    }
  }
}
```

## 9. 最佳实践

### 9.1 任务管理

#### 生成唯一请求ID

```python
import uuid
import time

def generate_request_id(prefix: str = \"req\") -> str:
    \"\"\"生成唯一的请求ID\"\"\"
    timestamp = int(time.time() * 1000)
    unique_id = str(uuid.uuid4())[:8]
    return f\"{prefix}_{timestamp}_{unique_id}\"

# 使用示例
request_id = generate_request_id(\"anime_transform\")
# 输出: anime_transform_1640995200000_a1b2c3d4
```

#### 批量任务管理

```python
class BatchTaskManager:
    def __init__(self, client):
        self.client = client
        self.tasks = {}
    
    def submit_batch(self, workflow_configs):
        \"\"\"批量提交任务\"\"\"
        task_ids = []
        
        for config in workflow_configs:
            request_id = generate_request_id(config['workflow_id'])
            
            try:
                task = self.client.execute_workflow(
                    request_id=request_id,
                    workflow_id=config['workflow_id'],
                    params=config['params']
                )
                
                self.tasks[request_id] = {
                    'config': config,
                    'task': task,
                    'status': 'submitted'
                }
                
                task_ids.append(request_id)
                
            except Exception as e:
                print(f\"提交任务失败 {config['workflow_id']}: {e}\")
        
        return task_ids
    
    def wait_all_complete(self, task_ids, timeout=600):
        \"\"\"等待所有任务完成\"\"\"
        start_time = time.time()
        completed = set()
        failed = set()
        
        while len(completed) + len(failed) < len(task_ids):
            if time.time() - start_time > timeout:
                break
            
            for task_id in task_ids:
                if task_id in completed or task_id in failed:
                    continue
                
                try:
                    status = self.client.get_workflow_status(task_id)
                    
                    if status['status'] == 'completed':
                        completed.add(task_id)
                        self.tasks[task_id]['result'] = self.client.get_workflow_result(task_id)
                        print(f\"任务完成: {task_id}\")
                    
                    elif status['status'] in ['failed', 'cancelled']:
                        failed.add(task_id)
                        self.tasks[task_id]['error'] = status.get('error_message')
                        print(f\"任务失败: {task_id} - {status.get('error_message')}\")
                
                except Exception as e:
                    print(f\"检查任务状态失败 {task_id}: {e}\")
            
            time.sleep(5)
        
        return {
            'completed': list(completed),
            'failed': list(failed),
            'total': len(task_ids)
        }

# 使用示例
batch_configs = [
    {
        'workflow_id': 'anime_style_transform',
        'params': {'input_image': 'https://example.com/img1.jpg'}
    },
    {
        'workflow_id': 'clay_style_transform',
        'params': {'input_image': 'https://example.com/img2.jpg'}
    }
]

manager = BatchTaskManager(client)
task_ids = manager.submit_batch(batch_configs)
results = manager.wait_all_complete(task_ids)

print(f\"批量任务完成: {results['completed']}/{results['total']}\")
```

### 9.2 错误恢复

#### 自动重试机制

```python
import functools
import random
import time

def retry_on_error(max_retries=3, delay=1, backoff=2, 
                  retryable_errors=None):
    \"\"\"重试装饰器\"\"\"
    if retryable_errors is None:
        retryable_errors = [3002, 9002, 1004]  # ComfyUI不可用、服务不可用、内部错误
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                
                except WorkflowAPIError as e:
                    last_exception = e
                    
                    if e.code not in retryable_errors:
                        break  # 不可重试的错误
                    
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt) + random.uniform(0, 1)
                        print(f\"第 {attempt + 1} 次尝试失败 (错误码: {e.code})，{wait_time:.1f}秒后重试...\")
                        time.sleep(wait_time)
                
                except Exception as e:
                    last_exception = e
                    break  # 非API错误不重试
            
            raise last_exception
        
        return wrapper
    return decorator

# 使用示例
@retry_on_error(max_retries=3, delay=2)
def execute_workflow_with_retry(client, request_id, workflow_id, params):
    return client.execute_workflow(request_id, workflow_id, params)
```

### 9.3 性能优化

#### 连接池管理

```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class OptimizedWorkflowClient(ComfyUIWorkflowClient):
    def __init__(self, base_url: str, pool_connections=10, pool_maxsize=10):
        super().__init__(base_url)
        
        # 配置连接池
        self.session = requests.Session()
        
        # 重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        
        self.session.mount(\"http://\", adapter)
        self.session.mount(\"https://\", adapter)
    
    def call(self, method: str, params: Optional[Dict] = None, 
             request_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"使用连接池的RPC调用\"\"\"
        if request_id is None:
            request_id = f\"req_{int(time.time() * 1000)}\"
        
        payload = {
            \"method\": method,
            \"params\": params or {},
            \"id\": request_id
        }
        
        response = self.session.post(self.rpc_url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if \"error\" in result:
            raise WorkflowAPIError(
                result[\"error\"][\"code\"],
                result[\"error\"][\"message\"],
                result[\"error\"].get(\"data\")
            )
        
        return result[\"result\"]
```

#### 异步批量操作

```python
import asyncio
import aiohttp
from typing import List

class AsyncWorkflowClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.rpc_url = f\"{self.base_url}/rpc\"
    
    async def call_async(self, session: aiohttp.ClientSession, 
                        method: str, params: Optional[Dict] = None,
                        request_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"异步RPC调用\"\"\"
        if request_id is None:
            request_id = f\"req_{int(time.time() * 1000)}\"
        
        payload = {
            \"method\": method,
            \"params\": params or {},
            \"id\": request_id
        }
        
        async with session.post(self.rpc_url, json=payload) as response:
            response.raise_for_status()
            result = await response.json()
            
            if \"error\" in result:
                raise WorkflowAPIError(
                    result[\"error\"][\"code\"],
                    result[\"error\"][\"message\"],
                    result[\"error\"].get(\"data\")
                )
            
            return result[\"result\"]
    
    async def batch_execute_workflows(self, workflow_configs: List[Dict]) -> List[Dict]:
        \"\"\"批量异步执行工作流\"\"\"
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for config in workflow_configs:
                request_id = generate_request_id(config['workflow_id'])
                task = self.call_async(
                    session,
                    \"workflow.execute\",
                    {
                        \"request_id\": request_id,
                        \"workflow_id\": config['workflow_id'],
                        \"params\": config['params']
                    }
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

# 使用示例
async def async_batch_example():
    client = AsyncWorkflowClient('http://localhost:8000')
    
    configs = [
        {
            'workflow_id': 'anime_style_transform',
            'params': {'input_image': f'https://example.com/img{i}.jpg'}
        }
        for i in range(10)
    ]
    
    results = await client.batch_execute_workflows(configs)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f\"任务 {i} 失败: {result}\")
        else:
            print(f\"任务 {i} 成功: {result['request_id']}\")

# 运行异步批量任务
asyncio.run(async_batch_example())
```

## 10. 故障排除

### 10.1 常见问题诊断

#### 连接问题

```bash
# 检查服务是否运行
curl -I http://localhost:8000/health

# 检查RPC端点
curl -X POST http://localhost:8000/rpc \\
  -H \"Content-Type: application/json\" \\
  -d '{\"method\":\"system.health\",\"id\":1}'

# 检查WebSocket连接
wscat -c ws://localhost:8000/ws/test_client
```

#### 工作流问题

```python
def diagnose_workflow_issue(client, workflow_id):
    \"\"\"诊断工作流问题\"\"\"
    print(f\"诊断工作流: {workflow_id}\")
    
    # 1. 检查工作流是否存在
    try:
        workflows = client.list_workflows()
        available_workflows = [w['workflow_id'] for w in workflows['workflows']]
        
        if workflow_id not in available_workflows:
            print(f\"❌ 工作流 '{workflow_id}' 不存在\")
            print(f\"可用工作流: {', '.join(available_workflows)}\")
            return False
        else:
            print(f\"✅ 工作流 '{workflow_id}' 存在\")
    
    except Exception as e:
        print(f\"❌ 获取工作流列表失败: {e}\")
        return False
    
    # 2. 检查工作流参数模式
    try:
        schema = client.get_workflow_schema(workflow_id)
        print(f\"✅ 工作流参数模式获取成功\")
        print(f\"必需参数: {[p for p, info in schema['parameters'].items() if info['required']]}\")
    
    except Exception as e:
        print(f\"❌ 获取工作流参数模式失败: {e}\")
        return False
    
    # 3. 检查系统健康状态
    try:
        health = client.health_check()
        print(f\"系统状态: {health['status']}\")
        print(f\"ComfyUI状态: {health['services']['comfyui']}\")
        
        if health['services']['comfyui'] != 'healthy':
            print(\"❌ ComfyUI服务不健康，请检查ComfyUI服务器\")
            return False
    
    except Exception as e:
        print(f\"❌ 健康检查失败: {e}\")
        return False
    
    print(f\"✅ 工作流 '{workflow_id}' 诊断通过\")
    return True

# 使用示例
if not diagnose_workflow_issue(client, 'anime_style_transform'):
    print(\"请修复上述问题后重试\")
```

### 10.2 日志分析

#### 错误日志解析

```python
import re
from datetime import datetime

def parse_error_logs(log_file_path):
    \"\"\"解析错误日志\"\"\"
    error_patterns = {
        'rpc_error': r'RPC错误 \\[(\\d+)\\]: (.+)',
        'workflow_failed': r'工作流执行失败: (.+)',
        'comfyui_error': r'ComfyUI错误: (.+)',
        'file_error': r'文件操作错误: (.+)'
    }
    
    errors = []
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            for error_type, pattern in error_patterns.items():
                match = re.search(pattern, line)
                if match:
                    errors.append({
                        'line': line_num,
                        'type': error_type,
                        'message': match.groups(),
                        'timestamp': extract_timestamp(line)
                    })
    
    return errors

def extract_timestamp(log_line):
    \"\"\"从日志行中提取时间戳\"\"\"
    timestamp_pattern = r'(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})'
    match = re.search(timestamp_pattern, log_line)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
    return None

# 使用示例
errors = parse_error_logs('logs/app.log')
for error in errors[-10:]:  # 显示最近10个错误
    print(f\"[{error['timestamp']}] {error['type']}: {error['message']}\")
```

### 10.3 性能监控

#### 任务执行时间统计

```python
import time
from collections import defaultdict
import statistics

class PerformanceMonitor:
    def __init__(self):
        self.execution_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
    
    def track_execution(self, workflow_id, execution_time, success=True):
        \"\"\"记录执行时间\"\"\"
        self.execution_times[workflow_id].append(execution_time)
        
        if success:
            self.success_counts[workflow_id] += 1
        else:
            self.error_counts[workflow_id] += 1
    
    def get_statistics(self, workflow_id=None):
        \"\"\"获取统计信息\"\"\"
        if workflow_id:
            workflows = [workflow_id]
        else:
            workflows = set(self.execution_times.keys())
        
        stats = {}
        
        for wf_id in workflows:
            times = self.execution_times[wf_id]
            if not times:
                continue
            
            stats[wf_id] = {
                'total_executions': len(times),
                'successful_executions': self.success_counts[wf_id],
                'failed_executions': self.error_counts[wf_id],
                'success_rate': self.success_counts[wf_id] / (self.success_counts[wf_id] + self.error_counts[wf_id]),
                'avg_execution_time': statistics.mean(times),
                'median_execution_time': statistics.median(times),
                'min_execution_time': min(times),
                'max_execution_time': max(times),
                'std_deviation': statistics.stdev(times) if len(times) > 1 else 0
            }
        
        return stats
    
    def print_report(self):
        \"\"\"打印性能报告\"\"\"
        stats = self.get_statistics()
        
        print(\"=== 工作流性能报告 ===\")
        print()
        
        for workflow_id, data in stats.items():
            print(f\"工作流: {workflow_id}\")
            print(f\"  总执行次数: {data['total_executions']}\")
            print(f\"  成功率: {data['success_rate']:.1%}\")
            print(f\"  平均执行时间: {data['avg_execution_time']:.1f}秒\")
            print(f\"  中位数执行时间: {data['median_execution_time']:.1f}秒\")
            print(f\"  最快执行时间: {data['min_execution_time']:.1f}秒\")
            print(f\"  最慢执行时间: {data['max_execution_time']:.1f}秒\")
            print(f\"  标准差: {data['std_deviation']:.1f}秒\")
            print()

# 使用示例
monitor = PerformanceMonitor()

def execute_with_monitoring(client, request_id, workflow_id, params):
    \"\"\"带性能监控的工作流执行\"\"\"
    start_time = time.time()
    
    try:
        # 执行工作流
        task = client.execute_workflow(request_id, workflow_id, params)
        
        # 等待完成
        result = client.wait_for_completion(request_id)
        
        execution_time = time.time() - start_time
        monitor.track_execution(workflow_id, execution_time, success=True)
        
        return result
    
    except Exception as e:
        execution_time = time.time() - start_time
        monitor.track_execution(workflow_id, execution_time, success=False)
        raise

# 执行多个任务并监控
for i in range(10):
    try:
        execute_with_monitoring(
            client,
            f\"perf_test_{i}\",
            \"anime_style_transform\",
            {\"input_image\": f\"https://example.com/img{i}.jpg\"}
        )
    except Exception as e:
        print(f\"任务 {i} 失败: {e}\")

# 打印性能报告
monitor.print_report()
```

---

## 📞 支持与联系

- **文档更新**: 请定期检查最新版本的API文档
- **问题反馈**: 通过GitHub Issues报告API问题
- **技术讨论**: 加入开发者社区讨论
- **商业支持**: 联系技术支持团队

---

**🚀 开始使用ComfyUI工作流服务器API，构建您的AI应用！**