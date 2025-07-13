"""
转换任务RPC方法

提供图像转换任务的创建、查询、管理功能
"""

import logging
from typing import Dict, Any, List
from fastapi import Request

from ..router import rpc_method
from ..validator import RPCValidator
from ..formatter import RPCFormatter
from ..exceptions import RPCError, RPCTransformError
from ..error_codes import ErrorCodes
from ...services.transform_task_service import TransformTaskService

logger = logging.getLogger(__name__)


@rpc_method("transform.create")
async def create_transform(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """创建转换任务（下载 + 转换）"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["user_id", "style_id", "image_url"])
        
        user_id = params["user_id"]
        style_id = params["style_id"]
        image_url = params["image_url"]
        
        # 验证参数
        RPCValidator.validate_user_id(user_id)
        RPCValidator.validate_style_id(style_id)
        RPCValidator.validate_image_url(image_url)
        
        # 获取转换任务服务
        transform_service: TransformTaskService = request.app.state.transform_task_service
        
        # 创建转换任务
        task_id = await transform_service.create_transform_task(
            user_id=user_id,
            style_id=style_id,
            image_url=image_url
        )
        
        # 获取任务信息
        task_data = transform_service.get_user_task(user_id, task_id)
        if not task_data:
            raise RPCError(
                code=ErrorCodes.INTERNAL_ERROR,
                message="任务创建后无法获取任务信息"
            )
        
        # 格式化任务状态
        result = RPCFormatter.format_task_status(task_data)
        
        # 添加估算时间
        style_registry = request.app.state.style_registry
        if style_id in style_registry.styles:
            style_config = style_registry.styles[style_id]
            result["estimated_time"] = getattr(style_config, 'estimated_time', 60)
        
        return result
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"创建转换任务失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="创建转换任务失败",
            data={"error": str(e)}
        )


@rpc_method("transform.get_status")
async def get_transform_status(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取转换任务状态"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["user_id", "task_id"])
        
        user_id = params["user_id"]
        task_id = params["task_id"]
        
        # 验证参数
        RPCValidator.validate_user_id(user_id)
        RPCValidator.validate_task_id(task_id)
        
        # 获取转换任务服务
        transform_service: TransformTaskService = request.app.state.transform_task_service
        
        # 获取任务状态
        task_data = transform_service.get_user_task(user_id, task_id)
        if not task_data:
            raise RPCError(
                code=ErrorCodes.TASK_NOT_FOUND,
                message="任务不存在",
                data={"user_id": user_id, "task_id": task_id}
            )
        
        # 格式化任务状态
        return RPCFormatter.format_task_status(task_data)
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取任务状态失败",
            data={"error": str(e)}
        )


@rpc_method("transform.get_result")
async def get_transform_result(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取转换任务结果"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["user_id", "task_id"])
        
        user_id = params["user_id"]
        task_id = params["task_id"]
        
        # 验证参数
        RPCValidator.validate_user_id(user_id)
        RPCValidator.validate_task_id(task_id)
        
        # 获取转换任务服务
        transform_service: TransformTaskService = request.app.state.transform_task_service
        
        # 获取任务数据
        task_data = transform_service.get_user_task(user_id, task_id)
        if not task_data:
            raise RPCError(
                code=ErrorCodes.TASK_NOT_FOUND,
                message="任务不存在",
                data={"user_id": user_id, "task_id": task_id}
            )
        
        # 检查任务状态
        if task_data.status != "completed":
            raise RPCError(
                code=ErrorCodes.TASK_NOT_FOUND,
                message="任务结果尚不可用",
                data={
                    "task_id": task_id,
                    "current_status": task_data.status,
                    "message": "任务未完成或已失败"
                }
            )
        
        if not task_data.result:
            raise RPCError(
                code=ErrorCodes.INTERNAL_ERROR,
                message="任务已完成但结果数据不可用",
                data={"task_id": task_id}
            )
        
        # 格式化转换结果
        return RPCFormatter.format_transform_result(task_data, task_data.result)
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取任务结果失败",
            data={"error": str(e)}
        )


@rpc_method("transform.list")
async def list_transforms(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取用户转换任务列表"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["user_id"])
        
        user_id = params["user_id"]
        limit = params.get("limit", 100)
        status_filter = params.get("status_filter", None)
        
        # 验证参数
        RPCValidator.validate_user_id(user_id)
        
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message="limit参数必须是1-1000之间的整数",
                data={"field": "limit", "value": limit}
            )
        
        # 获取转换任务服务
        transform_service: TransformTaskService = request.app.state.transform_task_service
        
        # 获取任务列表
        tasks = transform_service.list_user_tasks(user_id, limit)
        
        # 应用状态过滤
        if status_filter:
            if isinstance(status_filter, str):
                status_filter = [status_filter]
            elif not isinstance(status_filter, list):
                raise RPCError(
                    code=ErrorCodes.INVALID_PARAMS,
                    message="status_filter必须是字符串或字符串列表",
                    data={"field": "status_filter", "value": status_filter}
                )
            
            tasks = [task for task in tasks if task.status in status_filter]
        
        # 格式化任务列表
        formatted_tasks = [
            RPCFormatter.format_task_status(task) for task in tasks
        ]
        
        return {
            "user_id": user_id,
            "tasks": formatted_tasks,
            "total": len(formatted_tasks),
            "filters": {
                "status_filter": status_filter,
                "limit": limit
            }
        }
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取任务列表失败",
            data={"error": str(e)}
        )


@rpc_method("transform.cancel")
async def cancel_transform(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """取消转换任务"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["user_id", "task_id"])
        
        user_id = params["user_id"]
        task_id = params["task_id"]
        
        # 验证参数
        RPCValidator.validate_user_id(user_id)
        RPCValidator.validate_task_id(task_id)
        
        # 获取转换任务服务
        transform_service: TransformTaskService = request.app.state.transform_task_service
        
        # 取消任务
        success = await transform_service.cancel_task(user_id, task_id)
        
        if not success:
            # 检查任务是否存在
            task_data = transform_service.get_user_task(user_id, task_id)
            if not task_data:
                raise RPCError(
                    code=ErrorCodes.TASK_NOT_FOUND,
                    message="任务不存在",
                    data={"user_id": user_id, "task_id": task_id}
                )
            else:
                raise RPCError(
                    code=ErrorCodes.TASK_CANCELLED,
                    message="任务无法取消",
                    data={
                        "task_id": task_id,
                        "current_status": task_data.status,
                        "reason": "任务已完成或已失败"
                    }
                )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已成功取消"
        }
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="取消任务失败",
            data={"error": str(e)}
        )