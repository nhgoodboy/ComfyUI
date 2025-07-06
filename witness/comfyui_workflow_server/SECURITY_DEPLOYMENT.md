# ComfyUI工作流服务器 - 银行级安全部署指南

## 概述

本指南详细介绍如何部署和配置具有银行级安全防护的ComfyUI工作流服务器。该系统实现了五层安全防护架构，确保在多用户环境中的数据安全和系统稳定性。

## 安全架构概览

### 五层安全防护

1. **第1层：IP白名单控制** - 网络层访问控制
2. **第2层：API密钥认证** - 应用程序接口身份验证
3. **第3层：请求签名验证** - 数据完整性和防重放攻击
4. **第4层：速率限制保护** - 防止DDoS和滥用
5. **第5层：JWT令牌验证** - 用户身份和权限管理

### 安全特性

- **防重放攻击**：基于时间戳的签名验证
- **防时序攻击**：恒定时间比较算法
- **防DDoS攻击**：多层速率限制
- **数据加密**：HTTPS强制加密传输
- **令牌管理**：JWT黑名单机制
- **权限控制**：基于角色的访问控制
- **审计日志**：完整的安全事件记录

## 环境要求

### 系统要求

- **操作系统**：Linux (Ubuntu 20.04+ 推荐)
- **Python**：3.8+
- **内存**：最少2GB，推荐4GB+
- **存储**：最少10GB可用空间
- **网络**：稳定的互联网连接

### 依赖服务

- **ComfyUI**：图像处理后端
- **Redis**（可选）：分布式缓存和会话存储
- **Nginx**（推荐）：反向代理和负载均衡

## 安全配置

### 1. 快速配置工具

系统提供了完整的环境配置模板和自动化配置生成器，大大简化了部署过程：

#### 环境配置文件
- **`env.template`**：完整的环境变量模板文件（348行，包含所有配置选项）
- **`generate_config.py`**：智能配置生成器脚本（500+行，全自动化配置）

#### 使用配置生成器

```bash
# 生成开发环境配置
python generate_config.py --env development --output .env.dev

# 生成生产环境配置
python generate_config.py --env production --output .env.prod

# 生成预发布环境配置  
python generate_config.py --env staging --output .env.staging

# 验证配置文件完整性和安全性
python generate_config.py --validate .env

# 显示配置文件详细信息
python generate_config.py --info .env

# 只生成安全密钥
python generate_config.py --keys-only
```

输出示例：
```bash
✅ 配置文件已生成: .env.prod
📝 环境类型: production
🔐 包含 3 个安全密钥
⚙️ 包含 45 个配置项

🚨 生产环境安全提醒:
1. 请修改 ALLOWED_IPS 为实际的服务器IP
2. 请修改 CORS_ORIGINS 为实际的前端域名
3. 请确保所有密钥都是随机生成的
4. 建议定期轮换安全密钥
```

#### 配置验证功能

```bash
# 配置验证示例
python generate_config.py --validate .env

# 输出：
📋 配置文件验证结果: .env
✅ 已验证 45 个配置项
🎉 配置文件验证通过，无错误和警告
```

### 2. 环境特定配置

#### 开发环境配置
```bash
# 生成命令
python generate_config.py --env development --output .env.dev

# 特性：
DEBUG=true
LOG_LEVEL=DEBUG
ALLOWED_IPS=127.0.0.1,::1,192.168.0.0/24,10.0.0.0/8
ENFORCE_HTTPS=false
CORS_ORIGINS=*
ENABLE_DOCS=true
DEV_TOOLS=true
RATE_LIMIT_PER_IP=120
RATE_LIMIT_PER_USER=60
```

#### 生产环境配置
```bash
# 生成命令
python generate_config.py --env production --output .env.prod

# 特性：
DEBUG=false
LOG_LEVEL=WARNING
ALLOWED_IPS=10.0.1.100,10.0.1.101  # 需要修改为实际IP
ENFORCE_HTTPS=true
CORS_ORIGINS=https://your-frontend.com  # 需要修改为实际域名
ENABLE_DOCS=false
DEV_TOOLS=false
WORKERS=4
RATE_LIMIT_PER_IP=60
RATE_LIMIT_PER_USER=30
```

#### 预发布环境配置
```bash
# 生成命令
python generate_config.py --env staging --output .env.staging

# 特性：
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_IPS=127.0.0.1,::1,192.168.0.0/24,10.0.0.0/8
ENFORCE_HTTPS=true
CORS_ORIGINS=https://staging.your-frontend.com
ENABLE_DOCS=true
DEV_TOOLS=true
WORKERS=2
```

### 3. 核心安全配置

#### 自动生成的安全密钥
配置生成器会自动生成以下安全密钥：
```bash
API_SECRET_KEY=a1b2c3d4e5f6...  # 64字符的十六进制密钥
JWT_SECRET_KEY=f6e5d4c3b2a1...  # 64字符的十六进制密钥
ENCRYPTION_KEY=d4c3b2a1f6e5...  # 64字符的十六进制密钥
COMFYUI_CLIENT_ID=comfyui-client-a1b2c3d4
```

#### 只生成密钥
```bash
python generate_config.py --keys-only

# 输出：
🔐 生成安全密钥:
API_SECRET_KEY=a1b2c3d4e5f6789012345678901234567890123456789012345678901234
JWT_SECRET_KEY=f6e5d4c3b2a1098765432109876543210987654321098765432109876543
ENCRYPTION_KEY=d4c3b2a1f6e5432109876543210987654321098765432109876543210987
COMFYUI_CLIENT_ID=comfyui-client-a1b2c3d4
```

### 4. IP白名单配置

**开发环境**：
```bash
ALLOWED_IPS=127.0.0.1,::1,192.168.0.0/24
```

**生产环境**：
```bash
# 仅允许特定服务器访问
ALLOWED_IPS=10.0.1.100,10.0.1.101,203.0.113.10
```

**云环境（AWS/阿里云）**：
```bash
# 根据实际VPC网段配置
ALLOWED_IPS=172.31.0.0/16,10.0.0.0/8
```

## 部署指南

### 1. 标准部署

```bash
# 1. 克隆项目
git clone <repository-url>
cd comfyui_workflow_server

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
# 使用配置生成器生成安全配置
python generate_config.py --env production --output .env
# 根据实际环境修改 ALLOWED_IPS 和 CORS_ORIGINS

# 5. 启动服务
python -m app.main
```

### 2. Docker部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

# 安全设置
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .
RUN chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "-m", "app.main"]
```

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  comfyui-workflow-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_SECRET_KEY=${API_SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ALLOWED_IPS=${ALLOWED_IPS}
      - DEBUG=false
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
      - ./logs:/app/logs
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    networks:
      - comfyui-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - comfyui-workflow-server
    networks:
      - comfyui-network

  redis:
    image: redis:alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    networks:
      - comfyui-network

networks:
  comfyui-network:
    driver: bridge

volumes:
  redis-data:
```

### 3. 生产环境部署

#### Nginx配置

创建 `nginx.conf`：

```nginx
upstream comfyui_backend {
    server comfyui-workflow-server:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL配置
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # 安全头部
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 速率限制
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # 文件大小限制
    client_max_body_size 10M;

    location / {
        proxy_pass http://comfyui_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件缓存
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 安全最佳实践

### 1. 密钥管理

- **生成强密钥**：使用加密安全的随机数生成器
- **定期轮换**：每3-6个月更换密钥
- **安全存储**：使用环境变量或密钥管理服务
- **最小权限**：限制密钥访问权限

### 2. 网络安全

- **HTTPS强制**：生产环境必须使用HTTPS
- **防火墙**：配置适当的防火墙规则
- **VPN访问**：敏感环境使用VPN连接
- **DDoS防护**：使用CDN和DDoS防护服务

### 3. 监控和日志

#### 安全事件监控

```python
# 重要安全事件
- 认证失败
- 签名验证失败
- 速率限制触发
- IP白名单拒绝
- JWT令牌异常
```

#### 日志配置示例

```bash
# 配置结构化日志
LOG_LEVEL=INFO
LOG_FORMAT=json

# 日志轮转
LOG_FILE=/var/log/comfyui/app.log
LOG_MAX_SIZE=100MB
LOG_BACKUP_COUNT=5
```

### 4. 备份和恢复

```bash
# 定期备份关键数据
- 用户上传文件
- 配置文件
- 数据库（如果使用）
- 日志文件

# 备份脚本示例
#!/bin/bash
BACKUP_DIR="/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

tar -czf $BACKUP_DIR/uploads.tar.gz uploads/
tar -czf $BACKUP_DIR/configs.tar.gz configs/
tar -czf $BACKUP_DIR/logs.tar.gz logs/
```

## 用户管理

### 1. JWT令牌管理

#### 创建用户令牌

```python
from app.middleware.user_auth import create_user_token

# 基础用户
token = create_user_token(
    user_id="user123",
    permissions=["read_styles", "create_task", "upload_file"],
    roles=["user"]
)

# 高级用户
token = create_user_token(
    user_id="premium_user",
    permissions=["read_styles", "create_task", "delete_task", "upload_file"],
    roles=["premium"]
)

# 管理员
token = create_user_token(
    user_id="admin",
    permissions=["*"],
    roles=["admin"]
)
```

### 2. 权限矩阵

| 权限 | 基础用户 | 高级用户 | 管理员 |
|------|----------|----------|--------|
| 查看风格 | ✓ | ✓ | ✓ |
| 创建任务 | ✓ | ✓ | ✓ |
| 查看任务 | ✓ | ✓ | ✓ |
| 删除任务 | ✗ | ✓ | ✓ |
| 上传文件 | ✓ | ✓ | ✓ |
| 删除文件 | ✗ | ✓ | ✓ |
| 系统管理 | ✗ | ✗ | ✓ |

## 故障排除

### 1. 常见问题

#### 问题：403 访问被拒绝
```bash
# 检查IP白名单
curl -H "X-Forwarded-For: YOUR_IP" http://localhost:8000/health

# 解决方案
- 将IP添加到ALLOWED_IPS
- 检查网络代理配置
- 验证客户端IP获取逻辑
```

#### 问题：401 API密钥无效
```bash
# 检查API密钥
echo $API_SECRET_KEY

# 解决方案
- 验证密钥长度（至少32字符）
- 检查密钥是否正确设置
- 确认请求头格式正确
```

#### 问题：401 请求签名无效
```bash
# 解决方案
- 检查时间戳是否在有效范围内
- 验证签名算法实现
- 确认请求体哈希计算正确
```

### 2. 调试工具

#### 启用调试模式

```bash
DEBUG=true python -m app.main
```

#### 查看安全信息

```bash
curl http://localhost:8000/security-info
```

#### 健康检查

```bash
curl http://localhost:8000/health
```

## 性能优化

### 1. 系统调优

```bash
# 系统参数优化
echo 'net.core.somaxconn = 65535' >> /etc/sysctl.conf
echo 'net.ipv4.ip_local_port_range = 1024 65535' >> /etc/sysctl.conf
sysctl -p
```

### 2. 应用优化

```python
# 生产环境配置
WORKERS=4  # CPU核心数
WORKER_CONNECTIONS=1000
KEEPALIVE_TIMEOUT=65
```

### 3. 缓存策略

```bash
# Redis缓存配置
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600  # 1小时
```

## 合规性和审计

### 1. 数据保护

- **数据加密**：传输和存储数据加密
- **数据最小化**：只收集必要数据
- **访问控制**：基于最小权限原则
- **数据保留**：定义数据保留策略

### 2. 审计日志

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "event": "user_authentication",
  "user_id": "user123",
  "ip_address": "192.168.1.100",
  "user_agent": "SecureClient/1.0",
  "status": "success"
}
```

### 3. 合规检查清单

- [ ] 所有密钥使用强随机生成
- [ ] HTTPS在生产环境强制启用
- [ ] IP白名单正确配置
- [ ] 速率限制适当设置
- [ ] 日志记录完整安全事件
- [ ] 定期安全审计
- [ ] 备份和恢复流程测试
- [ ] 事件响应计划制定

## 更新和维护

### 1. 安全更新

```bash
# 检查依赖更新
pip list --outdated

# 更新安全补丁
pip install -U cryptography pyjwt
```

### 2. 定期维护任务

- **每日**：检查日志异常
- **每周**：监控系统性能
- **每月**：安全配置审查
- **每季度**：密钥轮换
- **每年**：全面安全审计

## 联系和支持

如有安全问题或需要支持，请联系：

- **安全团队**：security@your-company.com
- **技术支持**：support@your-company.com
- **紧急联系**：+86-xxx-xxxx-xxxx

---

**重要声明**：本部署指南提供的是银行级安全配置，请严格按照指南执行。任何安全配置的修改都应经过充分测试和安全评估。 