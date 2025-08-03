"""
RPC响应格式化器

负责格式化RPC响应数据，使用统一的协议模型
"""

import logging
from typing import Any, Dict
from pathlib import Path
from .protocol import WorkflowTaskStatus, WorkflowInfo, WorkflowResult, FileInfo

logger = logging.getLogger(__name__)


class RPCFormatter:
    """RPC响应格式化器"""
    
    @staticmethod
    def format_success(result: Any, request_id: str) -> Dict[str, Any]:
        """格式化成功响应"""
        if not isinstance(result, dict):
            result = {"data": result}
        
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
            try:
                import json
                json.dumps(data)
                error_dict["data"] = data
            except (TypeError, ValueError):
                error_dict["data"] = str(data)
        
        return {
            "error": error_dict,
            "id": str(request_id) if request_id else None
        }
    
    @staticmethod
    def format_workflow_task_status(task) -> Dict[str, Any]:
        """格式化工作流任务状态信息，使用协议模型"""
        try:
            # 使用协议模型创建标准化的任务状态
            task_status = WorkflowTaskStatus(
                request_id=task.request_id,
                workflow_id=task.workflow_id,
                status=task.status,
                progress=task.progress,
                stage=getattr(task, 'stage', 'unknown'),
                message=getattr(task, 'message', ''),
                created_at=int(task.created_at) if task.created_at else None,
                started_at=int(task.started_at) if hasattr(task, 'started_at') and task.started_at else None,
                completed_at=int(task.completed_at) if hasattr(task, 'completed_at') and task.completed_at else None,
                estimated_remaining=getattr(task, 'estimated_remaining', None),
                workflow_params=getattr(task, 'workflow_params', None),
                error_message=getattr(task, 'error_message', None)
            )
            
            return task_status.model_dump()
            
        except Exception as e:
            logger.error(f"格式化任务状态失败: {e}")
            # 降级处理，返回基本信息
            return {
                "request_id": getattr(task, 'request_id', 'unknown'),
                "workflow_id": getattr(task, 'workflow_id', 'unknown'),
                "status": getattr(task, 'status', 'unknown'),
                "progress": getattr(task, 'progress', 0.0),
                "stage": "unknown",
                "message": "状态信息不可用",
                "created_at": None
            }
    
    @staticmethod
    def format_workflow_info(workflow) -> Dict[str, Any]:
        """格式化工作流信息，使用协议模型"""
        try:
            # 使用协议模型创建标准化的工作流信息
            workflow_info = WorkflowInfo(
                workflow_id=str(workflow.id) if workflow.id else "",
                name=str(workflow.name) if workflow.name else "",
                description=str(workflow.description) if workflow.description else "",
                estimated_time=int(getattr(workflow, 'estimated_time', 0)),
                tags=list(getattr(workflow, 'tags', [])),
                version=str(getattr(workflow, 'version', '1.0'))
            )
            
            return workflow_info.model_dump()
            
        except Exception as e:
            logger.error(f"格式化工作流信息失败: {e}")
            # 降级处理，返回基本信息
            return {
                "workflow_id": "unknown",
                "name": "Unknown Workflow",
                "description": "Workflow information unavailable",
                "estimated_time": 60,
                "tags": [],
                "version": "1.0"
            }
    
    @staticmethod
    def format_workflow_result(task, result_data) -> Dict[str, Any]:
        """格式化工作流结果，使用协议模型"""
        from ..config import get_settings
        
        try:
            # 计算处理时长，保留2位小数
            duration = 0.0
            if task.completed_at and task.started_at:
                duration = round(task.completed_at - task.started_at, 2)
            
            # 获取外部访问的基础URL
            settings = get_settings()
            base_url = settings.get_external_base_url()
            
            # 处理输出文件信息
            output_images = []
            if result_data and 'output_images' in result_data:
                for img_data in result_data['output_images']:
                    filename = img_data.get('filename', 'unknown')
                    
                    # 检查文件是否存在并获取大小
                    try:
                        output_dir = Path("outputs")
                        file_path = output_dir / filename
                        
                        if file_path.exists():
                            file_size = file_path.stat().st_size
                            stat = file_path.stat()
                            
                            # 使用协议模型创建文件信息
                            file_info = FileInfo(
                                filename=filename,
                                size=file_size,
                                media_type=f"image/{file_path.suffix.lower()[1:]}",
                                extension=file_path.suffix.lower(),
                                url=f"{base_url}/outputs/{filename}",
                                static_url=f"{base_url}/outputs/{filename}",
                                created_time=int(stat.st_ctime),
                                modified_time=int(stat.st_mtime),
                                is_image=True
                            )
                            output_images.append(file_info)
                        else:
                            logger.warning(f"输出文件不存在: {filename}")
                            
                    except Exception as e:
                        logger.warning(f"获取文件信息失败 {filename}: {e}")
            
            # 使用协议模型创建结果
            workflow_result = WorkflowResult(
                request_id=task.request_id,
                workflow_id=task.workflow_id,
                status=task.status,
                duration=duration,
                completed_at=int(task.completed_at) if task.completed_at else None,
                workflow_params=getattr(task, 'workflow_params', None),
                output_images=[f.model_dump() for f in output_images]
            )
            
            return workflow_result.model_dump()
            
        except Exception as e:
            logger.error(f"格式化工作流结果失败: {e}")
            # 降级处理，返回基本信息
            return {
                "request_id": getattr(task, 'request_id', 'unknown'),
                "workflow_id": getattr(task, 'workflow_id', 'unknown'),
                "status": getattr(task, 'status', 'unknown'),
                "duration": 0.0,
                "completed_at": None,
                "workflow_params": None,
                "output_images": []
            }