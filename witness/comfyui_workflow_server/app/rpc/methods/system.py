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
from ..protocol import SystemHealth, ServiceStatus, SystemHealthDetails, SystemStats, TaskStats, FileStats, WorkflowStats
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
        
        # 使用协议模型返回结果
        services = ServiceStatus(
            comfyui="healthy" if comfyui_healthy else "unhealthy",
            storage="healthy" if storage_healthy else "unhealthy",
            workflows="healthy" if workflows_count > 0 else "unhealthy"
        )
        
        details = SystemHealthDetails(
            comfyui_connected=comfyui_healthy,
            storage_healthy=storage_healthy,
            workflows_count=workflows_count,
            environment=settings.environment,
            version="2.0.0"
        )
        
        result = SystemHealth(
            status=overall_status,
            timestamp=time.time(),
            services=services,
            details=details
        )
        
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="健康检查失败",
            data={"error": str(e)}
        )


# system.build_filename 方法已移除 - 在新架构中文件命名由客户端处理


@rpc_method("system.get_stats")
async def get_system_stats(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取系统统计信息"""
    try:
        # 基础统计数据
        task_stats = TaskStats(
            total=0,
            by_status={},
            by_user={}
        )
        
        file_stats = FileStats(
            inputs=0,
            outputs=0,
            temp=0
        )
        
        workflow_stats = WorkflowStats(
            total=0,
            available=[]
        )
        
        # 统计任务信息 - 简化统计（新架构中不再区分用户）
        if hasattr(request.app.state, 'workflow_task_service'):
            workflow_service = request.app.state.workflow_task_service
            
            # 新的数据结构：只按request_id存储任务
            total_tasks = len(workflow_service.tasks)
            task_stats.total = total_tasks
            
            # 按状态统计
            for task in workflow_service.tasks.values():
                status = task.status
                if status not in task_stats.by_status:
                    task_stats.by_status[status] = 0
                task_stats.by_status[status] += 1
        
        # 统计文件信息
        try:
            settings = request.app.state.settings
            
            uploads_dir = settings.storage.uploads_dir
            if uploads_dir.exists():
                file_stats.inputs = len(list(uploads_dir.glob("*")))
            
            outputs_dir = settings.storage.outputs_dir
            if outputs_dir.exists():
                file_stats.outputs = len(list(outputs_dir.glob("*")))
            
            # 临时目录（如果存在）
            temp_dir = settings.storage.uploads_dir.parent / "temp"
            if temp_dir.exists():
                file_stats.temp = len(list(temp_dir.glob("*")))
                
        except Exception as e:
            logger.warning(f"统计文件信息失败: {e}")
        
        # 统计工作流信息
        if hasattr(request.app.state, 'workflow_registry'):
            workflow_registry = request.app.state.workflow_registry
            available_workflows = workflow_registry.get_all_workflows()
            workflow_stats.total = len(available_workflows)
            workflow_stats.available = [wf.id for wf in available_workflows]
        
        # 使用协议模型返回结果
        result = SystemStats(
            timestamp=time.time(),
            uptime=time.time() - getattr(request.app.state, 'start_time', time.time()),
            tasks=task_stats,
            files=file_stats,
            workflows=workflow_stats
        )
        
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取系统统计失败",
            data={"error": str(e)}
        )