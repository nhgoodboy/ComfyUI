#!/usr/bin/env python3
"""
ComfyUI工作流服务器配置生成器
=====================================

这个脚本帮助生成安全的环境配置文件，包括：
- 随机安全密钥生成
- 不同环境的配置模板
- 安全检查和验证
- 配置文件加密

使用方法：
python generate_config.py [选项]

示例：
python generate_config.py --env production --output .env
python generate_config.py --env development --output .env.dev
python generate_config.py --validate .env
"""

import argparse
import secrets
import os
import sys
import json
import ipaddress
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib
import base64

class ConfigGenerator:
    """配置生成器类"""
    
    def __init__(self):
        self.template_file = "env.template"
        self.config_sections = {
            "security": "🔐 核心安全配置",
            "network": "🌐 网络安全配置", 
            "timing": "⏱️ 安全时间配置",
            "ratelimit": "🚦 速率限制配置",
            "app": "🚀 应用基础配置",
            "comfyui": "🎨 ComfyUI后端配置",
            "files": "📁 文件存储配置",
            "advanced": "🔧 高级配置",
            "monitoring": "📊 监控和性能配置",
            "users": "🎭 多用户和权限配置"
        }
        
    def generate_secure_key(self, length: int = 32) -> str:
        """生成安全的随机密钥"""
        return secrets.token_hex(length)
    
    def generate_client_id(self) -> str:
        """生成客户端ID"""
        return f"comfyui-client-{secrets.token_hex(8)}"
    
    def validate_ip_list(self, ip_list: str) -> bool:
        """验证IP地址列表"""
        try:
            ips = [ip.strip() for ip in ip_list.split(',')]
            for ip in ips:
                if '/' in ip:
                    ipaddress.ip_network(ip, strict=False)
                else:
                    ipaddress.ip_address(ip)
            return True
        except Exception:
            return False
    
    def get_environment_defaults(self, env_type: str) -> Dict[str, str]:
        """获取不同环境的默认配置"""
        base_config = {
            # 核心安全配置
            "API_SECRET_KEY": self.generate_secure_key(),
            "JWT_SECRET_KEY": self.generate_secure_key(),
            "ENCRYPTION_KEY": self.generate_secure_key(),
            
            # 应用基础配置
            "APP_NAME": "ComfyUI Workflow Server",
            "APP_VERSION": "2.0.0",
            "HOST": "0.0.0.0",
            "PORT": "8000",
            "WORKERS": "1",
            
            # ComfyUI配置
            "COMFYUI_HOST": "127.0.0.1",
            "COMFYUI_PORT": "8188",
            "COMFYUI_TIMEOUT": "300",
            "COMFYUI_MAX_RETRIES": "3",
            "COMFYUI_RETRY_DELAY": "5",
            "COMFYUI_CLIENT_ID": self.generate_client_id(),
            
            # 文件存储配置
            "UPLOADS_DIR": "uploads",
            "OUTPUTS_DIR": "outputs",
            "WORKFLOWS_DIR": "workflows",
            "CONFIGS_DIR": "configs",
            "MAX_FILE_SIZE": "10485760",
            "ALLOWED_EXTENSIONS": "jpg,jpeg,png,gif,bmp,webp",
            "FILE_RETENTION_HOURS": "24",
            
            # 时间配置
            "SIGNATURE_TIMEOUT": "300",
            "TOKEN_EXPIRY_MINUTES": "60",
            
            # 速率限制
            "RATE_LIMIT_PER_IP": "60",
            "RATE_LIMIT_PER_REQUEST": "30",
            
            # 高级配置
            "TASK_TIMEOUT": "300",
            "TASK_RETENTION_HOURS": "24",
            "MAX_CONCURRENT_TASKS": "10",
            "HTTP_CONNECTION_LIMIT": "100",
            "HTTP_CONNECTION_PER_HOST": "30",
            "HTTP_TIMEOUT_TOTAL": "120",
            "HTTP_TIMEOUT_CONNECT": "10",
            
            # 监控配置
            "HEALTH_CHECK_INTERVAL": "30",
            "PERFORMANCE_MONITORING": "true",
            "REQUEST_LOGGING": "true",
            "SLOW_QUERY_THRESHOLD": "5.0",
            
            # 多租户配置
            "REQUEST_ID_HEADER": "x-request-id",
            "MIN_REQUEST_ID_LENGTH": "3",
            "MAX_REQUEST_ID_LENGTH": "64",
            "MAX_TASKS_PER_CLIENT": "100",
            "MAX_FILES_PER_CLIENT": "1000",
            "MAX_STORAGE_PER_CLIENT": "1073741824",
            
            # 缓存配置
            "CACHE_TTL": "3600",
            
            # 安全增强选项
            "SECURE_COOKIES": "true",
            "SESSION_SECURE": "true",
            "SESSION_HTTPONLY": "true",
            "SESSION_SAMESITE": "strict",
            "MAX_REQUEST_SIZE": "10485760",
            
            # 密码复杂度
            "PASSWORD_MIN_LENGTH": "8",
            "PASSWORD_REQUIRE_UPPERCASE": "true",
            "PASSWORD_REQUIRE_LOWERCASE": "true",
            "PASSWORD_REQUIRE_NUMBERS": "true",
            "PASSWORD_REQUIRE_SYMBOLS": "true",
            
            # 国际化
            "DEFAULT_LANGUAGE": "zh-CN",
            "TIMEZONE": "Asia/Shanghai",
            
            # 开发和测试
            "TEST_MODE": "false",
            "DEV_TOOLS": "false",
            "ENABLE_DOCS": "false"
        }
        
        # 环境特定配置
        if env_type == "development":
            base_config.update({
                "DEBUG": "true",
                "LOG_LEVEL": "DEBUG",
                "ALLOWED_IPS": "127.0.0.1,::1,192.168.0.0/24,10.0.0.0/8",
                "ENFORCE_HTTPS": "false",
                "CORS_ORIGINS": "*",
                "ENABLE_DOCS": "true",
                "DEV_TOOLS": "true",
                "RATE_LIMIT_PER_IP": "120",
                "RATE_LIMIT_PER_REQUEST": "60"
            })
        elif env_type == "production":
            base_config.update({
                "DEBUG": "false",
                "LOG_LEVEL": "WARNING",
                "ALLOWED_IPS": "10.0.1.100,10.0.1.101",  # 需要用户自定义
                "ENFORCE_HTTPS": "true",
                "CORS_ORIGINS": "https://your-frontend.com",  # 需要用户自定义
                "ENABLE_DOCS": "false",
                "DEV_TOOLS": "false",
                "WORKERS": "4",
                "LOG_FILE": "logs/app.log"
            })
        elif env_type == "staging":
            base_config.update({
                "DEBUG": "false",
                "LOG_LEVEL": "INFO",
                "ALLOWED_IPS": "127.0.0.1,::1,192.168.0.0/24,10.0.0.0/8",
                "ENFORCE_HTTPS": "true",
                "CORS_ORIGINS": "https://staging.your-frontend.com",
                "ENABLE_DOCS": "true",
                "DEV_TOOLS": "true",
                "WORKERS": "2"
            })
        
        return base_config
    
    def generate_config_file(self, env_type: str, output_file: str) -> bool:
        """生成配置文件"""
        try:
            config = self.get_environment_defaults(env_type)
            
            # 生成配置文件内容
            content = []
            content.append(f"# ComfyUI工作流服务器 - {env_type.upper()}环境配置")
            content.append(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content.append(f"# 环境类型: {env_type}")
            content.append("")
            content.append("# ⚠️ 警告: 请妥善保管此文件，包含敏感信息")
            content.append("# ⚠️ 生产环境请修改默认密钥和IP配置")
            content.append("")
            
            # 按分类输出配置
            security_vars = ["API_SECRET_KEY", "JWT_SECRET_KEY", "ENCRYPTION_KEY"]
            network_vars = ["ALLOWED_IPS", "ENFORCE_HTTPS", "CORS_ORIGINS"]
            timing_vars = ["SIGNATURE_TIMEOUT", "TOKEN_EXPIRY_MINUTES"]
            rate_vars = ["RATE_LIMIT_PER_IP", "RATE_LIMIT_PER_REQUEST"]
            
            # 核心安全配置
            content.append("# =============================================================================")
            content.append("# 🔐 核心安全配置")
            content.append("# =============================================================================")
            content.append("")
            for var in security_vars:
                if var in config:
                    content.append(f"{var}={config[var]}")
            content.append("")
            
            # 网络安全配置
            content.append("# =============================================================================")
            content.append("# 🌐 网络安全配置")
            content.append("# =============================================================================")
            content.append("")
            for var in network_vars:
                if var in config:
                    content.append(f"{var}={config[var]}")
            content.append("")
            
            # 时间配置
            content.append("# =============================================================================")
            content.append("# ⏱️ 安全时间配置")
            content.append("# =============================================================================")
            content.append("")
            for var in timing_vars:
                if var in config:
                    content.append(f"{var}={config[var]}")
            content.append("")
            
            # 速率限制配置
            content.append("# =============================================================================")
            content.append("# 🚦 速率限制配置")
            content.append("# =============================================================================")
            content.append("")
            for var in rate_vars:
                if var in config:
                    content.append(f"{var}={config[var]}")
            content.append("")
            
            # 其他配置
            content.append("# =============================================================================")
            content.append("# 🚀 应用配置")
            content.append("# =============================================================================")
            content.append("")
            other_vars = [k for k in config.keys() if k not in security_vars + network_vars + timing_vars + rate_vars]
            for var in sorted(other_vars):
                content.append(f"{var}={config[var]}")
            
            # 写入文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            print(f"✅ 配置文件已生成: {output_file}")
            print(f"📝 环境类型: {env_type}")
            print(f"🔐 包含 {len(security_vars)} 个安全密钥")
            print(f"⚙️ 包含 {len(config)} 个配置项")
            
            # 安全提醒
            if env_type == "production":
                print("\n🚨 生产环境安全提醒:")
                print("1. 请修改 ALLOWED_IPS 为实际的服务器IP")
                print("2. 请修改 CORS_ORIGINS 为实际的前端域名")
                print("3. 请确保所有密钥都是随机生成的")
                print("4. 建议定期轮换安全密钥")
            
            return True
            
        except Exception as e:
            print(f"❌ 生成配置文件失败: {e}")
            return False
    
    def validate_config_file(self, config_file: str) -> Tuple[bool, List[str]]:
        """验证配置文件"""
        errors = []
        warnings = []
        
        try:
            if not os.path.exists(config_file):
                errors.append(f"配置文件不存在: {config_file}")
                return False, errors
            
            # 读取配置文件
            config = {}
            with open(config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
            
            # 必需的配置检查
            required_keys = [
                "API_SECRET_KEY", "JWT_SECRET_KEY", "ALLOWED_IPS",
                "HOST", "PORT", "COMFYUI_HOST", "COMFYUI_PORT"
            ]
            
            for key in required_keys:
                if key not in config:
                    errors.append(f"缺少必需配置: {key}")
                elif not config[key]:
                    errors.append(f"配置值为空: {key}")
            
            # 安全检查
            if "API_SECRET_KEY" in config:
                if len(config["API_SECRET_KEY"]) < 32:
                    errors.append("API_SECRET_KEY 长度不足32字符")
                elif config["API_SECRET_KEY"] == "your-64-char-api-secret-key-change-in-production":
                    warnings.append("API_SECRET_KEY 使用默认值，生产环境不安全")
            
            if "JWT_SECRET_KEY" in config:
                if len(config["JWT_SECRET_KEY"]) < 32:
                    errors.append("JWT_SECRET_KEY 长度不足32字符")
                elif config["JWT_SECRET_KEY"] == "your-64-char-jwt-secret-key-change-in-production":
                    warnings.append("JWT_SECRET_KEY 使用默认值，生产环境不安全")
            
            # IP地址验证
            if "ALLOWED_IPS" in config:
                if not self.validate_ip_list(config["ALLOWED_IPS"]):
                    errors.append("ALLOWED_IPS 格式不正确")
            
            # 端口验证
            for port_key in ["PORT", "COMFYUI_PORT"]:
                if port_key in config:
                    try:
                        port = int(config[port_key])
                        if port < 1 or port > 65535:
                            errors.append(f"{port_key} 端口范围不正确: {port}")
                    except ValueError:
                        errors.append(f"{port_key} 不是有效的端口号: {config[port_key]}")
            
            # 调试模式检查
            if config.get("DEBUG", "false").lower() == "true":
                warnings.append("DEBUG 模式已启用，生产环境不推荐")
            
            # HTTPS检查
            if config.get("ENFORCE_HTTPS", "false").lower() == "false":
                warnings.append("ENFORCE_HTTPS 已禁用，生产环境建议启用")
            
            # CORS检查
            if config.get("CORS_ORIGINS") == "*":
                warnings.append("CORS_ORIGINS 设为通配符，生产环境不安全")
            
            # 输出验证结果
            print(f"📋 配置文件验证结果: {config_file}")
            print(f"✅ 已验证 {len(config)} 个配置项")
            
            if errors:
                print(f"\n❌ 发现 {len(errors)} 个错误:")
                for error in errors:
                    print(f"  - {error}")
            
            if warnings:
                print(f"\n⚠️ 发现 {len(warnings)} 个警告:")
                for warning in warnings:
                    print(f"  - {warning}")
            
            if not errors and not warnings:
                print("\n🎉 配置文件验证通过，无错误和警告")
            
            return len(errors) == 0, errors + warnings
            
        except Exception as e:
            errors.append(f"验证过程出错: {e}")
            return False, errors
    
    def show_config_info(self, config_file: str):
        """显示配置文件信息"""
        if not os.path.exists(config_file):
            print(f"❌ 配置文件不存在: {config_file}")
            return
        
        config = {}
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        
        print(f"📋 配置文件信息: {config_file}")
        print(f"📁 文件大小: {os.path.getsize(config_file)} 字节")
        print(f"⚙️ 配置项数量: {len(config)}")
        
        # 显示关键配置
        key_configs = {
            "应用信息": ["APP_NAME", "APP_VERSION", "HOST", "PORT"],
            "安全配置": ["API_SECRET_KEY", "JWT_SECRET_KEY", "ALLOWED_IPS"],
            "ComfyUI": ["COMFYUI_HOST", "COMFYUI_PORT"],
            "调试模式": ["DEBUG", "LOG_LEVEL"],
            "HTTPS": ["ENFORCE_HTTPS"]
        }
        
        for category, keys in key_configs.items():
            print(f"\n{category}:")
            for key in keys:
                if key in config:
                    value = config[key]
                    if "SECRET" in key or "KEY" in key:
                        value = f"[已设置，{len(value)}字符]"
                    print(f"  {key}: {value}")
                else:
                    print(f"  {key}: [未设置]")
    
    def generate_keys_only(self):
        """只生成密钥"""
        print("🔐 生成安全密钥:")
        print(f"API_SECRET_KEY={self.generate_secure_key()}")
        print(f"JWT_SECRET_KEY={self.generate_secure_key()}")
        print(f"ENCRYPTION_KEY={self.generate_secure_key()}")
        print(f"COMFYUI_CLIENT_ID={self.generate_client_id()}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ComfyUI工作流服务器配置生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
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
        """
    )
    
    parser.add_argument(
        '--env', 
        choices=['development', 'production', 'staging'],
        help='环境类型'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='输出文件路径'
    )
    
    parser.add_argument(
        '--validate', '-v',
        help='验证配置文件'
    )
    
    parser.add_argument(
        '--info', '-i',
        help='显示配置文件信息'
    )
    
    parser.add_argument(
        '--keys-only', '-k',
        action='store_true',
        help='只生成密钥'
    )
    
    args = parser.parse_args()
    
    generator = ConfigGenerator()
    
    # 只生成密钥
    if args.keys_only:
        generator.generate_keys_only()
        return
    
    # 验证配置文件
    if args.validate:
        success, messages = generator.validate_config_file(args.validate)
        sys.exit(0 if success else 1)
    
    # 显示配置信息
    if args.info:
        generator.show_config_info(args.info)
        return
    
    # 生成配置文件
    if args.env and args.output:
        success = generator.generate_config_file(args.env, args.output)
        sys.exit(0 if success else 1)
    
    # 显示帮助
    parser.print_help()

if __name__ == "__main__":
    main() 