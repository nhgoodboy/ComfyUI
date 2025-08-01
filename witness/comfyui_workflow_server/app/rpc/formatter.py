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
        formatted_result = {
            "request_id": task.request_id,
            "workflow_id": task.workflow_id,
            "status": task.status,
            "duration": 0,
            "completed_at": task.completed_at
        }
        
        # 计算处理时长
        if task.completed_at and task.started_at:
            formatted_result["duration"] = task.completed_at - task.started_at
        
        # 处理工作流参数信息
        if hasattr(task, 'workflow_params'):
            formatted_result["workflow_params"] = task.workflow_params
        
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
                            "url": f"/outputs/{filename}",
                            "size": img_data.get('size', 0)
                        })
            
            formatted_result["output_images"] = output_images
        
        return formatted_result
    
    # 兼容性别名
    format_task_status = format_workflow_task_status
    format_transform_result = format_workflow_result