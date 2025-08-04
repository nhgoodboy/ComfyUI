# ComfyUI 工作流服务器 API 接入文档

## 目录
- [服务概览](#服务概览)
- [RPC协议规范](#rpc协议规范)
- [WebSocket协议](#websocket协议)
- [API方法详解](#api方法详解)
- [错误码说明](#错误码说明)
- [Go语言集成示例](#go语言集成示例)
- [最佳实践](#最佳实践)

## 服务概览

ComfyUI工作流服务器是一个基于RPC协议的微服务，专注于提供高效的图像工作流处理能力。服务采用现代化的异步架构，支持实时状态推送和灵活的工作流管理。

### 核心特性
- **RPC协议**: 标准化的JSON-RPC 2.0协议
- **实时推送**: WebSocket支持任务状态实时更新
- **工作流管理**: 支持多种预定义工作流和参数验证
- **文件处理**: 完整的文件上传、下载和管理功能
- **状态管理**: 完整的任务生命周期管理

### 服务端点
- **RPC端点**: `POST /rpc`
- **WebSocket**: `WS /ws/{client_id}`
- **健康检查**: `GET /health`
- **静态文件**: `GET /outputs/{filename}`

## RPC协议规范

### 基础协议格式

#### 请求格式
```json
{
  "method": "workflow.execute",
  "params": {
    "request_id": "req_20250803_001",
    "workflow_id": "clay_style_transform",
    "params": {
      "input_image": "https://example.com/image.jpg",
      "prompt": "Clay Style, lovely, cute"
    }
  },
  "id": "client_request_001"
}
```

#### 成功响应格式
```json
{
  "result": {
    "request_id": "req_20250803_001",
    "workflow_id": "clay_style_transform",
    "status": "pending",
    "progress": 0.0,
    "stage": "pending",
    "message": "任务已创建",
    "created_at": 1722697200,
    "workflow_info": {
      "workflow_id": "clay_style_transform",
      "name": "Clay Style Transform",
      "description": "将图片转换为粘土风格",
      "estimated_time": 30
    }
  },
  "id": "client_request_001"
}
```

#### 错误响应格式
```json
{
  "error": {
    "code": 1001,
    "message": "参数错误",
    "data": {
      "field": "workflow_id",
      "value": "invalid_workflow"
    }
  },
  "id": "client_request_001"
}
```

### 批量请求支持

```json
[
  {
    "method": "workflow.list",
    "params": {},
    "id": "req1"
  },
  {
    "method": "workflow.get_schema",
    "params": {"workflow_id": "clay_style_transform"},
    "id": "req2"
  }
]
```

## WebSocket协议

### 连接格式
```
ws://localhost:8000/ws/{client_id}
```

### 消息格式

#### 1. 工作流状态更新 (workflow_update)
针对特定请求ID的连接推送工作流状态变化：

```json
{
  "type": "workflow_update",
  "request_id": "req_20250803_001",
  "data": {
    "request_id": "req_20250803_001",
    "workflow_id": "clay_style_transform",
    "status": "running",
    "progress": 45.5,
    "stage": "processing",
    "message": "正在处理图像...",
    "estimated_remaining": 15
  }
}
```

#### 2. 任务状态更新 (task_update)
针对服务级连接推送所有任务的状态变化：

```json
{
  "type": "task_update",
  "request_id": "req_20250803_001",
  "data": {
    "request_id": "req_20250803_001",
    "workflow_id": "clay_style_transform",
    "status": "completed",
    "progress": 100.0,
    "stage": "completed",
    "message": "任务完成",
    "created_at": 1722697200,
    "started_at": 1722697205,
    "completed_at": 1722697228,
    "duration": 28.5,
    "workflow_params": {
      "input_image": "https://example.com/image.jpg",
      "prompt": "Clay Style, lovely, cute"
    },
    "result": {
      "output_images": [
        {
          "filename": "clay_style_20250803_001.png",
          "size": 1024000,
          "url": "http://localhost:8000/outputs/clay_style_20250803_001.png"
        }
      ]
    }
  }
}
```

#### 3. 心跳消息
用于保持连接活跃：

```
发送: "ping"
接收: "pong"
```

### 连接管理

WebSocket支持两种连接模式：

1. **请求级连接**: 使用`request_id`作为`client_id`
   - 只接收该特定请求的`workflow_update`消息
   - 适用于单次任务监控

2. **服务级连接**: 使用固定的服务标识符（如`workflow_test_system`）
   - 接收所有任务的`task_update`消息  
   - 适用于系统监控和管理面板

## API方法详解

### 工作流方法

#### 1. workflow.execute - 执行工作流

**描述**: 创建并执行工作流任务

**参数**:
```json
{
  "request_id": "string (必需) - 唯一请求标识符",
  "workflow_id": "string (必需) - 工作流标识符",
  "params": "object (必需) - 工作流参数"
}
```

**示例请求**:
```json
{
  "method": "workflow.execute",
  "params": {
    "request_id": "req_20250803_001",
    "workflow_id": "clay_style_transform",
    "params": {
      "input_image": "https://example.com/image.jpg",
      "prompt": "Clay Style, lovely, cute",
      "guidance": 12
    }
  },
  "id": "execute_001"
}
```

**响应**:
```json
{
  "result": {
    "request_id": "req_20250803_001",
    "workflow_id": "clay_style_transform",
    "status": "pending",
    "progress": 0.0,
    "stage": "pending",
    "message": "任务已创建",
    "created_at": 1722697200,
    "workflow_info": {
      "workflow_id": "clay_style_transform",
      "name": "Clay Style Transform",
      "description": "将图片转换为粘土风格",
      "estimated_time": 30,
      "tags": ["style_transfer", "clay"],
      "version": "1.0.0"
    }
  },
  "id": "execute_001"
}
```

#### 2. workflow.list - 获取工作流列表

**描述**: 获取所有可用工作流

**参数**: 无

**响应**:
```json
{
  "result": {
    "workflows": [
      {
        "workflow_id": "clay_style_transform",
        "name": "Clay Style Transform",
        "description": "将图片转换为粘土风格",
        "estimated_time": 30,
        "tags": ["style_transfer", "clay"],
        "version": "1.0.0",
        "parameter_count": 3
      }
    ],
    "total_count": 1
  },
  "id": "list_001"
}
```

#### 3. workflow.get_schema - 获取工作流参数模式

**描述**: 获取工作流的参数定义，用于表单生成

**参数**:
```json
{
  "workflow_id": "string (必需) - 工作流标识符"
}
```

**响应**:
```json
{
  "result": {
    "workflow_id": "clay_style_transform",
    "name": "Clay Style Transform",
    "description": "将图片转换为粘土风格",
    "parameters": {
      "input_image": {
        "name": "input_image",
        "type": "string",
        "description": "输入图片URL",
        "required": true,
        "validation": {
          "format": "url"
        }
      },
      "prompt": {
        "name": "prompt",
        "type": "string",
        "description": "提示词",
        "required": true,
        "default": "Clay Style"
      },
      "guidance": {
        "name": "guidance",
        "type": "number",
        "description": "引导强度",
        "required": false,
        "default": 12,
        "validation": {
          "min": 1,
          "max": 20
        }
      }
    }
  },
  "id": "schema_001"
}
```

#### 4. workflow.get_status - 获取任务状态

**描述**: 查询工作流任务的当前状态

**参数**:
```json
{
  "request_id": "string (必需) - 请求标识符"
}
```

**响应**:
```json
{
  "result": {
    "request_id": "req_20250803_001",
    "workflow_id": "clay_style_transform",
    "status": "running",
    "progress": 65.0,
    "stage": "processing",
    "message": "正在进行风格转换...",
    "created_at": 1722697200,
    "started_at": 1722697205,
    "estimated_remaining": 10,
    "workflow_params": {
      "input_image": "https://example.com/image.jpg",
      "prompt": "Clay Style, lovely, cute"
    }
  },
  "id": "status_001"
}
```

#### 5. workflow.get_result - 获取任务结果

**描述**: 获取已完成任务的处理结果

**参数**:
```json
{
  "request_id": "string (必需) - 请求标识符"
}
```

**响应**:
```json
{
  "result": {
    "request_id": "req_20250803_001",
    "workflow_id": "clay_style_transform",
    "status": "completed",
    "duration": 28.5,
    "completed_at": 1722697228,
    "workflow_params": {
      "input_image": "https://example.com/image.jpg",
      "prompt": "Clay Style, lovely, cute"
    },
    "output_images": [
      {
        "filename": "clay_style_20250803_001.png",
        "size": 1024000,
        "media_type": "image/png",
        "extension": ".png",
        "url": "http://localhost:8000/outputs/clay_style_20250803_001.png",
        "static_url": "http://localhost:8000/outputs/clay_style_20250803_001.png",
        "created_time": 1722697228,
        "modified_time": 1722697228,
        "is_image": true
      }
    ]
  },
  "id": "result_001"
}
```

#### 6. workflow.cancel - 取消任务

**描述**: 取消正在执行或等待的任务

**参数**:
```json
{
  "request_id": "string (必需) - 请求标识符"
}
```

**响应**:
```json
{
  "result": {
    "success": true,
    "request_id": "req_20250803_001",
    "message": "任务已成功取消"
  },
  "id": "cancel_001"
}
```

#### 7. workflow.search - 搜索工作流

**描述**: 根据关键词搜索工作流

**参数**:
```json
{
  "query": "string (可选) - 搜索关键词"
}
```

**响应**:
```json
{
  "result": {
    "workflows": [
      {
        "workflow_id": "clay_style_transform",
        "name": "Clay Style Transform",
        "description": "将图片转换为粘土风格",
        "estimated_time": 30,
        "tags": ["style_transfer", "clay"],
        "version": "1.0.0"
      }
    ],
    "total_count": 1,
    "query": "clay"
  },
  "id": "search_001"
}
```

### 文件方法

#### 8. files.get_output_image - 获取输出图片

**描述**: 获取输出图片的base64编码数据

**参数**:
```json
{
  "filename": "string (必需) - 文件名"
}
```

**响应**:
```json
{
  "result": {
    "filename": "clay_style_20250803_001.png",
    "media_type": "image/png",
    "size": 1024000,
    "data": "iVBORw0KGgoAAAANSUhEUgAA...",
    "url": "http://localhost:8000/outputs/clay_style_20250803_001.png",
    "static_url": "http://localhost:8000/outputs/clay_style_20250803_001.png"
  },
  "id": "get_image_001"
}
```

#### 9. files.get_output_image_info - 获取图片信息

**描述**: 获取输出图片的元信息（不包含图片数据）

**参数**:
```json
{
  "filename": "string (必需) - 文件名"
}
```

**响应**:
```json
{
  "result": {
    "filename": "clay_style_20250803_001.png",
    "size": 1024000,
    "media_type": "image/png",
    "extension": ".png",
    "url": "http://localhost:8000/outputs/clay_style_20250803_001.png",
    "static_url": "http://localhost:8000/outputs/clay_style_20250803_001.png",
    "created_time": 1722697228,
    "modified_time": 1722697228,
    "is_image": true
  },
  "id": "get_info_001"
}
```

#### 10. files.list_output_images - 列出输出图片

**描述**: 获取输出目录中的图片文件列表

**参数**:
```json
{
  "limit": "number (可选) - 返回数量限制，默认100",
  "offset": "number (可选) - 偏移量，默认0",
  "pattern": "string (可选) - 文件名过滤模式，默认*"
}
```

**响应**:
```json
{
  "result": {
    "files": [
      {
        "filename": "clay_style_20250803_001.png",
        "size": 1024000,
        "media_type": "image/png",
        "extension": ".png",
        "url": "http://localhost:8000/outputs/clay_style_20250803_001.png",
        "static_url": "http://localhost:8000/outputs/clay_style_20250803_001.png",
        "created_time": 1722697228,
        "modified_time": 1722697228,
        "is_image": true
      }
    ],
    "total": 1,
    "limit": 100,
    "offset": 0,
    "pattern": "*",
    "has_more": false
  },
  "id": "list_files_001"
}
```

### 系统方法

#### 11. system.health - 系统健康检查

**描述**: 检查系统各组件的健康状态

**参数**: 无

**响应**:
```json
{
  "result": {
    "status": "healthy",
    "timestamp": 1722697200.123,
    "services": {
      "comfyui": "healthy",
      "storage": "healthy",
      "workflows": "healthy"
    },
    "details": {
      "comfyui_connected": true,
      "storage_healthy": true,
      "workflows_count": 5,
      "environment": "production",
      "version": "2.0.0"
    }
  },
  "id": "health_001"
}
```

#### 12. system.get_stats - 获取系统统计

**描述**: 获取系统运行统计信息

**参数**: 无

**响应**:
```json
{
  "result": {
    "timestamp": 1722697200.123,
    "uptime": 86400.0,
    "tasks": {
      "total": 50,
      "by_status": {
        "completed": 45,
        "running": 2,
        "pending": 2,
        "failed": 1
      }
    },
    "files": {
      "inputs": 30,
      "outputs": 45,
      "temp": 5
    },
    "workflows": {
      "total": 5,
      "available": [
        "clay_style_transform",
        "anime_style_transform"
      ]
    }
  },
  "id": "stats_001"
}
```

## 错误码说明

### 通用错误 (1001-1099)
- `1001` - 参数错误：请求参数格式不正确或缺少必需参数
- `1002` - 请求ID无效：request_id格式不符合要求
- `1003` - 方法不存在：调用的RPC方法不存在
- `1004` - 内部错误：服务器内部处理错误

### 文件相关错误 (2001-2099)
- `2001` - 文件URL无效：提供的文件URL格式错误或无法访问
- `2002` - 下载失败：文件下载过程中发生错误
- `2003` - 文件格式无效：文件格式不被支持
- `2004` - 文件过大：文件大小超过限制
- `2005` - 下载超时：文件下载超时
- `2006` - 文件名格式错误：文件名不符合命名规范
- `2007` - 网络错误：网络连接问题

### 工作流相关错误 (3001-3099)
- `3001` - 工作流不存在：指定的工作流ID不存在
- `3002` - ComfyUI不可用：ComfyUI服务连接失败
- `3003` - 工作流执行失败：工作流处理过程中发生错误
- `3004` - 任务不存在：指定的任务ID不存在
- `3005` - 任务已取消：任务已被取消，无法执行操作
- `3006` - 工作流错误：工作流配置或执行错误
- `3007` - 参数验证失败：工作流参数不符合要求

### 系统错误 (9001-9099)
- `9001` - 存储错误：存储系统访问失败
- `9002` - 服务不可用：服务暂时无法提供服务
- `9003` - 请求频率限制：请求频率超过限制

## Go语言集成示例

### 基础客户端结构

```go
package main

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"
    "time"
    
    "github.com/gorilla/websocket"
)

// 基础配置
type Config struct {
    BaseURL   string
    Timeout   time.Duration
    UserAgent string
}

// RPC请求结构
type RPCRequest struct {
    Method string                 `json:"method"`
    Params map[string]interface{} `json:"params"`
    ID     string                 `json:"id"`
}

// RPC响应结构
type RPCResponse struct {
    Result json.RawMessage        `json:"result,omitempty"`
    Error  *RPCError              `json:"error,omitempty"`
    ID     string                 `json:"id"`
}

// RPC错误结构
type RPCError struct {
    Code    int                    `json:"code"`
    Message string                 `json:"message"`
    Data    map[string]interface{} `json:"data,omitempty"`
}

func (e *RPCError) Error() string {
    return fmt.Sprintf("RPC Error %d: %s", e.Code, e.Message)
}

// 客户端结构
type ComfyUIClient struct {
    config     Config
    httpClient *http.Client
    wsConn     *websocket.Conn
}

// 创建新客户端
func NewComfyUIClient(config Config) *ComfyUIClient {
    if config.Timeout == 0 {
        config.Timeout = 30 * time.Second
    }
    if config.UserAgent == "" {
        config.UserAgent = "ComfyUI-Go-Client/1.0"
    }
    
    return &ComfyUIClient{
        config: config,
        httpClient: &http.Client{
            Timeout: config.Timeout,
        },
    }
}
```

### RPC调用方法

```go
// 执行RPC调用
func (c *ComfyUIClient) CallRPC(ctx context.Context, method string, params map[string]interface{}, result interface{}) error {
    // 生成请求ID
    requestID := fmt.Sprintf("go_client_%d", time.Now().UnixNano())
    
    // 构造RPC请求
    rpcReq := RPCRequest{
        Method: method,
        Params: params,
        ID:     requestID,
    }
    
    // 序列化请求
    reqBody, err := json.Marshal(rpcReq)
    if err != nil {
        return fmt.Errorf("序列化请求失败: %w", err)
    }
    
    // 创建HTTP请求
    httpReq, err := http.NewRequestWithContext(ctx, "POST", c.config.BaseURL+"/rpc", bytes.NewBuffer(reqBody))
    if err != nil {
        return fmt.Errorf("创建HTTP请求失败: %w", err)
    }
    
    httpReq.Header.Set("Content-Type", "application/json")
    httpReq.Header.Set("User-Agent", c.config.UserAgent)
    
    // 发送请求
    resp, err := c.httpClient.Do(httpReq)
    if err != nil {
        return fmt.Errorf("发送请求失败: %w", err)
    }
    defer resp.Body.Close()
    
    // 解析响应
    var rpcResp RPCResponse
    if err := json.NewDecoder(resp.Body).Decode(&rpcResp); err != nil {
        return fmt.Errorf("解析响应失败: %w", err)
    }
    
    // 检查RPC错误
    if rpcResp.Error != nil {
        return rpcResp.Error
    }
    
    // 解析结果
    if result != nil && rpcResp.Result != nil {
        if err := json.Unmarshal(rpcResp.Result, result); err != nil {
            return fmt.Errorf("解析结果失败: %w", err)
        }
    }
    
    return nil
}
```

### 工作流执行示例

```go
// 工作流执行参数
type WorkflowExecuteParams struct {
    RequestID  string                 `json:"request_id"`
    WorkflowID string                 `json:"workflow_id"`
    Params     map[string]interface{} `json:"params"`
}

// 工作流状态结构
type WorkflowStatus struct {
    RequestID          string                 `json:"request_id"`
    WorkflowID         string                 `json:"workflow_id"`
    Status             string                 `json:"status"`
    Progress           float64                `json:"progress"`
    Stage              string                 `json:"stage"`
    Message            string                 `json:"message"`
    CreatedAt          int64                  `json:"created_at"`
    StartedAt          *int64                 `json:"started_at"`
    CompletedAt        *int64                 `json:"completed_at"`
    EstimatedRemaining *int                   `json:"estimated_remaining"`
    WorkflowParams     map[string]interface{} `json:"workflow_params"`
    ErrorMessage       *string                `json:"error_message"`
}

// 工作流结果结构
type WorkflowResult struct {
    RequestID      string                 `json:"request_id"`
    WorkflowID     string                 `json:"workflow_id"`
    Status         string                 `json:"status"`
    Duration       float64                `json:"duration"`
    CompletedAt    *int64                 `json:"completed_at"`
    WorkflowParams map[string]interface{} `json:"workflow_params"`
    OutputImages   []FileInfo             `json:"output_images"`
}

// 文件信息结构
type FileInfo struct {
    Filename     string `json:"filename"`
    Size         int64  `json:"size"`
    MediaType    string `json:"media_type"`
    Extension    string `json:"extension"`
    URL          string `json:"url"`
    StaticURL    string `json:"static_url"`
    CreatedTime  *int64 `json:"created_time"`
    ModifiedTime *int64 `json:"modified_time"`
    IsImage      *bool  `json:"is_image"`
}

// 执行工作流
func (c *ComfyUIClient) ExecuteWorkflow(ctx context.Context, requestID, workflowID string, params map[string]interface{}) (*WorkflowStatus, error) {
    executeParams := map[string]interface{}{
        "request_id":  requestID,
        "workflow_id": workflowID,
        "params":      params,
    }
    
    var status WorkflowStatus
    err := c.CallRPC(ctx, "workflow.execute", executeParams, &status)
    if err != nil {
        return nil, fmt.Errorf("执行工作流失败: %w", err)
    }
    
    return &status, nil
}

// 获取工作流状态
func (c *ComfyUIClient) GetWorkflowStatus(ctx context.Context, requestID string) (*WorkflowStatus, error) {
    params := map[string]interface{}{
        "request_id": requestID,
    }
    
    var status WorkflowStatus
    err := c.CallRPC(ctx, "workflow.get_status", params, &status)
    if err != nil {
        return nil, fmt.Errorf("获取工作流状态失败: %w", err)
    }
    
    return &status, nil
}

// 获取工作流结果
func (c *ComfyUIClient) GetWorkflowResult(ctx context.Context, requestID string) (*WorkflowResult, error) {
    params := map[string]interface{}{
        "request_id": requestID,
    }
    
    var result WorkflowResult
    err := c.CallRPC(ctx, "workflow.get_result", params, &result)
    if err != nil {
        return nil, fmt.Errorf("获取工作流结果失败: %w", err)
    }
    
    return &result, nil
}
```

### WebSocket实时监听

```go
// WebSocket消息结构
type WebSocketMessage struct {
    Type      string      `json:"type"`       // "workflow_update" 或 "task_update"
    RequestID string      `json:"request_id"`
    Data      interface{} `json:"data"`
}

// 连接WebSocket
func (c *ComfyUIClient) ConnectWebSocket(ctx context.Context, clientID string) error {
    u, err := url.Parse(c.config.BaseURL)
    if err != nil {
        return fmt.Errorf("解析URL失败: %w", err)
    }
    
    // 转换为WebSocket URL
    wsURL := url.URL{
        Scheme: func() string {
            if u.Scheme == "https" {
                return "wss"
            }
            return "ws"
        }(),
        Host: u.Host,
        Path: fmt.Sprintf("/ws/%s", clientID),
    }
    
    conn, _, err := websocket.DefaultDialer.DialContext(ctx, wsURL.String(), nil)
    if err != nil {
        return fmt.Errorf("WebSocket连接失败: %w", err)
    }
    
    c.wsConn = conn
    return nil
}

// 监听WebSocket消息
func (c *ComfyUIClient) ListenWebSocket(ctx context.Context, messageHandler func(WebSocketMessage)) error {
    if c.wsConn == nil {
        return fmt.Errorf("WebSocket未连接")
    }
    
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
            var message WebSocketMessage
            err := c.wsConn.ReadJSON(&message)
            if err != nil {
                return fmt.Errorf("读取WebSocket消息失败: %w", err)
            }
            
            messageHandler(message)
        }
    }
}

// 关闭WebSocket连接
func (c *ComfyUIClient) CloseWebSocket() error {
    if c.wsConn != nil {
        return c.wsConn.Close()
    }
    return nil
}
```

### 完整使用示例

```go
func main() {
    // 创建客户端
    client := NewComfyUIClient(Config{
        BaseURL: "http://localhost:8000",
        Timeout: 60 * time.Second,
    })
    
    ctx := context.Background()
    
    // 1. 获取可用工作流列表
    fmt.Println("获取工作流列表...")
    var workflows struct {
        Workflows   []map[string]interface{} `json:"workflows"`
        TotalCount  int                      `json:"total_count"`
    }
    err := client.CallRPC(ctx, "workflow.list", map[string]interface{}{}, &workflows)
    if err != nil {
        panic(fmt.Sprintf("获取工作流列表失败: %v", err))
    }
    
    fmt.Printf("发现 %d 个工作流\n", workflows.TotalCount)
    for _, wf := range workflows.Workflows {
        fmt.Printf("- %s: %s\n", wf["workflow_id"], wf["name"])
    }
    
    // 2. 执行工作流
    requestID := fmt.Sprintf("go_example_%d", time.Now().Unix())
    workflowParams := map[string]interface{}{
        "input_image": "https://example.com/test-image.jpg",
        "prompt":      "Clay Style, lovely, cute",
        "guidance":    12,
    }
    
    fmt.Printf("\n执行工作流 (Request ID: %s)...\n", requestID)
    status, err := client.ExecuteWorkflow(ctx, requestID, "clay_style_transform", workflowParams)
    if err != nil {
        panic(fmt.Sprintf("执行工作流失败: %v", err))
    }
    
    fmt.Printf("工作流已启动，状态: %s\n", status.Status)
    
    // 3. 连接WebSocket监听实时状态
    fmt.Println("\n连接WebSocket监听状态更新...")
    err = client.ConnectWebSocket(ctx, requestID)
    if err != nil {
        fmt.Printf("WebSocket连接失败: %v\n", err)
    } else {
        // 在新goroutine中监听WebSocket消息
        go func() {
            err := client.ListenWebSocket(ctx, func(message WebSocketMessage) {
                switch message.Type {
                case "workflow_update":
                    if message.RequestID == requestID {
                        fmt.Printf("工作流状态更新: %+v\n", message.Data)
                    }
                case "task_update":
                    fmt.Printf("任务状态更新: %+v\n", message.Data)
                default:
                    fmt.Printf("未知消息类型: %s\n", message.Type)
                }
            })
            if err != nil {
                fmt.Printf("WebSocket监听错误: %v\n", err)
            }
        }()
    }
    
    // 4. 轮询检查状态直到完成
    fmt.Println("\n等待任务完成...")
    for {
        currentStatus, err := client.GetWorkflowStatus(ctx, requestID)
        if err != nil {
            fmt.Printf("获取状态失败: %v\n", err)
            break
        }
        
        fmt.Printf("当前状态: %s (%.1f%%)\n", currentStatus.Status, currentStatus.Progress)
        
        if currentStatus.Status == "completed" {
            fmt.Println("任务完成！")
            break
        } else if currentStatus.Status == "failed" {
            fmt.Printf("任务失败: %s\n", *currentStatus.ErrorMessage)
            break
        }
        
        time.Sleep(2 * time.Second)
    }
    
    // 5. 获取结果
    fmt.Println("\n获取任务结果...")
    result, err := client.GetWorkflowResult(ctx, requestID)
    if err != nil {
        fmt.Printf("获取结果失败: %v\n", err)
    } else {
        fmt.Printf("处理完成，耗时: %.2f秒\n", result.Duration)
        fmt.Printf("输出图片数量: %d\n", len(result.OutputImages))
        for i, img := range result.OutputImages {
            fmt.Printf("  图片%d: %s (%d bytes)\n", i+1, img.Filename, img.Size)
            fmt.Printf("  访问URL: %s\n", img.URL)
        }
    }
    
    // 清理资源
    client.CloseWebSocket()
}
```

### 错误处理最佳实践

```go
// 定义自定义错误类型
type ComfyUIError struct {
    Code    int
    Message string
    Details map[string]interface{}
}

func (e *ComfyUIError) Error() string {
    return fmt.Sprintf("ComfyUI Error %d: %s", e.Code, e.Message)
}

// 错误处理辅助函数
func HandleRPCError(err error) {
    if rpcErr, ok := err.(*RPCError); ok {
        switch rpcErr.Code {
        case 1001:
            fmt.Printf("参数错误: %s\n", rpcErr.Message)
            if rpcErr.Data != nil {
                fmt.Printf("错误详情: %+v\n", rpcErr.Data)
            }
        case 3001:
            fmt.Printf("工作流不存在: %s\n", rpcErr.Message)
        case 3004:
            fmt.Printf("任务不存在: %s\n", rpcErr.Message)
        default:
            fmt.Printf("RPC错误: %s\n", rpcErr.Message)
        }
    } else {
        fmt.Printf("其他错误: %v\n", err)
    }
}

// 带重试的工作流执行
func (c *ComfyUIClient) ExecuteWorkflowWithRetry(ctx context.Context, requestID, workflowID string, params map[string]interface{}, maxRetries int) (*WorkflowStatus, error) {
    var lastErr error
    
    for i := 0; i < maxRetries; i++ {
        status, err := c.ExecuteWorkflow(ctx, requestID, workflowID, params)
        if err == nil {
            return status, nil
        }
        
        lastErr = err
        
        // 检查是否为可重试的错误
        if rpcErr, ok := err.(*RPCError); ok {
            switch rpcErr.Code {
            case 3002: // ComfyUI不可用
                fmt.Printf("ComfyUI暂时不可用，%d秒后重试... (尝试 %d/%d)\n", (i+1)*5, i+1, maxRetries)
                time.Sleep(time.Duration(i+1) * 5 * time.Second)
                continue
            default:
                // 非可重试错误，直接返回
                return nil, err
            }
        }
        
        // 其他错误也重试
        fmt.Printf("执行失败，%d秒后重试... (尝试 %d/%d): %v\n", (i+1)*2, i+1, maxRetries, err)
        time.Sleep(time.Duration(i+1) * 2 * time.Second)
    }
    
    return nil, fmt.Errorf("重试%d次后仍然失败: %w", maxRetries, lastErr)
}
```

## 最佳实践

### 1. 请求ID管理
- 使用唯一的请求ID，推荐格式：`{服务名}_{时间戳}_{随机数}`
- 保持请求ID的可追踪性，便于日志分析和问题排查

### 2. 错误处理
- 始终检查RPC响应中的错误字段
- 根据错误码实现相应的重试策略
- 对网络错误和临时故障实现指数退避重试

### 3. 性能优化
- 使用HTTP连接池减少连接开销
- 合理设置请求超时时间
- 对于批量操作，优先使用批量RPC请求

### 4. 实时监控
- 使用WebSocket获取实时状态更新
- 实现心跳机制保持连接活跃
- 妥善处理连接断开和重连

### 5. 资源管理
- 及时关闭WebSocket连接
- 使用context控制请求生命周期
- 实现优雅关闭机制

### 6. 安全考虑
- 验证输入参数，防止注入攻击
- 使用HTTPS确保传输安全
- 实现访问控制和频率限制

通过遵循这些最佳实践，您可以构建稳定、高效的ComfyUI工作流服务客户端应用。