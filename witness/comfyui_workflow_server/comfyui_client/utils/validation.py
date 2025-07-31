"""
输入验证工具函数

提供常用的参数验证功能，确保API调用的数据质量。
"""

import os
import re
from typing import Any, Optional, Union, List
from pathlib import Path

from ..exceptions import ComfyUIValidationError


def validate_required_string(value: Any, parameter_name: str) -> str:
    """
    验证必需的字符串参数。
    
    :param value: 要验证的值
    :param parameter_name: 参数名称
    :return: 验证后的字符串
    :raises ComfyUIValidationError: 如果验证失败
    """
    if not isinstance(value, str):
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 必须是字符串类型",
            parameter=parameter_name,
            expected_type="str"
        )
    
    if not value.strip():
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 不能为空",
            parameter=parameter_name
        )
    
    return value.strip()


def validate_optional_string(value: Any, parameter_name: str) -> Optional[str]:
    """
    验证可选的字符串参数。
    
    :param value: 要验证的值
    :param parameter_name: 参数名称
    :return: 验证后的字符串或None
    :raises ComfyUIValidationError: 如果验证失败
    """
    if value is None:
        return None
    
    if not isinstance(value, str):
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 必须是字符串类型或None",
            parameter=parameter_name,
            expected_type="str | None"
        )
    
    stripped = value.strip()
    return stripped if stripped else None


def validate_positive_integer(value: Any, parameter_name: str) -> int:
    """
    验证正整数参数。
    
    :param value: 要验证的值
    :param parameter_name: 参数名称
    :return: 验证后的整数
    :raises ComfyUIValidationError: 如果验证失败
    """
    if not isinstance(value, int):
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 必须是整数类型",
            parameter=parameter_name,
            expected_type="int"
        )
    
    if value <= 0:
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 必须是正整数",
            parameter=parameter_name
        )
    
    return value


def validate_non_negative_integer(value: Any, parameter_name: str) -> int:
    """
    验证非负整数参数。
    
    :param value: 要验证的值
    :param parameter_name: 参数名称
    :return: 验证后的整数
    :raises ComfyUIValidationError: 如果验证失败
    """
    if not isinstance(value, int):
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 必须是整数类型",
            parameter=parameter_name,
            expected_type="int"
        )
    
    if value < 0:
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 必须是非负整数",
            parameter=parameter_name
        )
    
    return value


def validate_bytes_data(value: Any, parameter_name: str, max_size: Optional[int] = None) -> bytes:
    """
    验证字节数据。
    
    :param value: 要验证的值
    :param parameter_name: 参数名称
    :param max_size: 最大字节数，None表示不限制
    :return: 验证后的字节数据
    :raises ComfyUIValidationError: 如果验证失败
    """
    if not isinstance(value, bytes):
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 必须是bytes类型",
            parameter=parameter_name,
            expected_type="bytes"
        )
    
    if max_size is not None and len(value) > max_size:
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 超过最大大小限制 {max_size} 字节",
            parameter=parameter_name
        )
    
    return value


def validate_file_path(value: Any, parameter_name: str, must_exist: bool = False) -> str:
    """
    验证文件路径。
    
    :param value: 要验证的值
    :param parameter_name: 参数名称
    :param must_exist: 是否必须存在
    :return: 验证后的文件路径
    :raises ComfyUIValidationError: 如果验证失败
    """
    path_str = validate_required_string(value, parameter_name)
    
    # 检查是否包含非法字符
    illegal_chars = ['<', '>', '|', '"', '?', '*']
    for char in illegal_chars:
        if char in path_str:
            raise ComfyUIValidationError(
                f"参数 {parameter_name} 包含非法字符 '{char}'",
                parameter=parameter_name
            )
    
    if must_exist and not os.path.exists(path_str):
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 指定的文件不存在: {path_str}",
            parameter=parameter_name
        )
    
    return path_str


def validate_model_type(value: Any, parameter_name: str) -> str:
    """
    验证模型类型。
    
    :param value: 要验证的值
    :param parameter_name: 参数名称
    :return: 验证后的模型类型
    :raises ComfyUIValidationError: 如果验证失败
    """
    model_type = validate_required_string(value, parameter_name)
    
    # 常见的模型类型
    valid_types = {
        'checkpoints', 'loras', 'vae', 'clip', 'unet', 'clip_vision',
        'style_models', 'embeddings', 'hypernetworks', 'controlnet',
        'gligen', 'upscale_models', 'custom_nodes'
    }
    
    if model_type not in valid_types:
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 不是有效的模型类型: {model_type}",
            parameter=parameter_name
        )
    
    return model_type


def validate_dict_data(value: Any, parameter_name: str, required_keys: Optional[List[str]] = None) -> dict:
    """
    验证字典数据。
    
    :param value: 要验证的值
    :param parameter_name: 参数名称
    :param required_keys: 必需的键列表
    :return: 验证后的字典
    :raises ComfyUIValidationError: 如果验证失败
    """
    if not isinstance(value, dict):
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 必须是字典类型",
            parameter=parameter_name,
            expected_type="dict"
        )
    
    if required_keys:
        missing_keys = [key for key in required_keys if key not in value]
        if missing_keys:
            raise ComfyUIValidationError(
                f"参数 {parameter_name} 缺少必需的键: {missing_keys}",
                parameter=parameter_name
            )
    
    return value


def validate_url(value: Any, parameter_name: str) -> str:
    """
    验证URL格式。
    
    :param value: 要验证的值
    :param parameter_name: 参数名称
    :return: 验证后的URL
    :raises ComfyUIValidationError: 如果验证失败
    """
    url_str = validate_required_string(value, parameter_name)
    
    # 简单的URL格式检查
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url_str):
        raise ComfyUIValidationError(
            f"参数 {parameter_name} 不是有效的URL格式",
            parameter=parameter_name
        )
    
    return url_str 