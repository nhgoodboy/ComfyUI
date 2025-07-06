"""
参数类型定义和验证器
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)

class ParameterType(Enum):
    """参数类型枚举"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FILE = "file"
    ENUM = "enum"
    ARRAY = "array"
    OBJECT = "object"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"

class ParameterValidator:
    """参数验证器"""
    
    @staticmethod
    def validate_string(value: Any, min_length: Optional[int] = None, 
                       max_length: Optional[int] = None, 
                       pattern: Optional[str] = None) -> str:
        """验证字符串参数"""
        if not isinstance(value, str):
            raise ValueError(f"参数必须是字符串类型，实际类型: {type(value)}")
        
        if min_length is not None and len(value) < min_length:
            raise ValueError(f"字符串长度不能少于 {min_length} 个字符")
        
        if max_length is not None and len(value) > max_length:
            raise ValueError(f"字符串长度不能超过 {max_length} 个字符")
        
        if pattern is not None:
            if not re.match(pattern, value):
                raise ValueError(f"字符串不符合模式: {pattern}")
        
        return value
    
    @staticmethod
    def validate_number(value: Any, min_value: Optional[float] = None,
                       max_value: Optional[float] = None) -> float:
        """验证数值参数"""
        if not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValueError(f"参数必须是数值类型，实际类型: {type(value)}")
        
        if min_value is not None and value < min_value:
            raise ValueError(f"数值不能小于 {min_value}")
        
        if max_value is not None and value > max_value:
            raise ValueError(f"数值不能大于 {max_value}")
        
        return float(value)
    
    @staticmethod
    def validate_integer(value: Any, min_value: Optional[int] = None,
                        max_value: Optional[int] = None) -> int:
        """验证整数参数"""
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError(f"参数必须是整数类型，实际类型: {type(value)}")
        
        if min_value is not None and value < min_value:
            raise ValueError(f"整数不能小于 {min_value}")
        
        if max_value is not None and value > max_value:
            raise ValueError(f"整数不能大于 {max_value}")
        
        return int(value)
    
    @staticmethod
    def validate_enum(value: Any, enum_values: List[str]) -> str:
        """验证枚举参数"""
        if not isinstance(value, str):
            value = str(value)
        
        if value not in enum_values:
            raise ValueError(f"值必须是以下选项之一: {enum_values}，实际值: {value}")
        
        return value
    
    @staticmethod
    def validate_image_file(value: Any) -> str:
        """验证图像文件参数"""
        if not isinstance(value, str):
            raise ValueError(f"图像文件路径必须是字符串类型，实际类型: {type(value)}")
        
        if not value.strip():
            raise ValueError("图像文件路径不能为空")
        
        # 检查文件扩展名
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff']
        file_ext = value.lower().split('.')[-1] if '.' in value else ''
        
        if file_ext and f'.{file_ext}' not in valid_extensions:
            logger.warning(f"文件扩展名 '{file_ext}' 可能不被支持，支持的格式: {valid_extensions}")
        
        return value
    
    @staticmethod
    def validate_boolean(value: Any) -> bool:
        """验证布尔参数"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ('true', '1', 'yes', 'on'):
                return True
            elif value_lower in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"字符串布尔值必须是以下之一: true, false, 1, 0, yes, no, on, off，实际值: {value}")
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        raise ValueError(f"参数必须是布尔类型，实际类型: {type(value)}")
    
    @staticmethod
    def validate_array(value: Any, item_type: Optional[str] = None) -> List[Any]:
        """验证数组参数"""
        if not isinstance(value, list):
            raise ValueError(f"参数必须是数组类型，实际类型: {type(value)}")
        
        # TODO: 添加数组元素类型验证
        return value
    
    @staticmethod
    def validate_dict(value: Any) -> Dict[str, Any]:
        """验证字典参数"""
        if not isinstance(value, dict):
            raise ValueError(f"参数必须是字典类型，实际类型: {type(value)}")
        
        return value 