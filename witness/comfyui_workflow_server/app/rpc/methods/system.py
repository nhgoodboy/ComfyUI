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
        comfyui_error = None
        
        try:
            if hasattr(request.app.state, 'comfyui_service'):
                comfyui_service: ComfyUIService = request.app.state.comfyui_service
                comfyui_healthy = comfyui_service._client_id is not None
        except Exception as e:
            comfyui_error = str(e)
        
        # 检查存储目录
        storage_healthy = True
        storage_errors = []
        
        try:
            # 检查输入目录
            inputs_dir = settings.storage.base_dir / "inputs"
            if not inputs_dir.exists():
                inputs_dir.mkdir(parents=True, exist_ok=True)
            
            # 检查输出目录  
            outputs_dir = settings.storage.base_dir / "outputs"
            if not outputs_dir.exists():
                outputs_dir.mkdir(parents=True, exist_ok=True)
                
            # 检查临时目录
            temp_dir = settings.storage.base_dir / "temp"
            if not temp_dir.exists():
                temp_dir.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            storage_healthy = False
            storage_errors.append(str(e))
        
        # 检查风格注册表
        styles_healthy = False
        styles_count = 0
        
        try:
            if hasattr(request.app.state, 'style_registry'):
                style_registry = request.app.state.style_registry
                styles_count = len(style_registry.styles)
                styles_healthy = styles_count > 0
        except Exception as e:
            logger.warning(f"检查风格注册表失败: {e}")
        
        # 检查服务状态
        services_status = {}
        
        # 检查转换任务服务
        try:
            if hasattr(request.app.state, 'transform_task_service'):
                transform_service = request.app.state.transform_task_service
                services_status["transform_task_service"] = "healthy"
            else:
                services_status["transform_task_service"] = "missing"
        except Exception as e:
            services_status["transform_task_service"] = f"error: {str(e)}"
        
        # 检查下载服务
        try:
            download_service = request.app.state.get('download_service')
            if download_service:
                services_status["download_service"] = "healthy"
            else:
                services_status["download_service"] = "not_configured"
        except Exception as e:
            services_status["download_service"] = f"error: {str(e)}"
        
        # 计算总体状态
        overall_status = "healthy"
        if not comfyui_healthy or not storage_healthy or not styles_healthy:
            overall_status = "unhealthy"
        elif any("error" in status for status in services_status.values()):
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "services": {
                "comfyui": "healthy" if comfyui_healthy else "unhealthy",
                "storage": "healthy" if storage_healthy else "unhealthy", 
                "styles": "healthy" if styles_healthy else "unhealthy"
            },
            "details": {
                "comfyui": {
                    "connected": comfyui_healthy,
                    "error": comfyui_error,
                    "url": settings.comfyui.base_url if hasattr(settings, 'comfyui') else None
                },
                "storage": {
                    "healthy": storage_healthy,
                    "errors": storage_errors,
                    "paths": {
                        "inputs": str(settings.storage.base_dir / "inputs"),
                        "outputs": str(settings.storage.base_dir / "outputs"),
                        "temp": str(settings.storage.base_dir / "temp")
                    }
                },
                "styles": {
                    "count": styles_count,
                    "healthy": styles_healthy
                },
                "services": services_status,
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


@rpc_method("system.build_filename")
async def build_filename(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """构建符合规范的文件名"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["style_id", "user_id", "type"])
        
        style_id = params["style_id"]
        user_id = params["user_id"]
        file_type = params["type"]
        extension = params.get("extension", "jpg")
        
        # 验证参数
        RPCValidator.validate_style_id(style_id)
        RPCValidator.validate_user_id(user_id)
        
        if file_type not in ["input", "output"]:
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message="文件类型必须是 'input' 或 'output'",
                data={"field": "type", "value": file_type}
            )
        
        # 构建文件名
        filename = FileNamingUtils.build_filename(style_id, user_id, file_type, extension)
        
        # 构建示例URL
        settings = request.app.state.settings
        base_url = "http://your-domain:8000"  # 可以从配置获取
        
        if file_type == "input":
            example_url = f"{base_url}/inputs/{filename}"
        else:
            example_url = f"{base_url}/outputs/{filename}"
        
        return {
            "filename": filename,
            "components": {
                "style_id": style_id,
                "user_id": user_id,
                "type": file_type,
                "extension": extension
            },
            "example_url": example_url,
            "pattern": "{style_id}_{user_id}_{type}.{ext}"
        }
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"构建文件名失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="构建文件名失败",
            data={"error": str(e)}
        )


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
        file_info = FileNamingUtils.extract_file_info(filename.strip())
        
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
            "expected_pattern": "{style_id}_{user_id}_{input|output}.{ext}",
            "example": "clay_style_alice_input.jpg"
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
            "styles": {
                "total": 0,
                "available": []
            }
        }
        
        # 统计任务信息
        if hasattr(request.app.state, 'transform_task_service'):
            transform_service = request.app.state.transform_task_service
            
            for user_id, user_tasks in transform_service.user_tasks.items():
                stats["tasks"]["by_user"][user_id] = len(user_tasks)
                stats["tasks"]["total"] += len(user_tasks)
                
                for task in user_tasks.values():
                    status = task.status
                    if status not in stats["tasks"]["by_status"]:
                        stats["tasks"]["by_status"][status] = 0
                    stats["tasks"]["by_status"][status] += 1
        
        # 统计文件信息
        try:
            settings = request.app.state.settings
            
            inputs_dir = settings.storage.base_dir / "inputs"
            if inputs_dir.exists():
                stats["files"]["inputs"] = len(list(inputs_dir.glob("*")))
            
            outputs_dir = settings.storage.base_dir / "outputs"
            if outputs_dir.exists():
                stats["files"]["outputs"] = len(list(outputs_dir.glob("*")))
            
            temp_dir = settings.storage.base_dir / "temp"
            if temp_dir.exists():
                stats["files"]["temp"] = len(list(temp_dir.glob("*")))
                
        except Exception as e:
            logger.warning(f"统计文件信息失败: {e}")
        
        # 统计风格信息
        if hasattr(request.app.state, 'style_registry'):
            style_registry = request.app.state.style_registry
            stats["styles"]["total"] = len(style_registry.styles)
            stats["styles"]["available"] = list(style_registry.styles.keys())
        
        return stats
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取系统统计失败",
            data={"error": str(e)}
        )