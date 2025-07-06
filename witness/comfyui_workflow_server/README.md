# ComfyUI工作流服务器

具有银行级安全防护的ComfyUI工作流服务器，支持多用户并发图片风格转换。

## 主要特性

- **🔐 银行级安全防护**：五层安全防护架构，包括IP白名单、API密钥认证、请求签名验证、速率限制和JWT令牌验证
- **👥 多用户支持**：用户数据完全隔离，支持并发访问
- **⚡ 高性能处理**：基于ComfyUI的强大图像处理能力
- **🎨 多风格支持**：支持陶土风格、动漫风格等多种图像风格转换
- **📁 智能存储**：用户文件独立存储，自动清理机制
- **🔄 配置驱动**：基于YAML配置的灵活架构

## 五层安全防护

1. **第1层：IP白名单控制** - 网络层访问控制
2. **第2层：API密钥认证** - 应用程序接口身份验证
3. **第3层：请求签名验证** - 数据完整性和防重放攻击
4. **第4层：速率限制保护** - 防止DDoS和滥用
5. **第5层：JWT令牌验证** - 用户身份和权限管理

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd comfyui_workflow_server

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 智能配置生成

系统提供了完整的配置生成器，可以一键生成所有必要的安全配置：

```bash
# 生成开发环境配置
python generate_config.py --env development --output .env.dev

# 生成生产环境配置
python generate_config.py --env production --output .env.prod

# 验证配置文件
python generate_config.py --validate .env

# 显示配置信息
python generate_config.py --info .env

# 只生成密钥
python generate_config.py --keys-only
```

### 3. 配置文件特性

- **🔐 自动密钥生成**：使用加密安全的随机数生成64字符密钥
- **📋 环境特定配置**：开发、生产、预发布环境的差异化配置
- **✅ 配置验证**：自动验证配置文件的完整性和安全性
- **📊 配置分析**：显示配置文件的详细信息和安全检查结果

### 4. 启动服务

```bash
# 启动开发服务器
python -m app.main

# 或使用指定配置文件
python -m app.main --config .env.prod
```

### 5. 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 获取可用风格
curl -X GET "http://localhost:8000/api/v1/styles" \
  -H "x-api-key: your-api-key" \
  -H "authorization: Bearer your-jwt-token"
```

## 配置文件详解

### 环境配置模板

系统提供了完整的配置模板文件：

- **`env.template`**：348行完整配置模板，包含所有配置项的详细说明
- **`generate_config.py`**：500+行智能配置生成器，支持多种环境配置

### 配置验证示例

```bash
# 验证配置文件
python generate_config.py --validate .env

# 输出示例：
📋 配置文件验证结果: .env
✅ 已验证 45 个配置项
🎉 配置文件验证通过，无错误和警告
```

### 生产环境安全提醒

生成生产环境配置时，系统会自动提示：
```bash
🚨 生产环境安全提醒:
1. 请修改 ALLOWED_IPS 为实际的服务器IP
2. 请修改 CORS_ORIGINS 为实际的前端域名
3. 请确保所有密钥都是随机生成的
4. 建议定期轮换安全密钥
```

## API 使用示例

系统提供了完整的安全客户端示例，展示如何正确使用API：

```bash
# 运行安全客户端示例
python examples/secure_client_example.py

# 生成配置示例
python examples/secure_client_example.py generate-config
```

## 多用户支持

系统支持多用户并发访问，每个用户的数据完全隔离：

- **用户身份验证**：通过JWT令牌识别用户
- **数据隔离**：每个用户的任务和文件独立存储
- **权限控制**：用户只能访问自己的资源
- **资源限制**：每用户的文件数量和存储空间限制

## 支持的风格

- **陶土风格**：将图片转换为陶土艺术风格
- **动漫风格**：将图片转换为动漫艺术风格
- **更多风格**：支持通过YAML配置添加新风格

## 性能特性

- **高并发处理**：支持多用户同时进行图片转换
- **智能缓存**：减少重复处理，提高响应速度
- **资源管理**：自动清理过期文件，优化存储使用
- **监控统计**：实时统计系统性能和用户使用情况

## 部署指南

详细的部署指南请参考：
- [SECURITY_DEPLOYMENT.md](SECURITY_DEPLOYMENT.md) - 银行级安全部署指南
- [MULTIUSER_IMPLEMENTATION.md](MULTIUSER_IMPLEMENTATION.md) - 多用户实施详解

## 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 贡献指南

欢迎提交问题和贡献代码。请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

## 支持

如果您遇到任何问题或需要帮助，请：
1. 查看 [FAQ](FAQ.md)
2. 提交 [Issue](https://github.com/your-repo/issues)
3. 联系技术支持

## 更新日志

请查看 [CHANGELOG.md](CHANGELOG.md) 了解最新更新。 