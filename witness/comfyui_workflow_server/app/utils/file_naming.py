"""
文件命名工具

提供文件命名规范的验证和生成功能
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
    
    # 文件命名模式: {style_id}_{user_id}_{type}.{ext}
    FILENAME_PATTERN = re.compile(r'^([a-zA-Z0-9_]+)_([a-zA-Z0-9_]+)_(input|output)\.([a-zA-Z0-9]+)$')
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
    
    # 允许的文件类型
    ALLOWED_TYPES = {"input", "output"}
    
    @classmethod
    def parse_filename(cls, filename: str) -> Tuple[str, str, str, str]:
        """
        解析文件名
        
        Args:
            filename: 文件名
        
        Returns:
            Tuple[str, str, str, str]: (style_id, user_id, file_type, extension)
        
        Raises:
            RPCInvalidParams: 文件名格式不符合规范
        """
        match = cls.FILENAME_PATTERN.match(filename)
        if not match:
            raise RPCInvalidParams(
                message="文件名格式不符合规范",
                field="filename",
                value={
                    "filename": filename,
                    "expected_pattern": "{style_id}_{user_id}_{input|output}.{ext}",
                    "example": "clay_style_alice_input.jpg"
                }
            )
        
        style_id, user_id, file_type, extension = match.groups()
        
        # 验证扩展名
        if f".{extension.lower()}" not in cls.ALLOWED_EXTENSIONS:
            raise RPCInvalidParams(
                message=f"不支持的文件扩展名: .{extension}",
                field="filename",
                value={
                    "filename": filename,
                    "extension": f".{extension}",
                    "allowed_extensions": list(cls.ALLOWED_EXTENSIONS)
                }
            )
        
        return style_id, user_id, file_type, extension.lower()
    
    @classmethod
    def build_filename(cls, style_id: str, user_id: str, file_type: str, extension: str = "jpg") -> str:
        """
        构建文件名
        
        Args:
            style_id: 风格ID
            user_id: 用户ID
            file_type: 文件类型 (input/output)
            extension: 文件扩展名 (不含点号)
        
        Returns:
            str: 构建的文件名
        
        Raises:
            RPCInvalidParams: 参数无效
        """
        # 验证参数
        if not style_id or not isinstance(style_id, str):
            raise RPCInvalidParams("风格ID不能为空", "style_id", style_id)
        
        if not user_id or not isinstance(user_id, str):
            raise RPCInvalidParams("用户ID不能为空", "user_id", user_id)
        
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
        
        # 清理和验证ID
        style_id = cls._clean_id(style_id)
        user_id = cls._clean_id(user_id)
        
        filename = f"{style_id}_{user_id}_{file_type}{extension.lower()}"
        return filename
    
    @classmethod
    def validate_url_filename(cls, url: str, expected_style_id: str, expected_user_id: str, expected_type: str = "input") -> str:
        """
        验证URL中的文件名是否符合规范
        
        Args:
            url: 图片URL
            expected_style_id: 期望的风格ID
            expected_user_id: 期望的用户ID  
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
            style_id, user_id, file_type, extension = cls.parse_filename(filename)
            
            # 验证参数匹配
            if style_id != expected_style_id:
                raise RPCInvalidParams(
                    "URL中的风格ID与请求参数不匹配",
                    "filename",
                    {
                        "url_style_id": style_id,
                        "expected_style_id": expected_style_id,
                        "filename": filename
                    }
                )
            
            if user_id != expected_user_id:
                raise RPCInvalidParams(
                    "URL中的用户ID与请求参数不匹配",
                    "filename", 
                    {
                        "url_user_id": user_id,
                        "expected_user_id": expected_user_id,
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
        style_id, user_id, file_type, extension = cls.parse_filename(input_filename)
        
        if file_type != "input":
            raise RPCInvalidParams(
                "只能从输入文件名生成输出文件名",
                "input_filename",
                input_filename
            )
        
        # 输出文件通常使用PNG格式以保证质量
        return cls.build_filename(style_id, user_id, "output", "png")
    
    @classmethod
    def _clean_id(cls, id_str: str) -> str:
        """清理ID字符串，移除不安全字符"""
        # 只保留字母、数字和下划线
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', id_str)
        
        # 移除连续的下划线
        cleaned = re.sub(r'_+', '_', cleaned)
        
        # 移除首尾下划线
        cleaned = cleaned.strip('_')
        
        if not cleaned:
            raise RPCInvalidParams(
                "ID不能为空或只包含特殊字符",
                "id",
                id_str
            )
        
        return cleaned
    
    @classmethod
    def validate_style_id(cls, style_id: str) -> str:
        """验证和清理风格ID"""
        if not style_id or not isinstance(style_id, str):
            raise RPCInvalidParams("风格ID不能为空", "style_id", style_id)
        
        return cls._clean_id(style_id)
    
    @classmethod
    def validate_user_id(cls, user_id: str) -> str:
        """验证和清理用户ID"""
        if not user_id or not isinstance(user_id, str):
            raise RPCInvalidParams("用户ID不能为空", "user_id", user_id)
        
        return cls._clean_id(user_id)
    
    @classmethod
    def extract_file_info(cls, filename: str) -> dict:
        """
        从文件名提取信息字典
        
        Args:
            filename: 文件名
        
        Returns:
            dict: 文件信息
        """
        style_id, user_id, file_type, extension = cls.parse_filename(filename)
        
        return {
            "style_id": style_id,
            "user_id": user_id,
            "file_type": file_type,
            "extension": extension,
            "filename": filename
        }