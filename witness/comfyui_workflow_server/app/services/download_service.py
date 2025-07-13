"""
文件下载服务

负责从外部URL下载图片文件，并按照规范保存到本地存储
"""

import asyncio
import aiohttp
import aiofiles
import logging
import time
from pathlib import Path
from typing import Optional, Tuple, Callable
from urllib.parse import urlparse
import hashlib

from ..rpc.exceptions import RPCDownloadError
from ..rpc.error_codes import ErrorCodes
from ..config import get_settings

logger = logging.getLogger(__name__)


class DownloadService:
    """文件下载服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self._session: Optional[aiohttp.ClientSession] = None
        
        # 下载配置
        self.timeout = 30
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_formats = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
        self.user_agent = "ComfyUI-Workflow-Server/2.0"
        self.max_redirects = 3
        
        # 存储路径
        self.temp_dir = self.settings.storage.uploads_dir / "temp"
        self.inputs_dir = self.settings.storage.uploads_dir / "inputs"
        
        # 确保目录存在
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.inputs_dir.mkdir(exist_ok=True, parents=True)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._close_session()
    
    async def _ensure_session(self):
        """确保HTTP会话存在"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {"User-Agent": self.user_agent}
            
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=aiohttp.TCPConnector(limit=10)
            )
    
    async def _close_session(self):
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _get_file_extension(self, url: str, content_type: str = None) -> str:
        """从URL或Content-Type获取文件扩展名"""
        # 首先尝试从URL获取
        parsed_url = urlparse(url)
        path = Path(parsed_url.path)
        if path.suffix.lower() in self.allowed_formats:
            return path.suffix.lower()
        
        # 从Content-Type获取
        if content_type:
            content_type = content_type.lower()
            if "jpeg" in content_type or "jpg" in content_type:
                return ".jpg"
            elif "png" in content_type:
                return ".png"
            elif "webp" in content_type:
                return ".webp"
            elif "bmp" in content_type:
                return ".bmp"
            elif "gif" in content_type:
                return ".gif"
        
        # 默认返回jpg
        return ".jpg"
    
    def _validate_file_size(self, content_length: Optional[str]):
        """验证文件大小"""
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_file_size:
                    raise RPCDownloadError(
                        code=ErrorCodes.FILE_TOO_LARGE,
                        message=f"文件过大: {size / 1024 / 1024:.2f}MB，最大允许: {self.max_file_size / 1024 / 1024}MB"
                    )
            except ValueError:
                pass
    
    async def download_image(
        self, 
        url: str, 
        expected_filename: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Tuple[str, dict]:
        """
        下载图片文件
        
        Args:
            url: 图片URL
            expected_filename: 期望的文件名（用于验证）
            progress_callback: 进度回调函数
        
        Returns:
            Tuple[str, dict]: (保存的文件路径, 文件信息)
        """
        await self._ensure_session()
        
        logger.info(f"开始下载图片: {url}")
        start_time = time.time()
        
        try:
            # 发起HTTP请求
            async with self._session.get(url, allow_redirects=True) as response:
                # 检查响应状态
                if response.status != 200:
                    raise RPCDownloadError(
                        code=ErrorCodes.DOWNLOAD_FAILED,
                        message=f"下载失败，HTTP状态码: {response.status}",
                        url=url,
                        details=f"服务器返回: {response.reason}"
                    )
                
                # 验证Content-Type（更宽松的验证）
                content_type = response.headers.get('content-type', '')
                
                # 如果有明确的图片类型，验证它
                if content_type and any(img_type in content_type.lower() for img_type in ['image/', 'jpeg', 'png', 'webp', 'bmp', 'gif']):
                    # 明确是图片类型，通过验证
                    pass
                elif content_type and content_type.lower().startswith('text/'):
                    # 如果是text类型，需要进一步检查URL扩展名
                    url_lower = url.lower()
                    if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']):
                        # URL看起来像图片，可能是服务器MIME类型配置问题，允许通过
                        logger.warning(f"Content-Type为text但URL像图片: {url}, Content-Type: {content_type}")
                    else:
                        raise RPCDownloadError(
                            code=ErrorCodes.INVALID_FILE_FORMAT,
                            message=f"不支持的内容类型: {content_type}",
                            url=url
                        )
                elif content_type:
                    # 其他明确非图片的类型
                    raise RPCDownloadError(
                        code=ErrorCodes.INVALID_FILE_FORMAT,
                        message=f"不支持的内容类型: {content_type}",
                        url=url
                    )
                # 如果没有Content-Type，继续尝试下载并依据内容判断
                
                # 验证文件大小
                content_length = response.headers.get('content-length')
                self._validate_file_size(content_length)
                
                # 获取文件扩展名
                file_ext = self._get_file_extension(url, content_type)
                
                # 生成临时文件路径
                temp_filename = f"temp_{int(time.time())}_{hashlib.md5(url.encode()).hexdigest()[:8]}{file_ext}"
                temp_path = self.temp_dir / temp_filename
                
                # 下载文件内容
                downloaded_size = 0
                total_size = int(content_length) if content_length else 0
                
                async with aiofiles.open(temp_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 检查文件大小限制
                        if downloaded_size > self.max_file_size:
                            # 删除临时文件
                            temp_path.unlink(missing_ok=True)
                            raise RPCDownloadError(
                                code=ErrorCodes.FILE_TOO_LARGE,
                                message=f"文件过大: {downloaded_size / 1024 / 1024:.2f}MB",
                                url=url
                            )
                        
                        # 调用进度回调
                        if progress_callback and total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            try:
                                progress_callback(progress)
                            except Exception as e:
                                logger.warning(f"进度回调失败: {e}")
                
                # 移动到最终位置
                final_path = self.inputs_dir / expected_filename
                temp_path.rename(final_path)
                
                download_time = time.time() - start_time
                
                file_info = {
                    "filename": expected_filename,
                    "path": str(final_path),
                    "size": downloaded_size,
                    "format": file_ext[1:],  # 去掉点号
                    "content_type": content_type,
                    "download_time": download_time,
                    "original_url": url
                }
                
                logger.info(f"图片下载完成: {expected_filename}, 大小: {downloaded_size / 1024:.1f}KB, 耗时: {download_time:.2f}s")
                
                return str(final_path), file_info
                
        except aiohttp.ClientError as e:
            raise RPCDownloadError(
                code=ErrorCodes.NETWORK_ERROR,
                message=f"网络连接错误: {str(e)}",
                url=url,
                details=str(e)
            )
        except asyncio.TimeoutError:
            raise RPCDownloadError(
                code=ErrorCodes.DOWNLOAD_TIMEOUT,
                message=f"下载超时（{self.timeout}秒）",
                url=url
            )
        except RPCDownloadError:
            # 重新抛出RPC下载错误
            raise
        except Exception as e:
            logger.error(f"下载异常: {str(e)}", exc_info=True)
            raise RPCDownloadError(
                code=ErrorCodes.DOWNLOAD_FAILED,
                message=f"下载失败: {str(e)}",
                url=url,
                details=str(e)
            )
    
    def cleanup_temp_files(self, max_age_hours: int = 2):
        """清理临时文件"""
        try:
            current_time = time.time()
            cleanup_count = 0
            
            for temp_file in self.temp_dir.glob("temp_*"):
                if temp_file.is_file():
                    file_age = current_time - temp_file.stat().st_mtime
                    if file_age > max_age_hours * 3600:
                        temp_file.unlink()
                        cleanup_count += 1
            
            if cleanup_count > 0:
                logger.info(f"清理了 {cleanup_count} 个临时文件")
                
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
    
    async def validate_url_accessible(self, url: str) -> bool:
        """验证URL是否可访问"""
        try:
            await self._ensure_session()
            async with self._session.head(url, allow_redirects=True) as response:
                return response.status == 200
        except:
            return False