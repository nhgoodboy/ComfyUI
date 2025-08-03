"""
系统管理RPC方法

提供系统状态检查、工具方法等功能
"""

import logging
import time
from typing import Dict, Any
from fastapi import Request

from ..router import rpc_method
from ..validator import RPCValidator
from ..formatter import RPCFormatter
from ..exceptions import RPCError
from ..error_codes import ErrorCodes
from ...utils.file_naming import FileNamingUtils
from ...services.comfyui_service import ComfyUIService

logger = logging.getLogger(__name__)


@rpc_method("system.health")
async def system_health(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """系统健康检查"""
    try:
        settings = request.app.state.settings
        
        # 检查ComfyUI连接
        comfyui_healthy = False
        try:
            if hasattr(request.app.state, 'comfyui_service'):
                comfyui_service = request.app.state.comfyui_service
                comfyui_healthy = await comfyui_service.health_check()
        except Exception:
            comfyui_healthy = False
        
        # 检查存储目录
        storage_healthy = True
        try:
            storage_healthy = (
                settings.storage.uploads_dir.exists() and 
                settings.storage.outputs_dir.exists()
            )
        except Exception:
            storage_healthy = False
        
        # 检查工作流注册表
        workflows_count = 0
        try:
            if hasattr(request.app.state, 'workflow_registry'):
                workflow_registry = request.app.state.workflow_registry
                workflows = workflow_registry.get_all_workflows()
                workflows_count = len(workflows)
            else:
                logger.warning("Health check: workflow_registry not found in app.state")
        except Exception as e:
            logger.error(f"Health check: error getting workflows: {e}")
            workflows_count = 0
        
        # 计算总体状态
        overall_status = "healthy" if comfyui_healthy and storage_healthy and workflows_count > 0 else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "services": {
                "comfyui": "healthy" if comfyui_healthy else "unhealthy",
                "storage": "healthy" if storage_healthy else "unhealthy", 
                "workflows": "healthy" if workflows_count > 0 else "unhealthy"
            },
            "details": {
                "comfyui_connected": comfyui_healthy,
                "storage_healthy": storage_healthy,
                "workflows_count": workflows_count,
                "environment": settings.environment,
                "version": "2.0.0"
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="健康检查失败",
            data={"error": str(e)}
        )


# system.build_filename 方法已移除 - 在新架构中文件命名由客户端处理


@rpc_method("system.parse_filename")
async def parse_filename(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """解析文件名"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["filename"])
        
        filename = params["filename"]
        
        if not isinstance(filename, str) or not filename.strip():
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message="文件名不能为空",
                data={"field": "filename", "value": filename}
            )
        
        # 解析文件名
        file_info = FileNamingUtils.parse_filename(filename.strip())
        
        return {
            "filename": filename.strip(),
            "valid": True,
            "components": file_info
        }
        
    except RPCError:
        raise
    except Exception as e:
        # 文件名格式错误
        return {
            "filename": params.get("filename", ""),
            "valid": False,
            "error": str(e),
            "expected_pattern": "{workflow_id}_{request_id}_{input|output}.{ext}",
            "example": "clay_style_123e4567-e89b-12d3-a456-426614174000_input.jpg"
        }


@rpc_method("system.get_stats")
async def get_system_stats(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取系统统计信息"""
    try:
        stats = {
            "timestamp": time.time(),
            "uptime": time.time() - getattr(request.app.state, 'start_time', time.time()),
            "tasks": {
                "total": 0,
                "by_status": {},
                "by_user": {}
            },
            "files": {
                "inputs": 0,
                "outputs": 0,
                "temp": 0
            },
            "workflows": {
                "total": 0,
                "available": []
            }
        }
        
        # 统计任务信息 - 简化统计（新架构中不再区分用户）
        if hasattr(request.app.state, 'workflow_task_service'):
            workflow_service = request.app.state.workflow_task_service
            
            # 新的数据结构：只按request_id存储任务
            total_tasks = len(workflow_service.tasks)
            stats["tasks"]["total"] = total_tasks
            
            # 按状态统计
            for task in workflow_service.tasks.values():
                status = task.status
                if status not in stats["tasks"]["by_status"]:
                    stats["tasks"]["by_status"][status] = 0
                stats["tasks"]["by_status"][status] += 1
        
        # 统计文件信息
        try:
            settings = request.app.state.settings
            
            uploads_dir = settings.storage.uploads_dir
            if uploads_dir.exists():
                stats["files"]["inputs"] = len(list(uploads_dir.glob("*")))
            
            outputs_dir = settings.storage.outputs_dir
            if outputs_dir.exists():
                stats["files"]["outputs"] = len(list(outputs_dir.glob("*")))
            
            # 临时目录（如果存在）
            temp_dir = settings.storage.uploads_dir.parent / "temp"
            if temp_dir.exists():
                stats["files"]["temp"] = len(list(temp_dir.glob("*")))
                
        except Exception as e:
            logger.warning(f"统计文件信息失败: {e}")
        
        # 统计工作流信息
        if hasattr(request.app.state, 'workflow_registry'):
            workflow_registry = request.app.state.workflow_registry
            available_workflows = workflow_registry.get_all_workflows()
            stats["workflows"]["total"] = len(available_workflows)
            stats["workflows"]["available"] = [wf.id for wf in available_workflows]
        
        return stats
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取系统统计失败",
            data={"error": str(e)}
        )