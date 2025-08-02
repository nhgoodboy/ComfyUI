"""
文件命名工具类

基于UUID的文件命名系统，支持多输入文件和单输出文件
文件命名格式：
- 输入文件：{task_file_id}_input_{param_name}.{ext}
- 输出文件：{task_file_id}_output.{ext}
"""

import re
import uuid
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from ..rpc.exceptions import RPCInvalidParams


class FileNamingUtils:
    """基于UUID的文件命名工具类"""
    
    # 允许的文件类型
    ALLOWED_INPUT_TYPES = ["input"]
    ALLOWED_OUTPUT_TYPES = ["output"]
    ALLOWED_TYPES = ALLOWED_INPUT_TYPES + ALLOWED_OUTPUT_TYPES
    
    # 文件名模式：task_file_id_type[_param].ext
    FILENAME_PATTERN = re.compile(r'^([a-f0-9\-]+)_(input|output)(?:_(.+))?\.([a-zA-Z0-9]+)$')
    
    @classmethod
    def generate_task_file_id(cls) -> str:
        """生成任务文件ID（UUID）"""
        return str(uuid.uuid4())
    
    @classmethod
    def build_input_filename(cls, task_file_id: str, param_name: str, extension: str = "jpg") -> str:
        """
        构建输入文件名
        
        Args:
            task_file_id: 任务文件ID
            param_name: 参数名（如：input_image, person_image）
            extension: 文件扩展名（不含点号）
        
        Returns:
            str: 输入文件名
        """
        if not task_file_id or not param_name:
            raise RPCInvalidParams("任务文件ID和参数名不能为空")
        
        # 清理扩展名
        extension = extension.lstrip('.').lower()
        
        return f"{task_file_id}_input_{param_name}.{extension}"
    
    @classmethod 
    def build_output_filename(cls, task_file_id: str, extension: str = "jpg") -> str:
        """
        构建输出文件名（单个输出）
        
        Args:
            task_file_id: 任务文件ID
            extension: 文件扩展名（不含点号）
        
        Returns:
            str: 输出文件名
        """
        if not task_file_id:
            raise RPCInvalidParams("任务文件ID不能为空")
        
        # 清理扩展名
        extension = extension.lstrip('.').lower()
        
        return f"{task_file_id}_output.{extension}"
    
    @classmethod
    def parse_filename(cls, filename: str) -> Tuple[str, str, Optional[str], str]:
        """
        解析文件名
        
        Args:
            filename: 文件名
        
        Returns:
            Tuple[str, str, Optional[str], str]: (task_file_id, file_type, param_name, extension)
        
        Raises:
            RPCInvalidParams: 文件名格式无效
        """
        if not filename or not isinstance(filename, str):
            raise RPCInvalidParams("文件名不能为空", "filename", filename)
        
        match = cls.FILENAME_PATTERN.match(filename)
        if not match:
            raise RPCInvalidParams(
                f"文件名格式无效。正确格式：task_file_id_type[_param].ext",
                "filename",
                value=filename
            )
        
        task_file_id, file_type, param_name, extension = match.groups()
        return task_file_id, file_type, param_name, extension.lower()
    
    @classmethod
    def get_task_files(cls, task_file_id: str, base_dir: str = "uploads") -> Dict[str, any]:
        """
        获取任务相关的所有文件
        
        Args:
            task_file_id: 任务文件ID
            base_dir: 基础目录
        
        Returns:
            Dict: {"input_files": {param_name: file_path}, "output_file": file_path}
        """
        import glob
        
        pattern = os.path.join(base_dir, f"{task_file_id}_*")
        files = glob.glob(pattern)
        
        result = {"input_files": {}, "output_file": None}
        
        for file_path in files:
            filename = os.path.basename(file_path)
            try:
                task_id, file_type, param_name, extension = cls.parse_filename(filename)
                
                if file_type == "input" and param_name:
                    result["input_files"][param_name] = file_path
                elif file_type == "output":
                    result["output_file"] = file_path
                    
            except RPCInvalidParams:
                # 忽略无效的文件名
                continue
        
        return result
    
    @classmethod
    def cleanup_task_files(cls, task_file_id: str, base_dir: str = "uploads") -> int:
        """
        清理任务相关的所有文件
        
        Args:
            task_file_id: 任务文件ID
            base_dir: 基础目录
        
        Returns:
            int: 删除的文件数量
        """
        import glob
        
        pattern = os.path.join(base_dir, f"{task_file_id}_*")
        files = glob.glob(pattern)
        
        deleted_count = 0
        for file_path in files:
            try:
                os.remove(file_path)
                deleted_count += 1
            except OSError:
                # 忽略删除失败的文件
                continue
        
        return deleted_count
    
    @classmethod
    def validate_task_file_id(cls, task_file_id: str) -> bool:
        """
        验证任务文件ID格式
        
        Args:
            task_file_id: 任务文件ID
        
        Returns:
            bool: 是否有效
        """
        if not task_file_id or not isinstance(task_file_id, str):
            return False
        
        # UUID格式验证
        uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
        return bool(uuid_pattern.match(task_file_id))
    
    # 向后兼容的方法（保留原有接口）
    @classmethod
    def validate_request_id(cls, request_id: str) -> str:
        """验证请求ID（保持原样，不再清理）"""
        if not request_id or not isinstance(request_id, str):
            raise RPCInvalidParams("请求ID不能为空", "request_id", request_id)
        return request_id