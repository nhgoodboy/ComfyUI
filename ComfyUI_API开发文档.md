# ComfyUI API 开发文档

## 目录
1. [概述](#概述)
2. [API优势](#api优势)
3. [接口详解](#接口详解)
4. [使用指南](#使用指南)
5. [错误处理](#错误处理)
6. [最佳实践](#最佳实践)

## 概述

ComfyUI API 是一套基于REST和WebSocket的图像生成API接口，支持Stable Diffusion模型的各种图像生成任务。与传统的WebUI API相比，ComfyUI API提供了更强大和灵活的功能。

### 基础信息
- **基础URL**: `http://localhost:8188` (默认端口)
- **API版本**: v1
- **支持格式**: JSON
- **通信协议**: HTTP + WebSocket

## API优势

相比WebUI API，ComfyUI API具有以下优势：

1. **自带队列管理** - 无需手动管理任务队列
2. **WebSocket支持** - 实时获取任务进度和状态
3. **插件兼容性** - 所有浏览器可用插件都可通过API调用
4. **开发友好** - 只需关心绘图流程搭建，无需关心底层实现
5. **模型切换简单** - 轻松实现模型切换和进度查询
6. **渐变效果支持** - 支持图片生成时的渐变效果
7. **任务中断** - 支持中断正在进行的绘图任务
8. **无需Base64转换** - 直接处理图片，无需繁琐的编码转换

## 接口详解

### 1. 绘图任务提交

#### 接口信息
- **URL**: `POST /prompt`
- **功能**: 提交绘图任务到队列
- **说明**: 该接口只负责任务下发，返回任务ID，不直接返回结果图片

#### 请求参数

| 参数名 | 类型 | 必选 | 说明 |
|--------|------|------|------|
| client_id | string | 是 | 客户端ID，用于标识任务发起者 |
| prompt | object | 是 | 任务参数JSON对象 |

#### 请求示例
```json
{
    "client_id": "unique-client-id-12345",
    "prompt": {
        "1": {
            "inputs": {
                "ckpt_name": "model.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "2": {
            "inputs": {
                "text": "a beautiful landscape",
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        }
        // ... 更多节点配置
    }
}
```

#### 响应参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| prompt_id | string | 任务唯一标识ID |
| number | integer | 当前任务序号 |
| node_errors | object | 节点错误信息 |

#### 响应示例
```json
{
    "prompt_id": "bd2cfa2c-de87-4258-89cc-d8791bc13a61",
    "number": 501,
    "node_errors": {}
}
```

### 2. WebSocket实时通信

#### 接口信息
- **URL**: `WS /ws?clientId={client_id}`
- **功能**: 实时获取任务进度、状态和结果
- **协议**: WebSocket

#### 连接示例
```javascript
const ws = new WebSocket('ws://localhost:8188/ws?clientId=unique-client-id-12345');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
};
```

#### 消息类型

##### 执行开始消息
```json
{
    "type": "execution_start",
    "data": {
        "prompt_id": "bd2cfa2c-de87-4258-89cc-d8791bc13a61"
    }
}
```

##### 进度更新消息
```json
{
    "type": "progress",
    "data": {
        "value": 5,
        "max": 20,
        "prompt_id": "bd2cfa2c-de87-4258-89cc-d8791bc13a61",
        "node": "3"
    }
}
```

##### 执行完成消息
```json
{
    "type": "executed",
    "data": {
        "node": "9",
        "prompt_id": "bd2cfa2c-de87-4258-89cc-d8791bc13a61",
        "output": {
            "images": [
                {
                    "filename": "ComfyUI_00001_.png",
                    "subfolder": "",
                    "type": "output"
                }
            ]
        }
    }
}
```

### 3. 队列管理

#### 获取队列状态
- **URL**: `GET /queue`
- **功能**: 获取当前队列状态

#### 响应示例
```json
{
    "queue_running": [
        {
            "prompt_id": "current-running-task-id",
            "number": 500
        }
    ],
    "queue_pending": [
        {
            "prompt_id": "pending-task-id-1",
            "number": 501
        },
        {
            "prompt_id": "pending-task-id-2", 
            "number": 502
        }
    ]
}
```

#### 清空队列
- **URL**: `POST /queue`
- **功能**: 清空待处理队列

#### 请求参数
```json
{
    "clear": true
}
```

#### 取消特定任务
- **URL**: `POST /queue`
- **功能**: 取消指定任务

#### 请求参数
```json
{
    "delete": ["prompt_id_to_cancel"]
}
```

### 4. 历史记录

#### 获取历史记录
- **URL**: `GET /history`
- **功能**: 获取任务执行历史

#### 获取特定任务历史
- **URL**: `GET /history/{prompt_id}`
- **功能**: 获取指定任务的执行历史

### 5. 系统信息

#### 获取系统信息
- **URL**: `GET /system_stats`
- **功能**: 获取系统状态信息

#### 响应示例
```json
{
    "system": {
        "os": "linux",
        "python_version": "3.10.0",
        "embedded_python": false
    },
    "devices": [
        {
            "name": "NVIDIA GeForce RTX 4090",
            "type": "cuda",
            "index": 0,
            "vram_total": 25757220864,
            "vram_free": 22928490496
        }
    ]
}
```

### 6. 图片获取

#### 查看生成图片
- **URL**: `GET /view?filename={filename}&subfolder={subfolder}&type={type}`
- **功能**: 获取生成的图片文件

#### 参数说明
- `filename`: 图片文件名
- `subfolder`: 子文件夹路径
- `type`: 文件类型 (output/input/temp)

## 使用指南

### 1. 基本工作流程

1. **生成工作流JSON**: 在ComfyUI界面中设计工作流，点击"Save (API Format)"保存为API格式
2. **修改参数**: 根据需要修改JSON中的参数值
3. **提交任务**: 通过POST /prompt接口提交任务
4. **监听结果**: 通过WebSocket监听任务进度和结果
5. **获取图片**: 任务完成后通过/view接口获取生成的图片

### 2. 常见参数修改

#### 文本提示词
```json
{
    "6": {
        "inputs": {
            "text": "your positive prompt here",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    }
}
```

#### 负面提示词
```json
{
    "7": {
        "inputs": {
            "text": "your negative prompt here", 
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    }
}
```

#### 图片尺寸
```json
{
    "5": {
        "inputs": {
            "width": 768,
            "height": 512,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    }
}
```

#### 采样参数
```json
{
    "3": {
        "inputs": {
            "seed": 123456789,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
    }
}
```

### 3. Python使用示例

```python
import requests
import websocket
import json
import uuid

class ComfyUIAPI:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
    
    def submit_prompt(self, prompt):
        """提交绘图任务"""
        url = f"http://{self.server_address}/prompt"
        data = {
            "client_id": self.client_id,
            "prompt": prompt
        }
        response = requests.post(url, json=data)
        return response.json()
    
    def get_queue_status(self):
        """获取队列状态"""
        url = f"http://{self.server_address}/queue"
        response = requests.get(url)
        return response.json()
    
    def listen_websocket(self, on_message):
        """监听WebSocket消息"""
        ws_url = f"ws://{self.server_address}/ws?clientId={self.client_id}"
        
        def on_ws_message(ws, message):
            data = json.loads(message)
            on_message(data)
        
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_ws_message
        )
        ws.run_forever()
    
    def get_image(self, filename, subfolder="", type="output"):
        """获取生成的图片"""
        url = f"http://{self.server_address}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": type
        }
        response = requests.get(url, params=params)
        return response.content

# 使用示例
api = ComfyUIAPI()

# 提交任务
prompt = {
    # 你的工作流JSON
}
result = api.submit_prompt(prompt)
print(f"任务ID: {result['prompt_id']}")

# 监听结果
def handle_message(data):
    if data['type'] == 'executed':
        print("任务完成!")
        print(data)

api.listen_websocket(handle_message)
```

### 4. JavaScript使用示例

```javascript
class ComfyUIAPI {
    constructor(serverAddress = '127.0.0.1:8188') {
        this.serverAddress = serverAddress;
        this.clientId = this.generateUUID();
    }
    
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
    
    async submitPrompt(prompt) {
        const response = await fetch(`http://${this.serverAddress}/prompt`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                client_id: this.clientId,
                prompt: prompt
            })
        });
        return await response.json();
    }
    
    connectWebSocket(onMessage) {
        const ws = new WebSocket(`ws://${this.serverAddress}/ws?clientId=${this.clientId}`);
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            onMessage(data);
        };
        
        return ws;
    }
    
    async getImage(filename, subfolder = '', type = 'output') {
        const params = new URLSearchParams({
            filename: filename,
            subfolder: subfolder,
            type: type
        });
        
        const response = await fetch(`http://${this.serverAddress}/view?${params}`);
        return await response.blob();
    }
}

// 使用示例
const api = new ComfyUIAPI();

async function generateImage() {
    const prompt = {
        // 你的工作流JSON
    };
    
    // 提交任务
    const result = await api.submitPrompt(prompt);
    console.log('任务ID:', result.prompt_id);
    
    // 监听进度
    const ws = api.connectWebSocket((data) => {
        if (data.type === 'progress') {
            console.log(`进度: ${data.data.value}/${data.data.max}`);
        } else if (data.type === 'executed') {
            console.log('任务完成!', data);
            // 获取生成的图片
            if (data.data.output && data.data.output.images) {
                data.data.output.images.forEach(async (img) => {
                    const blob = await api.getImage(img.filename);
                    // 处理图片blob
                });
            }
        }
    });
}
```

## 错误处理

### 常见错误代码

| 状态码 | 说明 | 解决方案 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查JSON格式和必需参数 |
| 404 | 节点或模型未找到 | 确认模型文件存在，节点类型正确 |
| 500 | 服务器内部错误 | 检查服务器日志，确认资源充足 |

### 节点错误处理

当prompt中包含错误节点时，响应中的`node_errors`字段会包含具体错误信息：

```json
{
    "prompt_id": "xxx",
    "number": 0,
    "node_errors": {
        "1": {
            "errors": [
                {
                    "type": "return_with_leftover_nodes",
                    "message": "模型文件未找到",
                    "details": "无法加载指定的checkpoint文件"
                }
            ],
            "dependent_outputs": ["2", "3"]
        }
    }
}
```

## 最佳实践

### 1. 性能优化

- **批量处理**: 合理设置batch_size以提高GPU利用率
- **队列管理**: 避免提交过多任务导致内存溢出
- **资源监控**: 定期检查系统资源使用情况

### 2. 错误处理

- **重试机制**: 对网络错误实现自动重试
- **超时处理**: 设置合理的请求超时时间
- **状态检查**: 定期检查任务状态，处理异常情况

### 3. 安全考虑

- **输入验证**: 验证用户输入的prompt内容
- **资源限制**: 限制用户可使用的计算资源
- **访问控制**: 实现适当的身份验证和授权机制

### 4. 监控日志

- **任务追踪**: 记录每个任务的生命周期
- **性能监控**: 监控API响应时间和成功率
- **错误日志**: 详细记录错误信息便于调试

---

## 参考资源

- [ComfyUI官方文档](https://github.com/comfyanonymous/ComfyUI)
- [API接口文件参考](https://gitee.com/BTYY/wailikeji-chatgpt/blob/master/comfyui-api.md)
- [原文链接](https://blog.csdn.net/WANGJUNAIJIAO/article/details/143481239)

---

*本文档基于ComfyUI最新版本编写，如有更新请参考官方文档。* 