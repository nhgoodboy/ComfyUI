"""
RPC响应格式化器

负责格式化RPC响应数据
"""

import logging
from typing import Any, Dict
from .protocol import RPCResponse

logger = logging.getLogger(__name__)


class RPCFormatter:
    """RPC响应格式化器"""
    
    @staticmethod
    def format_success(result: Any, request_id: str) -> Dict[str, Any]:
        """格式化成功响应"""
        if not isinstance(result, dict):
            # 如果结果不是字典，包装成字典
            result = {"data": result}
        
        # 直接返回字典，避免Pydantic序列化问题
        return {
            "result": result,
            "id": request_id
        }
    
    @staticmethod
    def format_error(error_code: int, message: str, request_id: str, data: Any = None) -> Dict[str, Any]:
        """格式化错误响应"""
        error_dict = {
            "code": int(error_code),
            "message": str(message)
        }
        
        if data is not None:
            # 确保data是可序列化的
            try:
                import json
                # 尝试序列化data，如果失败就转换为字符串
                json.dumps(data)
                error_dict["data"] = data
            except (TypeError, ValueError):
                # 如果data不能序列化，转换为字符串
                error_dict["data"] = str(data)
        
        # 直接返回字典，避免Pydantic序列化问题
        return {
            "error": error_dict,
            "id": str(request_id) if request_id else None
        }
    
    @staticmethod
    def format_task_status(task) -> Dict[str, Any]:
        """格式化任务状态信息"""
        result = {
            "request_id": task.request_id,
            "user_id": task.user_id,
            "style_id": task.style_id,
            "status": task.status,
            "progress": task.progress,
            "stage": getattr(task, 'stage', 'unknown'),
            "message": getattr(task, 'message', ''),
            "created_at": task.created_at,
            "estimated_remaining": getattr(task, 'estimated_remaining', None)
        }
        
        # 添加可选字段
        if hasattr(task, 'started_at') and task.started_at:
            result["started_at"] = task.started_at
        
        if hasattr(task, 'completed_at') and task.completed_at:
            result["completed_at"] = task.completed_at
        
        if hasattr(task, 'error_message') and task.error_message:
            result["error_message"] = task.error_message
        
        # 添加文件信息
        if hasattr(task, 'file_info') and task.file_info:
            result["file_info"] = {
                "input_filename": getattr(task.file_info, 'input_filename', ''),
                "expected_output_filename": getattr(task.file_info, 'expected_output_filename', '')
            }
        
        return result
    
    @staticmethod
    def format_style_info(style) -> Dict[str, Any]:
        """格式化风格信息"""
        try:
            # 确保所有值都是可序列化的
            result = {
                "id": str(style.id) if style.id else "",
                "name": str(style.name) if style.name else "",
                "description": str(style.description) if style.description else "",
                "estimated_time": int(getattr(style, 'estimated_time', 0)),
                "tags": list(getattr(style, 'tags', []))
            }
            return result
        except Exception as e:
            logger.error(f"格式化风格信息失败: {e}")
            # 返回安全的默认值
            return {
                "id": "unknown",
                "name": "Unknown Style",
                "description": "Style information unavailable",
                "estimated_time": 60,
                "tags": []
            }
    
    @staticmethod
    def format_transform_result(task, result_data) -> Dict[str, Any]:
        """格式化转换结果"""
        formatted_result = {
            "request_id": task.request_id,
            "user_id": task.user_id,
            "style_id": task.style_id,
            "status": task.status,
            "duration": 0,
            "completed_at": task.completed_at
        }
        
        # 计算处理时长
        if task.completed_at and task.started_at:
            formatted_result["duration"] = task.completed_at - task.started_at
        
        # 处理输入文件信息
        if hasattr(task, 'input_file_info'):
            formatted_result["input_info"] = task.input_file_info
        
        # 处理输出文件信息
        if result_data and 'output' in result_data:
            output_images = []
            raw_outputs = result_data.get('output', {})
            
            for node_id, node_output in raw_outputs.items():
                if 'images' in node_output:
                    for img_data in node_output['images']:
                        filename = img_data.get('filename', 'unknown')
                        output_images.append({
                            "filename": filename,
                            "url": f"/view?filename={filename}&subfolder={img_data.get('subfolder', '')}&type={img_data.get('type', 'output')}",
                            "size": 0  # 暂时无法获取文件大小
                        })
            
            formatted_result["output_images"] = output_images
        
        return formatted_result