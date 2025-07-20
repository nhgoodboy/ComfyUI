# ComfyUI Workflow Server RPC API 接入指南

## 📋 目录

- [API 概览](#api-概览)
- [快速开始](#快速开始)
- [RPC方法详解](#rpc方法详解)
  - [风格管理](#风格管理)
  - [转换任务](#转换任务)
  - [系统管理](#系统管理)
- [WebSocket 实时推送](#websocket-实时推送)
- [错误处理](#错误处理)
- [代码示例](#代码示例)
- [最佳实践](#最佳实践)

---

## 🚀 API 概览

ComfyUI Workflow Server 提供了基于JSON-RPC的API接口，专注于AI图像风格转换和工作流管理。

### 基础信息

- **RPC端点**: `POST http://your-domain:8000/rpc`
- **WebSocket**: `ws://your-domain:8000/ws/{user_id}`
- **健康检查**: `GET http://your-domain:8000/health`
- **数据格式**: JSON
- **认证方式**: 无认证（简化微服务）
- **用户隔离**: 基于参数 `user_id`

### 功能特性

- 🎨 **风格管理**: 风格发现、搜索和查询
- 🔄 **一体化转换**: 自动下载图片 + 风格转换
- 📁 **规范化命名**: `{style_id}_{user_id}_{request_id}_{input/output}.{ext}`
- 🔌 **实时推送**: WebSocket 任务状态和进度更新，支持心跳保活
- 📊 **精确进度跟踪**: 直接反映ComfyUI采样进度，过滤无关步骤
- 📈 **多阶段监控**: 下载阶段 + 转换阶段完整生命周期
- 🔍 **端到端追踪**: request_id支持完整请求链路追踪
- 🎯 **智能结果处理**: 自动获取ComfyUI历史记录和生成文件
- ⚡ **批量支持**: 支持批量RPC请求

### 🏗️ 文件命名规范

#### 输入文件命名
```
{style_id}_{user_id}_{request_id}_input.{ext}
示例: clay_style_alice_req123_input.jpg
     anime_style_bob_req456_input.png
```

#### 输出文件命名
```
{style_id}_{user_id}_{request_id}_output.{ext} 
示例: clay_style_alice_req123_output.png
     anime_style_bob_req456_output.jpg
```

#### 处理流程
1. 外部服务器按规范命名上传图片
2. 提供图片URL给RPC接口
3. 系统自动下载、验证命名、执行转换
4. 返回转换结果和输出文件访问地址

---

## ⚡ 快速开始

### 1. RPC请求格式

```json
{
  "method": "方法名",
  "params": {
    "参数名": "参数值"
  },
  "id": "请求ID"
}
```

### 2. 基础请求示例

```bash
# 获取所有风格
curl -X POST "http://your-domain:8000/rpc" \
     -H "Content-Type: application/json" \
     -d '{
       "method": "styles.list",
       "params": {},
       "id": "req_001"
     }'

# 创建转换任务
curl -X POST "http://your-domain:8000/rpc" \
     -H "Content-Type: application/json" \
     -d '{
       "method": "transform.create",
       "params": {
         "user_id": "alice",
         "style_id": "clay_style",
         "image_url": "https://external.com/clay_style_alice_req123_input.jpg",
         "request_id": "req123"
       },
       "id": "req_002"
     }'
```

### 3. 批量请求示例

```json
[
  {
    "method": "styles.list",
    "params": {},
    "id": "req_001"
  },
  {
    "method": "transform.create", 
    "params": {
      "user_id": "alice",
      "style_id": "clay_style",
      "image_url": "https://external.com/clay_style_alice_req123_input.jpg",
      "request_id": "req123"
    },
    "id": "req_002"
  }
]
```

### 4. WebSocket连接

```javascript
const ws = new WebSocket('ws://your-domain:8000/ws/alice');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('任务更新:', data);
};
```

---

## 📚 RPC方法详解

### 风格管理

#### styles.list - 获取所有风格

**请求**:
```json
{
  "method": "styles.list",
  "params": {},
  "id": "req_001"
}
```

**响应**:
```json
{
  "result": {
    "styles": [
      {
        "id": "clay_style",
        "name": "黏土风格转换",
        "description": "将输入图像转换为黏土风格，呈现可爱、3D、立体效果",
        "estimated_time": 45,
        "tags": ["黏土风格", "3D效果", "可爱"]
      },
      {
        "id": "anime_style",
        "name": "动漫风格转换", 
        "description": "将输入图像转换为动漫风格，呈现鲜艳色彩和漫画风格",
        "estimated_time": 40,
        "tags": ["动漫风格", "漫画", "动画"]
      }
    ],
    "total": 2
  },
  "id": "req_001"
}
```

#### styles.search - 搜索风格

**请求**:
```json
{
  "method": "styles.search",
  "params": {
    "q": "动漫"
  },
  "id": "req_002"
}
```

**响应**: 与 `styles.list` 相同格式，但只返回匹配的风格

#### styles.get - 获取风格详情

**请求**:
```json
{
  "method": "styles.get", 
  "params": {
    "style_id": "clay_style"
  },
  "id": "req_003"
}
```

**响应**:
```json
{
  "result": {
    "id": "clay_style",
    "name": "黏土风格转换",
    "description": "将输入图像转换为黏土风格，呈现可爱、3D、立体效果", 
    "estimated_time": 45,
    "tags": ["黏土风格", "3D效果", "可爱"]
  },
  "id": "req_003"
}
```

---

### 转换任务

#### transform.create - 创建转换任务

**请求**:
```json
{
  "method": "transform.create",
  "params": {
    "user_id": "alice",
    "style_id": "clay_style", 
    "image_url": "https://external.com/clay_style_alice_req123_input.jpg",
    "request_id": "req123"
  },
  "id": "req_004"
}
```

**响应**:
```json
{
  "result": {
    "request_id": "task_12345",
    "user_id": "alice",
    "style_id": "clay_style",
    "status": "pending",
    "progress": 0.0,
    "stage": "pending",
    "message": "任务已创建，等待开始",
    "created_at": 1640995200.123,
    "estimated_time": 45,
    "file_info": {
      "input_filename": "clay_style_alice_req123_input.jpg",
      "expected_output_filename": "clay_style_alice_req123_output.png"
    }
  },
  "id": "req_004"
}
```

#### transform.get_status - 获取任务状态

**请求**:
```json
{
  "method": "transform.get_status",
  "params": {
    "user_id": "alice",
    "request_id": "task_12345"
  },
  "id": "req_005"
}
```

**响应示例（不同阶段）**:

**下载阶段**:
```json
{
  "result": {
    "request_id": "task_12345",
    "user_id": "alice",
    "style_id": "clay_style", 
    "status": "downloading",
    "progress": 15.0,
    "stage": "download",
    "message": "正在下载图片... 45.2%",
    "created_at": 1640995200.123,
    "started_at": 1640995205.456,
    "file_info": {
      "input_filename": "clay_style_alice_req123_input.jpg",
      "expected_output_filename": "clay_style_alice_req123_output.png"
    }
  },
  "id": "req_005"
}
```

**转换阶段**:
```json
{
  "result": {
    "request_id": "task_12345",
    "user_id": "alice", 
    "style_id": "clay_style",
    "status": "processing",
    "progress": 65.0,
    "stage": "transform", 
    "message": "正在进行风格转换... 步骤 12/25",
    "created_at": 1640995200.123,
    "started_at": 1640995205.456
  },
  "id": "req_005"
}
```

#### transform.get_result - 获取任务结果

**请求**:
```json
{
  "method": "transform.get_result",
  "params": {
    "user_id": "alice",
    "request_id": "task_12345"
  },
  "id": "req_006"
}
```

**响应**:
```json
{
  "result": {
    "request_id": "task_12345",
    "user_id": "alice",
    "style_id": "clay_style",
    "status": "completed",
    "input_info": {
      "filename": "clay_style_alice_req123_input.jpg",
      "path": "/storage/inputs/clay_style_alice_req123_input.jpg",
      "size": 1024000,
      "format": "jpeg",
      "original_url": "https://external.com/clay_style_alice_req123_input.jpg"
    },
    "output_images": [
      {
        "filename": "clay_style_alice_req123_output.png",
        "url": "http://127.0.0.1:8188/view?filename=clay_style_alice_req123_output.png&type=output",
        "size": 2048000
      }
    ],
    "duration": 95.5,
    "completed_at": 1640995295.678
  },
  "id": "req_006"
}
```

#### transform.list - 获取任务列表

**请求**:
```json
{
  "method": "transform.list",
  "params": {
    "user_id": "alice",
    "limit": 50,
    "status_filter": ["completed", "processing"]
  },
  "id": "req_007"
}
```

**响应**:
```json
{
  "result": {
    "user_id": "alice",
    "tasks": [
      {
        "request_id": "task_12345",
        "user_id": "alice",
        "style_id": "clay_style",
        "status": "completed",
        "progress": 100.0,
        "created_at": 1640995200.123,
        "completed_at": 1640995295.678
      }
    ],
    "total": 1,
    "filters": {
      "status_filter": ["completed", "processing"],
      "limit": 50
    }
  },
  "id": "req_007"
}
```

#### transform.cancel - 取消任务

**请求**:
```json
{
  "method": "transform.cancel",
  "params": {
    "user_id": "alice", 
    "request_id": "task_12345"
  },
  "id": "req_008"
}
```

**响应**:
```json
{
  "result": {
    "success": true,
    "request_id": "task_12345", 
    "message": "任务已成功取消"
  },
  "id": "req_008"
}
```

---

### 系统管理

#### system.health - 系统健康检查

**请求**:
```json
{
  "method": "system.health",
  "params": {},
  "id": "req_009"
}
```

**响应**:
```json
{
  "result": {
    "status": "healthy",
    "timestamp": 1640995500.123,
    "services": {
      "comfyui": "healthy",
      "storage": "healthy", 
      "styles": "healthy"
    },
    "details": {
      "comfyui": {
        "connected": true,
        "url": "http://127.0.0.1:8188"
      },
      "storage": {
        "healthy": true,
        "paths": {
          "inputs": "/storage/inputs",
          "outputs": "/storage/outputs",
          "temp": "/storage/temp"
        }
      },
      "styles": {
        "count": 5,
        "healthy": true
      },
      "version": "2.0.0"
    }
  },
  "id": "req_009"
}
```

#### system.build_filename - 构建文件名

**请求**:
```json
{
  "method": "system.build_filename",
  "params": {
    "style_id": "clay_style",
    "user_id": "alice", 
    "request_id": "req123",
    "type": "input",
    "extension": "jpg"
  },
  "id": "req_010"
}
```

**响应**:
```json
{
  "result": {
    "filename": "clay_style_alice_req123_input.jpg",
    "components": {
      "style_id": "clay_style",
      "user_id": "alice",
      "request_id": "req123",
      "type": "input", 
      "extension": "jpg"
    },
    "example_url": "http://your-domain:8000/inputs/clay_style_alice_req123_input.jpg",
    "pattern": "{style_id}_{user_id}_{request_id}_{type}.{ext}"
  },
  "id": "req_010"
}
```

#### system.get_stats - 获取系统统计

**请求**:
```json
{
  "method": "system.get_stats",
  "params": {},
  "id": "req_011"
}
```

**响应**:
```json
{
  "result": {
    "timestamp": 1640995500.123,
    "uptime": 3600.5,
    "tasks": {
      "total": 25,
      "by_status": {
        "completed": 20,
        "processing": 2,
        "pending": 1,
        "failed": 2
      },
      "by_user": {
        "alice": 15,
        "bob": 10
      }
    },
    "files": {
      "inputs": 25,
      "outputs": 20,
      "temp": 2
    },
    "styles": {
      "total": 5,
      "available": ["clay_style", "anime_style", "cartoon_style"]
    }
  },
  "id": "req_011"
}
```

---

## 🔌 WebSocket 实时推送

### 连接地址
```
ws://your-domain:8000/ws/{user_id}
```

### 消息格式

**标准消息结构**:
```json
{
  "type": "task_update",
  "request_id": "task_12345",
  "data": {
    "user_id": "alice",
    "style_id": "clay_style",
    "status": "processing",
    "stage": "transform",
    "progress": 45.6,
    "message": "生成进度: 12/25 (45.6%) - 节点: 73",
    "request_id": "req123",
    "timestamp": 1640995250.123,
    "files": {
      "input": "clay_style_alice_req123_input.jpg",
      "output": "clay_style_alice_req123_output.png"
    }
  }
}
```

**任务完成消息**:
```json
{
  "type": "task_update",
  "request_id": "task_12345", 
  "data": {
    "user_id": "alice",
    "style_id": "clay_style",
    "status": "completed",
    "stage": "completed",
    "progress": 100.0,
    "message": "转换完成",
    "request_id": "req123",
    "timestamp": 1640995350.456,
    "result": {
      "status": "completed",
      "prompt_id": "6bed9e06-f08c-4a7d-b204-4c4f54ea33cb",
      "files": {
        "input": "http://host:port/uploads/input.jpg",
        "output": ["http://127.0.0.1:8188/view?filename=clay_style_alice_req123_output.png"]
      },
      "output_images": [
        {
          "url": "http://127.0.0.1:8188/view?filename=clay_style_alice_req123_output.png"
        }
      ],
      "history": { /* ComfyUI完整历史记录用于调试 */ }
    }
  }
}
```

**心跳消息**:
```
pong
```
*注意：客户端应忽略心跳消息，不尝试JSON解析*

### JavaScript 示例

```javascript
class ComfyUIRPCClient {
    constructor(baseUrl, userId) {
        this.baseUrl = baseUrl;
        this.userId = userId;
        this.requestId = 0;
        this.ws = null;
        this.connectWebSocket();
    }
    
    connectWebSocket() {
        const wsUrl = `ws://${this.baseUrl.replace('http://', '')}/ws/${this.userId}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket连接已建立');
        };
        
        this.ws.onmessage = (event) => {
            // 忽略心跳消息
            if (event.data === 'pong') {
                return;
            }
            
            const data = JSON.parse(event.data);
            if (data.type === 'task_update') {
                this.handleTaskUpdate(data);
            }
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket连接已关闭，3秒后重连...');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };
    }
    
    async callRPC(method, params = {}) {
        const requestId = `req_${++this.requestId}`;
        const payload = {
            method,
            params,
            id: requestId
        };
        
        const response = await fetch(`${this.baseUrl}/rpc`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(`RPC错误 ${result.error.code}: ${result.error.message}`);
        }
        
        return result.result;
    }
    
    async getStyles() {
        return await this.callRPC('styles.list');
    }
    
    async createTransform(styleId, imageUrl, requestId = null) {
        return await this.callRPC('transform.create', {
            user_id: this.userId,
            style_id: styleId,
            image_url: imageUrl,
            request_id: requestId
        });
    }
    
    async getTaskStatus(taskId) {
        return await this.callRPC('transform.get_status', {
            user_id: this.userId,
            request_id: taskId
        });
    }
    
    async getTaskResult(taskId) {
        return await this.callRPC('transform.get_result', {
            user_id: this.userId,
            request_id: taskId
        });
    }
    
    handleTaskUpdate(data) {
        const taskData = data.data;
        console.log(`任务 ${data.request_id}: ${taskData.status} (${taskData.progress}%) - ${taskData.message}`);
        
        if (taskData.status === 'completed') {
            this.handleTaskCompleted(taskData);
        } else if (taskData.status === 'download_failed' || taskData.status === 'processing_failed') {
            this.handleTaskFailed(taskData);
        }
    }
    
    handleTaskCompleted(taskData) {
        if (taskData.result && taskData.result.files && taskData.result.files.output) {
            const outputFiles = taskData.result.files.output;
            console.log('任务完成，输出文件:', outputFiles);
            if (outputFiles.length > 0) {
                this.displayResult(outputFiles[0]);
            }
        } else if (taskData.result && taskData.result.output_images) {
            // 兼容旧格式
            const outputImage = taskData.result.output_images[0];
            console.log('任务完成，输出文件:', outputImage.url);
            this.displayResult(outputImage.url);
        }
    }
    
    handleTaskFailed(data) {
        console.error('任务失败:', data.message);
    }
    
    displayResult(imageUrl) {
        // 显示结果图片
        const img = document.getElementById('result-image');
        if (img) {
            img.src = imageUrl;
        }
    }
}

// 使用示例
const client = new ComfyUIRPCClient('http://localhost:8000', 'alice');

// 获取风格列表
client.getStyles().then(styles => {
    console.log('可用风格:', styles.styles);
});

// 创建转换任务
client.createTransform('clay_style', 'https://external.com/clay_style_alice_req123_input.jpg')
    .then(task => {
        console.log('任务已创建:', task.request_id);
    })
    .catch(error => {
        console.error('创建任务失败:', error);
    });
```

---

## ❌ 错误处理

### 错误响应格式

```json
{
  "error": {
    "code": 错误码,
    "message": "错误描述",
    "data": {
      "详细信息": "可选"
    }
  },
  "id": "请求ID"
}
```

### 错误码参考

| 错误码 | 说明 | 常见原因 |
|--------|------|----------|
| 1001 | 参数错误 | 缺少必需参数或参数格式错误 |
| 1002 | 用户ID无效 | 用户ID为空或格式不正确 |
| 1003 | 方法不存在 | RPC方法名错误 |
| 1004 | 内部错误 | 服务器内部处理异常 |
| **下载相关错误** |
| 2001 | 图片URL无效 | URL格式错误或无法访问 |
| 2002 | 图片下载失败 | 网络错误或服务器返回错误 |
| 2003 | 文件格式不支持 | 文件不是支持的图片格式 |
| 2004 | 文件过大 | 文件超过10MB限制 |
| 2005 | 下载超时 | 下载时间超过30秒 |
| 2006 | 文件名格式不符合规范 | URL中的文件名不符合命名规范 |
| 2007 | 风格参数不匹配 | URL文件名中的风格与请求不一致 |
| 2008 | 用户ID不匹配 | URL文件名中的用户ID与请求不一致 |
| **转换相关错误** |
| 3001 | 风格不存在 | 指定的风格ID不存在 |
| 3002 | ComfyUI服务不可用 | ComfyUI后端服务连接失败 |
| 3003 | 转换处理失败 | 图像转换过程中出现错误 |
| 3004 | 任务不存在 | 指定的任务ID不存在 |
| 3005 | 任务已取消 | 任务已被用户取消 |

### 错误处理示例

```javascript
try {
    const result = await client.createTransform('invalid_style', 'bad_url');
} catch (error) {
    if (error.message.includes('3001')) {
        console.error('风格不存在，请检查风格ID');
    } else if (error.message.includes('2001')) {
        console.error('图片URL无效，请检查URL格式');
    } else {
        console.error('未知错误:', error.message);
    }
}
```

---

## 💻 完整代码示例

### Python 客户端

```python
import asyncio
import aiohttp
import json
import websockets
from typing import Dict, Any, Optional

class ComfyUIRPCClient:
    def __init__(self, base_url: str, user_id: str):
        self.base_url = base_url
        self.user_id = user_id
        self.request_id = 0
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def call_rpc(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用RPC方法"""
        if params is None:
            params = {}
        
        self.request_id += 1
        payload = {
            "method": method,
            "params": params,
            "id": f"req_{self.request_id}"
        }
        
        async with self.session.post(
            f"{self.base_url}/rpc",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            result = await response.json()
            
            if "error" in result:
                raise Exception(f"RPC错误 {result['error']['code']}: {result['error']['message']}")
            
            return result["result"]
    
    async def get_styles(self) -> Dict[str, Any]:
        """获取所有风格"""
        return await self.call_rpc("styles.list")
    
    async def search_styles(self, query: str) -> Dict[str, Any]:
        """搜索风格"""
        return await self.call_rpc("styles.search", {"q": query})
    
    async def create_transform(self, style_id: str, image_url: str) -> Dict[str, Any]:
        """创建转换任务"""
        return await self.call_rpc("transform.create", {
            "user_id": self.user_id,
            "style_id": style_id,
            "image_url": image_url
        })
    
    async def get_task_status(self, request_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        return await self.call_rpc("transform.get_status", {
            "user_id": self.user_id,
            "request_id": request_id
        })
    
    async def get_task_result(self, request_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        return await self.call_rpc("transform.get_result", {
            "user_id": self.user_id,
            "request_id": request_id
        })
    
    async def list_tasks(self, limit: int = 100, status_filter: list = None) -> Dict[str, Any]:
        """获取任务列表"""
        params = {
            "user_id": self.user_id,
            "limit": limit
        }
        if status_filter:
            params["status_filter"] = status_filter
        
        return await self.call_rpc("transform.list", params)
    
    async def cancel_task(self, request_id: str) -> Dict[str, Any]:
        """取消任务"""
        return await self.call_rpc("transform.cancel", {
            "user_id": self.user_id,
            "request_id": request_id
        })
    
    async def build_filename(self, style_id: str, file_type: str = "input", extension: str = "jpg") -> Dict[str, Any]:
        """构建文件名"""
        return await self.call_rpc("system.build_filename", {
            "style_id": style_id,
            "user_id": self.user_id,
            "type": file_type,
            "extension": extension
        })
    
    async def listen_websocket(self, message_handler=None):
        """监听WebSocket消息"""
        ws_url = f"ws://{self.base_url.replace('http://', '')}/ws/{self.user_id}"
        
        async with websockets.connect(ws_url) as websocket:
            print(f"WebSocket连接已建立: {self.user_id}")
            
            try:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    if message_handler:
                        await message_handler(data)
                    else:
                        print(f"任务更新: {data}")
                        
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket连接已关闭")

# 使用示例
async def main():
    async with ComfyUIRPCClient("http://localhost:8000", "alice") as client:
        # 获取风格列表
        styles = await client.get_styles()
        print("可用风格:", [style["id"] for style in styles["styles"]])
        
        # 构建符合规范的文件名
        filename_info = await client.build_filename("clay_style", "input", "jpg")
        print("文件名:", filename_info["filename"])
        print("示例URL:", filename_info["example_url"])
        
        # 创建转换任务
        task = await client.create_transform(
            "clay_style",
            "https://external.com/clay_style_alice_req123_input.jpg"
        )
        print("任务创建:", task["request_id"])
        
        # 定义消息处理器
        async def handle_message(data):
            if data.get('type') == 'task_update':
                task_data = data.get('data', {})
                print(f"任务 {data['request_id']}: {task_data['status']} ({task_data['progress']}%)")
                
                if task_data['status'] == 'completed':
                    # 检查结果数据
                    if 'result' in task_data and task_data['result']:
                        result = task_data['result']
                        if 'files' in result and result['files']['output']:
                            print("任务完成，输出文件:", result['files']['output'])
                        elif 'output_images' in result:
                            print("任务完成，输出文件:", result['output_images'])
                    else:
                        # 如果WebSocket没有结果，主动获取
                        result = await client.get_task_result(data['request_id'])
                        print("任务完成，输出文件:", result["output_images"])
        
        # 启动WebSocket监听（这会一直运行）
        await client.listen_websocket(handle_message)

# 运行示例
if __name__ == "__main__":
    asyncio.run(main())
```

### Node.js 客户端

```javascript
const WebSocket = require('ws');
const fetch = require('node-fetch');

class ComfyUIRPCClient {
    constructor(baseUrl, userId) {
        this.baseUrl = baseUrl;
        this.userId = userId;
        this.requestId = 0;
        this.ws = null;
    }
    
    async callRPC(method, params = {}) {
        const requestId = `req_${++this.requestId}`;
        const payload = {
            method,
            params,
            id: requestId
        };
        
        const response = await fetch(`${this.baseUrl}/rpc`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.error) {
            throw new Error(`RPC错误 ${result.error.code}: ${result.error.message}`);
        }
        
        return result.result;
    }
    
    async getStyles() {
        return await this.callRPC('styles.list');
    }
    
    async createTransform(styleId, imageUrl, requestId = null) {
        return await this.callRPC('transform.create', {
            user_id: this.userId,
            style_id: styleId,
            image_url: imageUrl,
            request_id: requestId
        });
    }
    
    async getTaskStatus(taskId) {
        return await this.callRPC('transform.get_status', {
            user_id: this.userId,
            request_id: taskId
        });
    }
    
    async getTaskResult(taskId) {
        return await this.callRPC('transform.get_result', {
            user_id: this.userId,
            request_id: taskId
        });
    }
    
    connectWebSocket(messageHandler) {
        const wsUrl = `ws://${this.baseUrl.replace('http://', '')}/ws/${this.userId}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.on('open', () => {
            console.log('WebSocket连接已建立');
        });
        
        this.ws.on('message', (data) => {
            // 忽略心跳消息
            if (data === 'pong') {
                return;
            }
            
            const message = JSON.parse(data);
            if (message.type === 'task_update') {
                if (messageHandler) {
                    messageHandler(message);
                } else {
                    console.log('任务更新:', message);
                }
            }
        });
        
        this.ws.on('close', () => {
            console.log('WebSocket连接已关闭，3秒后重连...');
            setTimeout(() => this.connectWebSocket(messageHandler), 3000);
        });
        
        this.ws.on('error', (error) => {
            console.error('WebSocket错误:', error);
        });
        
        return this.ws;
    }
}

// 使用示例
async function main() {
    const client = new ComfyUIRPCClient('http://localhost:8000', 'alice');
    
    try {
        // 获取风格列表
        const styles = await client.getStyles();
        console.log('可用风格:', styles.styles.map(s => s.id));
        
        // 创建转换任务
        const task = await client.createTransform(
            'clay_style',
            'https://external.com/clay_style_alice_req123_input.jpg'
        );
        console.log('任务创建:', task.request_id);
        
        // 监听WebSocket消息
        client.connectWebSocket(async (data) => {
            if (data.type === 'task_update') {
                const taskData = data.data;
                console.log(`任务 ${data.request_id}: ${taskData.status} (${taskData.progress}%)`);
                
                if (taskData.status === 'completed') {
                    // 检查结果数据
                    if (taskData.result && taskData.result.files && taskData.result.files.output) {
                        console.log('任务完成，输出文件:', taskData.result.files.output);
                    } else {
                        // 如果WebSocket没有结果，主动获取
                        const result = await client.getTaskResult(data.request_id);
                        console.log('任务完成，输出文件:', result.output_images);
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('操作失败:', error.message);
    }
}

main();
```

---

## 🚀 最佳实践

### 1. 文件命名规范

**外部服务器文件命名**:
```bash
# 正确的文件命名
clay_style_alice_req123_input.jpg     ✅
anime_style_bob_req456_input.png      ✅
cartoon_style_charlie_req789_input.webp ✅

# 错误的文件命名  
alice_input.jpg                ❌ 缺少风格ID和请求ID
clay_style_input.jpg           ❌ 缺少用户ID和请求ID
clay_style_alice_input.jpg     ❌ 缺少请求ID
random_photo.jpg               ❌ 不符合规范
```

**使用辅助方法**:
```javascript
// 获取标准文件名
const filenameInfo = await client.callRPC('system.build_filename', {
    style_id: 'clay_style',
    user_id: 'alice',
    request_id: 'req123',
    type: 'input',
    extension: 'jpg'
});

console.log('标准文件名:', filenameInfo.filename);
// 输出: clay_style_alice_req123_input.jpg
```

### 2. 错误处理策略

**分类错误处理**:
```javascript
async function handleRPCCall(client, method, params) {
    try {
        return await client.callRPC(method, params);
    } catch (error) {
        const errorCode = parseInt(error.message.match(/\d+/)?.[0] || '0');
        
        if (errorCode >= 2001 && errorCode <= 2099) {
            // 下载相关错误
            console.error('下载失败:', error.message);
            return { error: 'download_failed', details: error.message };
        } else if (errorCode >= 3001 && errorCode <= 3099) {
            // 转换相关错误  
            console.error('转换失败:', error.message);
            return { error: 'transform_failed', details: error.message };
        } else {
            // 其他错误
            console.error('系统错误:', error.message);
            return { error: 'system_error', details: error.message };
        }
    }
}
```

### 3. 任务监控模式

**轮询 + WebSocket组合**:
```javascript
class TaskMonitor {
    constructor(client, taskId) {
        this.client = client;
        this.taskId = taskId;
        this.polling = false;
        this.wsConnected = false;
    }
    
    async startMonitoring() {
        // 启动WebSocket监听
        this.client.connectWebSocket((data) => {
            if (data.type === 'task_update' && data.request_id === this.taskId) {
                this.wsConnected = true;
                this.handleUpdate(data.data);
            }
        });
        
        // 启动轮询作为备用
        setTimeout(() => {
            if (!this.wsConnected) {
                this.startPolling();
            }
        }, 5000);
    }
    
    async startPolling() {
        this.polling = true;
        
        while (this.polling) {
            try {
                const status = await this.client.getTaskStatus(this.taskId);
                this.handleUpdate(status);
                
                if (status.status === 'completed' || status.status.includes('failed')) {
                    this.polling = false;
                }
            } catch (error) {
                console.warn('轮询失败:', error.message);
            }
            
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }
    
    handleUpdate(data) {
        console.log(`任务进度: ${data.progress}% - ${data.message}`);
        
        if (data.status === 'completed') {
            this.onCompleted(data);
        } else if (data.status.includes('failed')) {
            this.onFailed(data);
        }
    }
    
    async onCompleted(data) {
        console.log('任务完成!');
        const result = await this.client.getTaskResult(this.taskId);
        console.log('输出文件:', result.output_images);
    }
    
    onFailed(data) {
        console.error('任务失败:', data.message);
    }
}

// 使用示例
const task = await client.createTransform('clay_style', imageUrl);
const monitor = new TaskMonitor(client, task.request_id);
monitor.startMonitoring();
```

### 4. 批量操作优化

```javascript
// 批量获取多个任务状态
async function batchGetTaskStatus(client, taskIds) {
    const requests = taskIds.map((taskId, index) => ({
        method: 'transform.get_status',
        params: {
            user_id: client.userId,
            request_id: taskId
        },
        id: `batch_${index}`
    }));
    
    const response = await fetch(`${client.baseUrl}/rpc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requests)
    });
    
    const results = await response.json();
    return results.map(r => r.result);
}
```

### 5. 连接管理

```javascript
class ConnectionManager {
    constructor(baseUrl, userId) {
        this.client = new ComfyUIRPCClient(baseUrl, userId);
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }
    
    async ensureConnection() {
        try {
            // 测试连接
            await this.client.callRPC('system.health');
            this.reconnectAttempts = 0;
            return true;
        } catch (error) {
            this.reconnectAttempts++;
            
            if (this.reconnectAttempts <= this.maxReconnectAttempts) {
                console.warn(`连接失败，${3 ** this.reconnectAttempts}秒后重试...`);
                await new Promise(resolve => 
                    setTimeout(resolve, 3000 * this.reconnectAttempts)
                );
                return this.ensureConnection();
            } else {
                throw new Error('连接失败，已达到最大重试次数');
            }
        }
    }
}
```

### 6. 性能优化建议

- **文件预处理**: 上传前适当压缩图片（建议2-5MB）
- **并发控制**: 同时处理的任务不超过5个
- **缓存策略**: 缓存风格列表等静态数据
- **连接复用**: 复用HTTP连接和WebSocket连接
- **错误重试**: 实现指数退避重试机制
- **超时设置**: 为每个请求设置合理的超时时间
- **心跳处理**: 正确过滤WebSocket心跳消息，避免JSON解析错误
- **进度优化**: 只关注多步骤节点的进度，获得平滑的进度体验
- **结果处理**: 优先使用WebSocket推送的结果，必要时主动获取
- **request_id追踪**: 使用request_id进行端到端请求跟踪和调试

---

这份API指南提供了完整的RPC接口使用说明，包括详细的方法文档、错误处理、代码示例和最佳实践，帮助开发者快速集成ComfyUI Workflow Server的RPC服务。