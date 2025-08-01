"""
文件命名工具

提供简化的文件命名规范：{request_id}_{type}.{ext}
"""

import re
import logging
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse

from ..rpc.exceptions import RPCInvalidParams
from ..rpc.error_codes import ErrorCodes

logger = logging.getLogger(__name__)


class FileNamingUtils:
    """文件命名工具类"""
    
    # 文件命名模式: {request_id}_{type}.{ext}
    FILENAME_PATTERN = re.compile(r'^([a-zA-Z0-9\-]+)_(input|output)\.([a-zA-Z0-9]+)$')
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
    
    # 允许的文件类型
    ALLOWED_TYPES = {"input", "output"}
    
    @classmethod
    def parse_filename(cls, filename: str) -> Tuple[str, str, str]:
        """
        解析文件名
        
        Args:
            filename: 文件名
        
        Returns:
            Tuple[str, str, str]: (request_id, file_type, extension)
        
        Raises:
            RPCInvalidParams: 文件名格式不符合规范
        """
        if '.' not in filename:
            raise RPCInvalidParams(
                message="文件名必须包含扩展名",
                field="filename",
                value=filename
            )
        
        name_without_ext, extension = filename.rsplit('.', 1)
        
        # 检查是否符合命名模式
        match = cls.FILENAME_PATTERN.match(filename)
        if not match:
            raise RPCInvalidParams(
                message="文件名格式错误：应为{request_id}_{input|output}.{ext}",
                field="filename",
                value=filename
            )
        
        request_id, file_type, extension = match.groups()
        return request_id, file_type, extension.lower()
    
    @classmethod
    def build_filename(cls, request_id: str, file_type: str, extension: str = "jpg") -> str:
        """
        构建文件名
        
        Args:
            request_id: 请求ID
            file_type: 文件类型 (input/output)
            extension: 文件扩展名 (不含点号)
        
        Returns:
            str: 构建的文件名
        
        Raises:
            RPCInvalidParams: 参数无效
        """
        # 验证参数
        if not request_id or not isinstance(request_id, str):
            raise RPCInvalidParams("请求ID不能为空", "request_id", request_id)
        
        if file_type not in cls.ALLOWED_TYPES:
            raise RPCInvalidParams(
                f"文件类型必须是: {', '.join(cls.ALLOWED_TYPES)}",
                "file_type", 
                file_type
            )
        
        # 标准化扩展名
        if not extension.startswith('.'):
            extension = f".{extension}"
        
        if extension.lower() not in cls.ALLOWED_EXTENSIONS:
            raise RPCInvalidParams(
                f"不支持的文件扩展名: {extension}",
                "extension",
                {
                    "extension": extension,
                    "allowed": list(cls.ALLOWED_EXTENSIONS)
                }
            )
        
        # 清理和验证request_id
        request_id = cls._clean_request_id(request_id)
        
        filename = f"{request_id}_{file_type}{extension.lower()}"
        return filename
    
    @classmethod
    def validate_url_filename(cls, url: str, expected_request_id: str, expected_type: str = "input") -> str:
        """
        验证URL中的文件名是否符合规范
        
        Args:
            url: 图片URL
            expected_request_id: 期望的请求ID
            expected_type: 期望的文件类型
        
        Returns:
            str: 解析出的文件名
        
        Raises:
            RPCInvalidParams: 文件名不符合规范或参数不匹配
        """
        try:
            parsed_url = urlparse(url)
            filename = Path(parsed_url.path).name
            
            if not filename:
                raise RPCInvalidParams(
                    "URL中未找到文件名",
                    "image_url",
                    {"url": url}
                )
            
            # 解析文件名
            request_id, file_type, extension = cls.parse_filename(filename)
            
            # 验证参数匹配
            if request_id != expected_request_id:
                raise RPCInvalidParams(
                    "URL中的请求ID与请求参数不匹配",
                    "filename",
                    {
                        "url_request_id": request_id,
                        "expected_request_id": expected_request_id,
                        "filename": filename
                    }
                )
            
            if file_type != expected_type:
                raise RPCInvalidParams(
                    f"URL中的文件类型应为 '{expected_type}'",
                    "filename",
                    {
                        "url_file_type": file_type,
                        "expected_type": expected_type,
                        "filename": filename
                    }
                )
            
            return filename
            
        except RPCInvalidParams:
            raise
        except Exception as e:
            raise RPCInvalidParams(
                f"解析URL文件名失败: {str(e)}",
                "image_url",
                {"url": url, "error": str(e)}
            )
    
    @classmethod
    def get_output_filename(cls, input_filename: str) -> str:
        """
        根据输入文件名生成输出文件名
        
        Args:
            input_filename: 输入文件名
        
        Returns:
            str: 输出文件名
        """
        request_id, file_type, extension = cls.parse_filename(input_filename)
        
        if file_type != "input":
            raise RPCInvalidParams(
                "只能从输入文件名生成输出文件名",
                "input_filename",
                input_filename
            )
        
        # 输出文件通常使用PNG格式以保证质量
        return cls.build_filename(request_id, "output", "png")
    
    @classmethod
    def _clean_request_id(cls, request_id: str) -> str:
        """清理请求ID字符串，只保留字母、数字和连字符"""
        # 只保留字母、数字和连字符
        cleaned = re.sub(r'[^a-zA-Z0-9\-]', '', request_id)
        
        if not cleaned:
            raise RPCInvalidParams(
                "请求ID不能为空或只包含特殊字符",
                "request_id",
                request_id
            )
        
        return cleaned
    
    @classmethod
    def validate_request_id(cls, request_id: str) -> str:
        """验证和清理请求ID"""
        if not request_id or not isinstance(request_id, str):
            raise RPCInvalidParams("请求ID不能为空", "request_id", request_id)
        
        return cls._clean_request_id(request_id)
    
    @classmethod
    def extract_file_info(cls, filename: str) -> dict:
        """
        从文件名提取信息字典
        
        Args:
            filename: 文件名
        
        Returns:
            dict: 文件信息
        """
        request_id, file_type, extension = cls.parse_filename(filename)
        
        return {
            "request_id": request_id,
            "file_type": file_type,
            "extension": extension,
            "filename": filename
        }