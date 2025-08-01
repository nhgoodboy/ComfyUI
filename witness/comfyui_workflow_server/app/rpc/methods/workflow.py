"""
工作流执行RPC方法

提供统一的工作流执行、查询、管理功能
支持任意类型的工作流处理
"""

import logging
from typing import Dict, Any, List
from fastapi import Request

from ..router import rpc_method
from ..validator import RPCValidator
from ..formatter import RPCFormatter
from ..exceptions import RPCError
from ..error_codes import ErrorCodes
from ...services.workflow_task_service import WorkflowTaskService
from ...core.workflow_registry import WorkflowRegistry

logger = logging.getLogger(__name__)


@rpc_method("workflow.execute")
async def execute_workflow(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """执行工作流
    
    统一的工作流执行接口，支持任意类型的工作流
    
    Args:
        params: {
            "request_id": "req_123456789",
            "workflow_id": "clay_style_transform", 
            "params": {
                "input_image": "http://example.com/image.jpg",
                "prompt": "Clay Style, lovely, cute",
                "guidance": 12
            }
        }
    """
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["request_id", "workflow_id", "params"])
        
        request_id = params["request_id"]
        workflow_id = params["workflow_id"]
        workflow_params = params["params"]
        
        # 验证基础参数
        RPCValidator.validate_request_id(request_id)
        
        # 获取工作流注册器
        workflow_registry: WorkflowRegistry = request.app.state.workflow_registry
        
        # 验证工作流是否存在
        if not workflow_registry.workflow_exists(workflow_id):
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message=f"工作流不存在: {workflow_id}",
                data={"workflow_id": workflow_id}
            )
        
        # 验证工作流参数
        try:
            validated_params = workflow_registry.validate_parameters(workflow_id, workflow_params)
        except ValueError as e:
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message=f"工作流参数验证失败: {str(e)}",
                data={"workflow_id": workflow_id, "params": workflow_params}
            )
        
        # 获取工作流任务服务
        workflow_service: WorkflowTaskService = request.app.state.workflow_task_service
        
        # 创建工作流执行任务
        task_id = await workflow_service.create_workflow_task(
            request_id=request_id,
            workflow_id=workflow_id,
            params=validated_params
        )
        
        # 获取任务信息
        task_data = workflow_service.get_task(request_id)
        if not task_data:
            raise RPCError(
                code=ErrorCodes.INTERNAL_ERROR,
                message="任务创建后无法获取任务信息"
            )
        
        # 格式化任务状态
        result = RPCFormatter.format_task_status(task_data)
        
        # 添加工作流信息
        workflow_config = workflow_registry.get_workflow(workflow_id)
        if workflow_config:
            result["workflow_info"] = {
                "workflow_id": workflow_id,
                "name": workflow_config.name,
                "description": workflow_config.description,
                "estimated_time": workflow_config.estimated_time
            }
        
        return result
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"执行工作流失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="执行工作流失败",
            data={"error": str(e)}
        )


@rpc_method("workflow.list")
async def list_workflows(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取可用工作流列表"""
    try:
        # 获取工作流注册器
        workflow_registry: WorkflowRegistry = request.app.state.workflow_registry
        
        # 获取所有工作流
        workflows = workflow_registry.get_all_workflows()
        
        # 格式化工作流信息
        workflow_list = []
        for workflow in workflows:
            workflow_info = {
                "workflow_id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "estimated_time": workflow.estimated_time,
                "tags": workflow.tags,
                "version": workflow.version,
                "parameter_count": len(workflow.parameters)
            }
            workflow_list.append(workflow_info)
        
        return {
            "workflows": workflow_list,
            "total_count": len(workflow_list)
        }
        
    except Exception as e:
        logger.error(f"获取工作流列表失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取工作流列表失败",
            data={"error": str(e)}
        )


@rpc_method("workflow.get_schema")
async def get_workflow_schema(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取工作流参数模式
    
    返回工作流的参数定义，用于前端表单生成
    """
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["workflow_id"])
        
        workflow_id = params["workflow_id"]
        
        # 获取工作流注册器
        workflow_registry: WorkflowRegistry = request.app.state.workflow_registry
        
        # 验证工作流是否存在
        if not workflow_registry.workflow_exists(workflow_id):
            raise RPCError(
                code=ErrorCodes.INVALID_PARAMS,
                message=f"工作流不存在: {workflow_id}",
                data={"workflow_id": workflow_id}
            )
        
        # 获取工作流模式
        schema = workflow_registry.get_workflow_schema(workflow_id)
        
        return schema
        
    except RPCError:
        raise
    except Exception as e:
        logger.error(f"获取工作流模式失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="获取工作流模式失败",
            data={"error": str(e)}
        )


@rpc_method("workflow.get_status")
async def get_workflow_status(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取工作流任务状态"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["request_id"])
        
        request_id = params["request_id"]
        
        # 验证参数
        RPCValidator.validate_request_id(request_id)
        
        # 获取工作流任务服务
        workflow_service: WorkflowTaskService = request.app.state.workflow_task_service
        
        # 获取任务状态
        task_data = workflow_service.get_task(request_id)
        if not task_data:
            raise RPCError(
                code=ErrorCodes.TASK_NOT_FOUND,
                message="任务不存在",
                data={"request_id": request_id}
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


@rpc_method("workflow.get_result")
async def get_workflow_result(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """获取工作流任务结果"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["request_id"])
        
        request_id = params["request_id"]
        
        # 验证参数
        RPCValidator.validate_request_id(request_id)
        
        # 获取工作流任务服务
        workflow_service: WorkflowTaskService = request.app.state.workflow_task_service
        
        # 获取任务数据
        task_data = workflow_service.get_task(request_id)
        if not task_data:
            raise RPCError(
                code=ErrorCodes.TASK_NOT_FOUND,
                message="任务不存在",
                data={"request_id": request_id}
            )
        
        # 检查任务状态
        if task_data.status != "completed":
            raise RPCError(
                code=ErrorCodes.TASK_NOT_FOUND,
                message="任务结果尚不可用",
                data={
                    "request_id": request_id,
                    "current_status": task_data.status,
                    "message": "任务未完成或已失败"
                }
            )
        
        if not task_data.result:
            raise RPCError(
                code=ErrorCodes.INTERNAL_ERROR,
                message="任务已完成但结果数据不可用",
                data={"request_id": request_id}
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


@rpc_method("workflow.cancel")
async def cancel_workflow(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """取消工作流任务"""
    try:
        # 验证必需参数
        RPCValidator.validate_required_fields(params, ["request_id"])
        
        request_id = params["request_id"]
        
        # 验证参数
        RPCValidator.validate_request_id(request_id)
        
        # 获取工作流任务服务
        workflow_service: WorkflowTaskService = request.app.state.workflow_task_service
        
        # 取消任务
        success = await workflow_service.cancel_task(request_id)
        
        if not success:
            # 检查任务是否存在
            task_data = workflow_service.get_task(request_id)
            if not task_data:
                raise RPCError(
                    code=ErrorCodes.TASK_NOT_FOUND,
                    message="任务不存在",
                    data={"request_id": request_id}
                )
            else:
                raise RPCError(
                    code=ErrorCodes.TASK_CANCELLED,
                    message="任务无法取消",
                    data={
                        "request_id": request_id,
                        "current_status": task_data.status,
                        "reason": "任务已完成或已失败"
                    }
                )
        
        return {
            "success": True,
            "request_id": request_id,
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


@rpc_method("workflow.search")
async def search_workflows(params: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """搜索工作流"""
    try:
        # 获取查询参数
        query = params.get("query", "").strip()
        
        # 获取工作流注册器
        workflow_registry: WorkflowRegistry = request.app.state.workflow_registry
        
        # 搜索工作流
        workflows = workflow_registry.search_workflows(query)
        
        # 格式化搜索结果
        workflow_list = []
        for workflow in workflows:
            workflow_info = {
                "workflow_id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "estimated_time": workflow.estimated_time,
                "tags": workflow.tags,
                "version": workflow.version
            }
            workflow_list.append(workflow_info)
        
        return {
            "workflows": workflow_list,
            "total_count": len(workflow_list),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"搜索工作流失败: {e}", exc_info=True)
        raise RPCError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="搜索工作流失败",
            data={"error": str(e)}
        )
