"""
帮助工具模块

提供各种实用工具函数，包括图像处理、URL验证、文件操作等。
"""

import re
import hashlib
import secrets
import ipaddress
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, unquote
import aiohttp
import aiofiles
from pathlib import Path
import logging
import time
import json
import base64
from PIL import Image
import io
import asyncio

logger = logging.getLogger(__name__)

# URL验证相关
def is_valid_url(url: str) -> bool:
    """验证URL是否有效"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def is_safe_url(url: str) -> bool:
    """检查URL是否安全（防止SSRF攻击）"""
    try:
        parsed = urlparse(url)
        
        # 只允许HTTP和HTTPS协议
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # 检查主机名
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # 防止访问内网地址
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ipaddress.AddressValueError:
            # 域名情况，检查是否为本地域名
            if hostname in ['localhost', '127.0.0.1', '0.0.0.0'] or hostname.endswith('.local'):
                return False
        
        return True
        
    except Exception:
        return False

def extract_domain(url: str) -> Optional[str]:
    """从URL中提取域名"""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None

# 字符串处理
def sanitize_filename(filename: str) -> str:
    """清理文件名，移除不安全字符"""
    # 移除或替换不安全字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除控制字符
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    # 限制长度
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]
    
    return filename.strip()

def generate_unique_id(prefix: str = "", length: int = 32) -> str:
    """生成唯一ID"""
    unique_part = secrets.token_hex(length // 2)
    return f"{prefix}_{unique_part}" if prefix else unique_part

def calculate_file_hash(file_path: Path, algorithm: str = 'sha256') -> str:
    """计算文件哈希值"""
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()

# 时间处理
def format_duration(seconds: float) -> str:
    """格式化时长"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds//60:.0f}m {seconds%60:.0f}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:.0f}h {minutes:.0f}m"

def get_timestamp() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)

# 数据验证
def validate_user_id(user_id: str) -> bool:
    """验证用户ID格式"""
    if not user_id or not isinstance(user_id, str):
        return False
    
    # 长度检查
    if len(user_id) < 1 or len(user_id) > 100:
        return False
    
    # 格式检查（只允许字母、数字、下划线、连字符）
    if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
        return False
    
    return True

def validate_image_url(url: str) -> Tuple[bool, Optional[str]]:
    """验证图像URL"""
    if not url or not isinstance(url, str):
        return False, "URL不能为空"
    
    if not is_valid_url(url):
        return False, "URL格式无效"
    
    if not is_safe_url(url):
        return False, "URL不安全，可能存在SSRF风险"
    
    if len(url) > 2048:
        return False, "URL长度超过限制"
    
    return True, None

def validate_strength(strength: float) -> bool:
    """验证强度参数"""
    return isinstance(strength, (int, float)) and 0.1 <= strength <= 1.0

# 图像处理
async def get_image_info(url: str) -> Optional[Dict[str, Any]]:
    """获取图像信息"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                
                content_type = response.headers.get('content-type', '').lower()
                content_length = response.headers.get('content-length')
                
                return {
                    'content_type': content_type,
                    'size_bytes': int(content_length) if content_length else None,
                    'is_image': any(img_type in content_type for img_type in ['image/jpeg', 'image/png', 'image/webp', 'image/gif'])
                }
    except Exception as e:
        logger.warning(f"获取图像信息失败: {e}")
        return None

def validate_image_data(image_data: bytes, max_size: int = 10 * 1024 * 1024) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """验证图像数据"""
    try:
        # 检查大小
        if len(image_data) > max_size:
            return False, f"图像过大，最大允许 {max_size // (1024*1024)}MB", None
        
        # 尝试打开图像
        with Image.open(io.BytesIO(image_data)) as img:
            info = {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height
            }
            
            # 检查图像尺寸
            if img.width > 8192 or img.height > 8192:
                return False, "图像尺寸过大，最大支持8192x8192", info
            
            if img.width < 64 or img.height < 64:
                return False, "图像尺寸过小，最小支持64x64", info
            
            return True, None, info
            
    except Exception as e:
        return False, f"无效的图像数据: {e}", None

# 文件操作
async def ensure_directory(path: Path):
    """确保目录存在"""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"创建目录失败 {path}: {e}")
        raise

async def save_file_safely(file_path: Path, content: bytes, max_size: int = 100 * 1024 * 1024):
    """安全保存文件"""
    if len(content) > max_size:
        raise ValueError(f"文件过大，最大允许 {max_size // (1024*1024)}MB")
    
    # 确保目录存在
    await ensure_directory(file_path.parent)
    
    # 使用临时文件，原子性写入
    temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
    
    try:
        async with aiofiles.open(temp_path, 'wb') as f:
            await f.write(content)
        
        # 原子性重命名
        temp_path.rename(file_path)
        
    except Exception as e:
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
        raise e

async def read_file_safely(file_path: Path, max_size: int = 100 * 1024 * 1024) -> bytes:
    """安全读取文件"""
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    file_size = file_path.stat().st_size
    if file_size > max_size:
        raise ValueError(f"文件过大，最大允许 {max_size // (1024*1024)}MB")
    
    async with aiofiles.open(file_path, 'rb') as f:
        return await f.read()

# JSON处理
def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """安全解析JSON"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """安全序列化JSON"""
    try:
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError):
        return default

# 配置处理
def parse_list_from_env(env_value: str, separator: str = ',') -> List[str]:
    """从环境变量解析列表"""
    if not env_value:
        return []
    
    return [item.strip().strip('"\'') for item in env_value.split(separator) if item.strip()]

def format_bytes(bytes_value: int) -> str:
    """格式化字节大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f}{unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f}PB"

# 性能相关
class RateLimiter:
    """简单的速率限制器"""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def is_allowed(self) -> bool:
        """检查是否允许调用"""
        now = time.time()
        
        # 移除过期的调用记录
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        # 检查是否超过限制
        if len(self.calls) >= self.max_calls:
            return False
        
        # 记录此次调用
        self.calls.append(now)
        return True
    
    def get_wait_time(self) -> float:
        """获取需要等待的时间"""
        if not self.calls:
            return 0.0
        
        now = time.time()
        oldest_call = min(self.calls)
        return max(0.0, self.time_window - (now - oldest_call))

# Base64编码/解码
def safe_base64_encode(data: bytes) -> str:
    """安全的Base64编码"""
    try:
        return base64.b64encode(data).decode('utf-8')
    except Exception:
        return ""

def safe_base64_decode(data: str) -> Optional[bytes]:
    """安全的Base64解码"""
    try:
        return base64.b64decode(data)
    except Exception:
        return None

# 缓存键生成
def generate_cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    # 将所有参数序列化为字符串
    key_parts = []
    
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(safe_json_dumps(arg))
    
    for key, value in sorted(kwargs.items()):
        if isinstance(value, (str, int, float, bool)):
            key_parts.append(f"{key}:{value}")
        else:
            key_parts.append(f"{key}:{safe_json_dumps(value)}")
    
    # 生成哈希
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()

# 错误重试装饰器
def retry_on_exception(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{max_retries}): {e}, {wait_time}秒后重试")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"函数 {func.__name__} 最终失败: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator 