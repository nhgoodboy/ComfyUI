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
    def format_workflow_task_status(task) -> Dict[str, Any]:
        """格式化工作流任务状态信息"""
        result = {
            "request_id": task.request_id,
            "workflow_id": task.workflow_id,
            "status": task.status,
            "progress": task.progress,
            "stage": getattr(task, 'stage', 'unknown'),
            "message": getattr(task, 'message', ''),
            "created_at": int(task.created_at) if task.created_at else None,
            "estimated_remaining": getattr(task, 'estimated_remaining', None)
        }
        
        # 添加可选字段，时间戳转换为整数
        if hasattr(task, 'started_at') and task.started_at:
            result["started_at"] = int(task.started_at)
        
        if hasattr(task, 'completed_at') and task.completed_at:
            result["completed_at"] = int(task.completed_at)
        
        if hasattr(task, 'error_message') and task.error_message:
            result["error_message"] = task.error_message
        
        # 添加工作流参数信息
        if hasattr(task, 'workflow_params') and task.workflow_params:
            result["workflow_params"] = task.workflow_params
        
        return result
    
    @staticmethod
    def format_workflow_info(workflow) -> Dict[str, Any]:
        """格式化工作流信息"""
        try:
            # 确保所有值都是可序列化的
            result = {
                "id": str(workflow.id) if workflow.id else "",
                "name": str(workflow.name) if workflow.name else "",
                "description": str(workflow.description) if workflow.description else "",
                "estimated_time": int(getattr(workflow, 'estimated_time', 0)),
                "tags": list(getattr(workflow, 'tags', [])),
                "version": str(getattr(workflow, 'version', '1.0'))
            }
            return result
        except Exception as e:
            logger.error(f"格式化工作流信息失败: {e}")
            # 返回安全的默认值
            return {
                "id": "unknown",
                "name": "Unknown Workflow",
                "description": "Workflow information unavailable",
                "estimated_time": 60,
                "tags": [],
                "version": "1.0"
            }
    
    @staticmethod
    def format_workflow_result(task, result_data) -> Dict[str, Any]:
        """格式化工作流结果"""
        from ..config import settings
        
        formatted_result = {
            "request_id": task.request_id,
            "workflow_id": task.workflow_id,
            "status": task.status,
            "duration": 0,
            "completed_at": int(task.completed_at) if task.completed_at else None
        }
        
        # 计算处理时长，保留到秒（2位小数）
        if task.completed_at and task.started_at:
            formatted_result["duration"] = round(task.completed_at - task.started_at, 2)
        
        # 处理工作流参数信息
        if hasattr(task, 'workflow_params'):
            formatted_result["workflow_params"] = task.workflow_params
        
        # 获取外部访问的基础URL
        base_url = settings.get_external_base_url()
        
        # 处理输出文件信息 - 使用新的数据结构
        output_images = []
        if result_data and 'output_images' in result_data:
            for img_data in result_data['output_images']:
                filename = img_data.get('filename', 'unknown')
                # 检查文件是否存在并获取大小
                from pathlib import Path
                
                try:
                    # 假设输出文件在 outputs 目录中
                    output_dir = Path("outputs")
                    file_path = output_dir / filename
                    
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                    else:
                        file_size = 0
                        logger.warning(f"输出文件不存在: {filename}")
                        
                except Exception as e:
                    logger.warning(f"获取文件大小失败 {filename}: {e}")
                    file_size = 0
                
                output_images.append({
                    "filename": filename,
                    "url": f"{base_url}/outputs/{filename}",  # 使用完整URL
                    "size": file_size
                })
        
        formatted_result["output_images"] = output_images
        
        return formatted_result
    
    # 兼容性别名
    format_task_status = format_workflow_task_status
    format_transform_result = format_workflow_result