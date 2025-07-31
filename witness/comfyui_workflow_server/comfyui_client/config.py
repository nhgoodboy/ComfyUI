"""
ComfyUI客户端配置管理

提供客户端的各种配置选项，包括超时、重试、连接池等设置。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ComfyUIClientConfig:
    """ComfyUI客户端配置类"""
    
    # 网络配置
    request_timeout: float = 30.0  # HTTP请求超时时间（秒）
    connect_timeout: float = 10.0  # 连接超时时间（秒）
    read_timeout: float = 300.0    # 读取超时时间（秒），对于长时间运行的任务
    
    # 重试配置
    max_retries: int = 3           # 最大重试次数
    retry_delay: float = 1.0       # 重试间隔（秒）
    retry_backoff: float = 2.0     # 重试延迟倍数（指数退避）
    
    # 连接池配置
    max_connections: int = 100     # 最大连接数
    max_connections_per_host: int = 30  # 每个主机的最大连接数
    
    # WebSocket配置
    websocket_timeout: float = 60.0     # WebSocket连接超时
    websocket_ping_interval: float = 30.0  # WebSocket心跳间隔
    websocket_debug: bool = False       # WebSocket调试模式
    
    # 日志配置
    log_level: str = "INFO"        # 日志级别
    log_requests: bool = False     # 是否记录请求日志
    log_responses: bool = False    # 是否记录响应日志
    
    # 文件上传配置
    max_file_size: int = 100 * 1024 * 1024  # 最大文件大小（100MB）
    chunk_size: int = 8192         # 文件上传块大小
    
    # 其他配置
    user_agent: str = "ComfyUI-Python-Client/2.0.0"
    enable_compression: bool = True  # 启用压缩
    use_api_prefix: bool = False     # 是否使用 /api 前缀
    
    # 高级配置
    verify_ssl: bool = True          # SSL 证书验证
    follow_redirects: bool = True    # 跟随重定向
    keep_alive: bool = True          # 保持连接
    tcp_keepalive: bool = True       # TCP 保活
    
    def __post_init__(self):
        """配置验证"""
        if self.request_timeout <= 0:
            raise ValueError("request_timeout 必须大于 0")
        if self.max_retries < 0:
            raise ValueError("max_retries 必须大于等于 0")
        if self.retry_delay < 0:
            raise ValueError("retry_delay 必须大于等于 0")
        if self.max_connections <= 0:
            raise ValueError("max_connections 必须大于 0")
        if self.max_file_size <= 0:
            raise ValueError("max_file_size 必须大于 0")
    
    @classmethod
    def create_default(cls) -> 'ComfyUIClientConfig':
        """创建默认配置"""
        return cls()
    
    @classmethod
    def create_fast(cls) -> 'ComfyUIClientConfig':
        """创建快速响应配置（适用于低延迟场景）"""
        return cls(
            request_timeout=10.0,
            connect_timeout=3.0,
            read_timeout=30.0,
            max_retries=1,
            retry_delay=0.5
        )
    
    @classmethod
    def create_robust(cls) -> 'ComfyUIClientConfig':
        """创建健壮配置（适用于不稳定网络环境）"""
        return cls(
            request_timeout=60.0,
            connect_timeout=15.0,
            read_timeout=600.0,
            max_retries=5,
            retry_delay=2.0,
            retry_backoff=2.5
        )
    
    def to_aiohttp_timeout(self) -> 'aiohttp.ClientTimeout':
        """转换为aiohttp超时配置"""
        import aiohttp
        return aiohttp.ClientTimeout(
            total=self.request_timeout,
            connect=self.connect_timeout,
            sock_read=self.read_timeout
        )
    
    def to_aiohttp_connector(self) -> 'aiohttp.TCPConnector':
        """转换为aiohttp连接器配置"""
        import aiohttp
        return aiohttp.TCPConnector(
            limit=self.max_connections,
            limit_per_host=self.max_connections_per_host,
            enable_cleanup_closed=True,
            verify_ssl=self.verify_ssl,
            keepalive_timeout=30 if self.keep_alive else 0
        )
    
    @classmethod
    def create_production(cls) -> 'ComfyUIClientConfig':
        """创建生产环境配置"""
        return cls(
            request_timeout=120.0,
            connect_timeout=10.0,
            read_timeout=300.0,
            max_retries=3,
            retry_delay=2.0,
            max_connections=50,
            max_connections_per_host=20,
            log_requests=False,
            log_responses=False,
            websocket_debug=False
        ) 