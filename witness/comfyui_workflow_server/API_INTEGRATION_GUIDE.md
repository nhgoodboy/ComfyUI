# ComfyUI工作流服务器 - API集成指南

**版本**: 2.0.0
**最后更新**: [DATE]

## 引言

欢迎使用ComfyUI工作流服务器API！本指南旨在帮助外部服务器开发者安全、高效地与我们的API进行集成。本文档详细介绍了API的五层安全防护架构、所有可用端点、数据模型以及完整的集成工作流示例。

在集成开始前，请确保您已从管理员处获取以下信息：
- **服务器基础URL** (例如: `https://your-server.com`)
- **API密钥** (`API_SECRET_KEY`)
- **您的服务器IP地址** (必须被添加到服务器的IP白名单中)

---

## 1. 银行级安全与认证

为了确保最高级别的安全性，所有对本API的请求都必须经过一个严格的五层安全防护验证。**任何不符合安全要求的请求都将被直接拒绝。**

### 1.1. 五层安全防护架构

| 层级 | 防护措施 | 实现方式 | 作用 |
|:---:|:---|:---|:---|
| **1** | **IP白名单** | 服务器配置 | 仅允许授权的服务器IP发起请求。 |
| **2** | **API密钥认证** | `x-api-key` 请求头 | 验证请求来源是否为已授权的客户端。 |
| **3** | **请求签名验证** | `x-signature` & `x-timestamp` 请求头 | 使用HMAC-SHA256确保数据完整性，防止重放攻击和数据篡改。 |
| **4** | **速率限制** | 服务器中间件 | 基于IP和用户ID限制请求频率，防止DDoS和恶意攻击。 |
| **5** | **JWT用户令牌** | `Authorization: Bearer <token>` 请求头 | 验证执行操作的用户身份，实现多用户数据隔离。 |

### 1.2. 请求签名流程 (关键步骤)

除了获取用户令牌的端点外，**所有API请求都必须进行签名**。以下是生成有效签名的分步指南。

#### 第1步：准备签名材料

您需要准备以下四项内容：
1.  **HTTP方法**: 大写的请求方法 (如 `GET`, `POST`, `DELETE`)。
2.  **请求路径**: 完整的请求路径，包含查询参数 (如 `/api/v1/styles?page=1&limit=10`)。
3.  **时间戳**: 当前的Unix时间戳（整数秒）。
4.  **请求体 (Body)**:
    - 对于 `GET`, `DELETE` 等无请求体的请求，请求体为空字符串 `""`。
    - 对于 `POST`, `PUT` 等有请求体的请求，请求体为**未经修改的原始JSON字符串**。

#### 第2步：构造签名字符串

将上述材料用换行符 `\n` 连接，构成一个待签名的字符串。格式如下：

```
{HTTP方法}\n{请求路径}\n{时间戳}\n{请求体}
```

**示例 (POST请求):**
```
POST\n/api/v1/styles/clay_style/transform\n1678886400\n{"image_id":"file-abc-123","user_id":"user-001"}
```

**示例 (GET请求):**
```
GET\n/api/v1/tasks\n1678886405\n
```
(注意：GET请求的最后是一个空字符串，因此以`\n`结尾)

#### 第3步：计算HMAC-SHA256签名

使用您的 `API_SECRET_KEY` 作为密钥，对上一步构造的签名字符串进行HMAC-SHA256哈希计算，然后进行Hex编码。

#### 第4步：组装请求头

在您的HTTP请求中加入以下**四个**必需的安全相关的请求头：

- `x-api-key`: 您的API密钥。
- `x-timestamp`: 第1步中使用的时间戳。
- `x-signature`: 第3步中计算出的签名 (Hex编码字符串)。
- `Authorization`: `Bearer ` + 您的用户JWT令牌 (获取令牌的API除外)。

#### Python签名代码示例

这是一个可以直接使用的Python函数，用于生成请求签名和请求头。

```python
import time
import hmac
import hashlib
import json

def get_secure_headers(api_secret_key: str, method: str, path: str, body: dict = None) -> dict:
    """
    为API请求生成安全头部
    """
    timestamp = str(int(time.time()))
    
    body_str = ""
    if body:
        # 使用紧凑格式的JSON字符串
        body_str = json.dumps(body, separators=(',', ':'), ensure_ascii=False)

    # 构造签名字符串
    message_to_sign = f"{method.upper()}\n{path}\n{timestamp}\n{body_str}"
    
    # 计算签名
    signature = hmac.new(
        api_secret_key.encode('utf-8'),
        message_to_sign.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'x-api-key': api_secret_key, # 注意：实际生产中API Key不应该直接等于Secret Key
        'x-timestamp': timestamp,
        'x-signature': signature,
        'Content-Type': 'application/json'
    }
    
    return headers

# --- 使用示例 ---
# API_SECRET_KEY = "your_actual_api_secret_key"
# API_KEY = "your_actual_api_key" # 通常与Secret Key不同

# # 示例1: POST请求
# method = "POST"
# path = "/api/v1/auth/token"
# body = {"user_id": "test-user-007", "expires_in_minutes": 60}
# headers = get_secure_headers(API_SECRET_KEY, method, path, body)
# headers['x-api-key'] = API_KEY # 使用实际的API Key
# print("POST Headers:", headers)

# # 示例2: GET请求
# method = "GET"
# path = "/api/v1/styles"
# headers = get_secure_headers(API_SECRET_KEY, method, path)
# headers['x-api-key'] = API_KEY # 使用实际的API Key
# print("\nGET Headers:", headers)
```

### 1.3. 获取用户JWT令牌

在调用业务API之前，您必须为需要操作的用户获取一个JWT令牌。

- **端点**: `POST /api/v1/auth/token`
- **请求说明**: 此请求**也需要签名**，但不需要 `Authorization` 头。
- **请求体**:
    - `user_id` (string, required): 您系统中的唯一用户标识符。
    - `user_name` (string, optional): 用户的显示名称。
    - `expires_in_minutes` (integer, optional): 令牌有效期（分钟），默认60。
- **成功响应**:
    - `access_token`: JWT令牌字符串。
    - `token_type`: "bearer"。
    - `expires_at`: 令牌过期时间戳。

您需要缓存此令牌，并在其过期前使用它来调用其他API。

---

## 2. API端点详解

**基础URL**: `https://your-server.com`

### 2.1. 认证API

#### 获取用户令牌
- `POST /api/v1/auth/token`
- **描述**: 为指定用户生成一个JWT访问令牌。
- **请求头**: `x-api-key`, `x-timestamp`, `x-signature`
- **请求体**: `application/json`
  ```json
  {
    "user_id": "user-unique-id-123",
    "user_name": "John Doe",
    "expires_in_minutes": 120
  }
  ```
- **成功响应 (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJI...",
    "token_type": "bearer",
    "expires_at": 1678893600
  }
  ```

### 2.2. 文件管理API

#### 上传文件
- `POST /api/v1/files/upload`
- **描述**: 上传一个图片文件供后续工作流使用。
- **请求头**: `Authorization`, `x-api-key`, `x-timestamp`, `x-signature`
- **请求体**: `multipart/form-data`
  - `file`: 图像文件本身。
- **成功响应 (201 Created)**:
  ```json
  {
    "id": "file-a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
    "filename": "cat_photo.jpg",
    "content_type": "image/jpeg",
    "size": 524288,
    "created_at": "2023-03-15T12:00:00Z",
    "user_id": "user-unique-id-123"
  }
  ```

#### 列出用户文件
- `GET /api/v1/files`
- **描述**: 获取当前用户已上传的所有文件列表。
- **请求头**: `Authorization`, `x-api-key`, `x-timestamp`, `x-signature`
- **成功响应 (200 OK)**:
  ```json
  [
    {
      "id": "file-a1b2...",
      "filename": "cat_photo.jpg",
      ...
    }
  ]
  ```

### 2.3. 风格API

#### 列出可用风格
- `GET /api/v1/styles`
- **描述**: 获取所有可用的图像转换风格。
- **请求头**: `Authorization`, `x-api-key`, `x-timestamp`, `x-signature`
- **成功响应 (200 OK)**:
  ```json
  [
    {
      "id": "clay_style",
      "name": "陶土风格转换",
      "description": "将图片转换为可爱的陶土捏制艺术风格。",
      "tags": ["artistic", "cute", "3d"],
      "estimated_time": 45
    },
    {
      "id": "anime_style",
      "name": "动漫风格转换",
      ...
    }
  ]
  ```

### 2.4. 任务执行API

#### 创建转换任务
- `POST /api/v1/styles/{style_id}/transform`
- **描述**: 使用指定风格和图片，创建一个新的图像转换任务。
- **请求头**: `Authorization`, `x-api-key`, `x-timestamp`, `x-signature`
- **路径参数**:
  - `style_id` (string): 要使用的风格ID，如 `clay_style`。
- **请求体**:
  ```json
  {
    "image_id": "file-a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8"
  }
  ```
- **成功响应 (202 Accepted)**:
  ```json
  {
    "task_id": "task-b2c3d4e5-f6a1-b2c3-d4e5-f6a1b2c3d4e5",
    "status": "queued",
    "message": "任务已成功加入队列"
  }
  ```

#### 获取任务状态
- `GET /api/v1/tasks/{task_id}`
- **描述**: 查询指定任务的当前状态。
- **请求头**: `Authorization`, `x-api-key`, `x-timestamp`, `x-signature`
- **成功响应 (200 OK)**:
  ```json
  {
    "id": "task-b2c3...",
    "user_id": "user-unique-id-123",
    "style_id": "clay_style",
    "status": "processing",  // queued, processing, completed, failed
    "progress": 0.75,
    "created_at": "2023-03-15T12:05:00Z",
    "updated_at": "2023-03-15T12:05:30Z"
  }
  ```

#### 获取任务结果
- `GET /api/v1/tasks/{task_id}/result`
- **描述**: 获取已完成任务的结果。仅当任务状态为 `completed` 时有效。
- **请求头**: `Authorization`, `x-api-key`, `x-timestamp`, `x-signature`
- **成功响应 (200 OK)**:
  ```json
  {
    "task_id": "task-b2c3...",
    "status": "completed",
    "result": {
      "original_file_id": "file-a1b2...",
      "output_files": [
        {
          "id": "file-f6a1b2c3...",
          "filename": "result_clay_style_cat_photo.png",
          "url": "https://your-server.com/outputs/user-unique-id-123/result_....png",
          "size": 1048576
        }
      ]
    },
    "completed_at": "2023-03-15T12:06:00Z"
  }
  ```

---

## 3. 端到端工作流示例

以下是一个完整的业务流程，展示如何将一张用户上传的图片转换为陶土风格。

**前提**:
- 外部服务器IP已加入白名单。
- 已获取`API_KEY`和`API_SECRET_KEY`。
- 用户 `user-101` 在外部服务器上操作。

**流程**:

1.  **外部服务器为 `user-101` 获取JWT**:
    - `POST /api/v1/auth/token` with body `{"user_id": "user-101"}`.
    - 收到并缓存 `access_token`。

2.  **用户上传图片 `my_pet.png`**:
    - 外部服务器接收到图片。
    - 外部服务器调用 `POST /api/v1/files/upload` (multipart/form-data)，将图片上传。
    - 收到响应，获得 `file_id` (例如: `file-pet-001`)。

3.  **用户选择 "陶土风格"**:
    - 外部服务器调用 `POST /api/v1/styles/clay_style/transform`。
    - 请求体: `{"image_id": "file-pet-001"}`。
    - 所有请求头 (包括签名和JWT) 都必须正确设置。
    - 收到响应，获得 `task_id` (例如: `task-clay-002`)。

4.  **外部服务器轮询任务状态**:
    - 定期 (例如每5秒) 调用 `GET /api/v1/tasks/task-clay-002`。
    - 持续检查响应中的 `status` 字段。

5.  **任务完成**:
    - 当轮询发现 `status` 变为 `completed` 时，停止轮询。

6.  **获取并展示结果**:
    - 外部服务器调用 `GET /api/v1/tasks/task-clay-002/result`。
    - 从响应的 `result.output_files[0].url` 中获取结果图片的URL。
    - 将该图片URL返回给前端或直接下载图片内容，展示给用户。

---

## 4. 错误处理

API使用标准的HTTP状态码。所有错误响应体都遵循统一格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "A human-readable error message.",
    "details": "Optional extra details or context."
  }
}
```

**常见错误码**:
| HTTP状态码 | 错误码 (`code`) | 描述 |
|:---|:---|:---|
| `400 Bad Request` | `VALIDATION_ERROR` | 请求体或参数验证失败。 |
| `401 Unauthorized` | `AUTHENTICATION_FAILED` | API密钥错误、签名无效或JWT令牌过期/无效。 |
| `403 Forbidden` | `PERMISSION_DENIED` | IP不在白名单，或用户无权访问资源。 |
| `404 Not Found` | `RESOURCE_NOT_FOUND` | 请求的资源 (如任务、文件) 不存在。 |
| `429 Too Many Requests` | `RATE_LIMIT_EXCEEDED` | 请求频率超过限制。 |
| `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | 服务器内部发生未知错误。 |
| `503 Service Unavailable` | `COMFYUI_UNAVAILABLE` | 后端ComfyUI服务无法连接。 | 